"""Build the immutable, detector-blind synthetic validation contract."""

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "protocol" / "waveform-battery.json"
PI = math.pi


def landmarks_for_phase(fs, duration, frequency, phase, amplitude=20.0):
    result = {"extrema": [], "inflections": []}
    for family, base in (("extrema", PI / 2), ("inflections", 0.0)):
        for k in range(-100, int(2 * duration * frequency) + 101):
            t = (base - phase + k * PI) / (2 * PI * frequency)
            if 0 <= t < duration:
                result[family].append({"seconds": t, "nearest_sample": math.floor(fs * t + .5),
                                       "polarity": ("peak" if k % 2 == 0 else "trough") if family == "extrema" else None,
                                       "direction": ("curvature_positive_to_negative" if k % 2 == 0 else "curvature_negative_to_positive") if family == "inflections" else None})
    return result


def chirp_truth(fs, duration, f0, f1, phase):
    slope = (f1 - f0) / duration
    result = {"extrema": [], "inflections": []}
    for family, base in (("extrema", PI / 2), ("inflections", 0.0)):
        for k in range(-20, 2 * int(f1 * duration) + 30):
            target = (base - phase + k * PI) / (2 * PI)
            disc = f0 * f0 + 2 * slope * target
            if disc < 0:
                continue
            t = (-f0 + math.sqrt(disc)) / slope
            if family == "inflections" and 0 <= t < duration:
                # x''=A*(phase''*cos(phase)-phase'^2*sin(phase)); solve
                # phase(t)-atan(phase''/phase'(t)^2)=k*pi.
                left, right = max(0., t-.01), min(duration, t+.01)
                for _ in range(70):
                    middle = (left + right) / 2
                    angular_rate = 2*PI*(f0+slope*middle)
                    value = 2*PI*(f0*middle+.5*slope*middle*middle)+phase - math.atan(2*PI*slope/(angular_rate*angular_rate)) - k*PI
                    if value < 0:
                        left = middle
                    else:
                        right = middle
                t = (left+right)/2
            if 0 <= t < duration:
                result[family].append({"seconds": t, "nearest_sample": math.floor(fs * t + .5),
                                       "phase_crossing_k": k,
                                       "polarity": ("peak" if k % 2 == 0 else "trough") if family == "extrema" else None,
                                       "direction": ("curvature_positive_to_negative" if k % 2 == 0 else
                                                     "curvature_negative_to_positive") if family == "inflections" else None})
    return result


def asymmetric_truth(fs, duration, f):
    root = math.acos((math.sqrt(3) - 1) / 2)
    extrema_phases = [(root, "peak"), (2 * PI - root, "trough")]
    inflection_phases = [(0, "curvature_positive_to_negative"), (2 * PI / 3, "curvature_negative_to_positive"),
                         (PI, "curvature_positive_to_negative"), (4 * PI / 3, "curvature_negative_to_positive")]
    result = {"extrema": [], "inflections": []}
    for cycle in range(int(duration * f) + 1):
        for theta, polarity in extrema_phases:
            t = (cycle + theta / (2 * PI)) / f
            if t < duration:
                result["extrema"].append({"seconds": t, "nearest_sample": math.floor(fs*t+.5), "polarity": polarity})
        for theta, direction in inflection_phases:
            t = (cycle + theta / (2 * PI)) / f
            if t < duration:
                result["inflections"].append({"seconds": t, "nearest_sample": math.floor(fs*t+.5), "direction": direction})
    return result


def packet_truth(fs=250, start=10., end=20., frequency=8.):
    """Roots of derivatives of the specified raised-cosine packet, excluding edges."""
    omega, taper = 2*PI*frequency, 2*PI/(end-start)
    def derivatives(t):
        u = t-start
        env = .5-.5*math.cos(taper*u)
        d_env = .5*taper*math.sin(taper*u)
        dd_env = .5*taper*taper*math.cos(taper*u)
        sn, cs = math.sin(omega*t), math.cos(omega*t)
        return (d_env*sn+env*omega*cs,
                (dd_env-env*omega*omega)*sn+2*d_env*omega*cs)
    result = {"extrema": [], "inflections": []}
    grid_step = 1/(fs*8)
    for family, component in (("extrema", 0), ("inflections", 1)):
        last = start+grid_step
        while last+grid_step < end:
            right = last+grid_step
            if derivatives(last)[component]*derivatives(right)[component] < 0:
                left = last
                sign = 1 if derivatives(left)[component] > 0 else -1
                for _ in range(55):
                    midpoint = (left+right)/2
                    if derivatives(midpoint)[component]*sign > 0:
                        left = midpoint
                    else:
                        right = midpoint
                root = (left+right)/2
                label = ("peak" if sign > 0 else "trough") if family == "extrema" else (
                    "curvature_positive_to_negative" if sign > 0 else "curvature_negative_to_positive")
                result[family].append({"seconds": root, "nearest_sample": math.floor(root*fs+.5),
                                       "polarity": label if family == "extrema" else None,
                                       "direction": label if family == "inflections" else None})
            last = right
    return result


def build():
    sine = []
    for fs in (200, 250, 500):
        for frequency in (3, 5, 10, 20):
            for phase_name, phase in (("zero", 0.0), ("pi_over_7", PI/7), ("pi_over_2", PI/2)):
                sine.append({"id": f"sine-fs{fs}-f{frequency}-{phase_name}", "generator": "20*sin(2*pi*f*t+phase) microvolt",
                             "fs_hz": fs, "duration_seconds": 30, "frequency_hz": frequency, "phase_radians": phase,
                             "amplitude_uv": 20.0, "truth": landmarks_for_phase(fs, 30, frequency, phase)})
    controls = []
    for kind in ("white", "colored_ar1"):
        for seed in range(100):
            controls.append({"id": f"{kind}-{seed:03d}", "generator": kind, "seed": seed,
                             "fs_hz": 250, "duration_seconds": 20, "scale_uv": 5.0,
                             "rng": "NumPy1.26.4 default_rng(seed) PCG64 normal(0,1,N)",
                             "colored_formula": "lfilter([1],[1,-0.9],normal); divide by its sample standard deviation; multiply by5uv" if kind == "colored_ar1" else None,
                             "oscillator_present": False, "truth": {"cycles": [], "bursts": []}})
    packet = []
    for noise_uv in (0.0, 2.0, 8.0):
        for seed in range(10):
            packet.append({"id": f"packet-noise{noise_uv:g}-seed{seed:02d}", "generator": "8Hz raised_cosine_packet",
                           "seed": seed, "fs_hz": 250, "duration_seconds": 30, "start_seconds": 10.0,
                           "end_seconds": 20.0, "amplitude_uv": 20.0, "noise_sd_uv": noise_uv,
                           "rng": "NumPy1.26.4 default_rng(seed) PCG64 normal(0,noise_sd_uv,N)",
                           "packet_envelope": "0.5-0.5*cos(2*pi*(t-10)/10) for10<=t<20, else0",
                           "truth": {"packet_intervals_samples": [[2500, 5000]], "trial_has_packet": True}})
    protocol = {
        "schema": "eegt-waveform-battery-protocol/v1", "status": "REVIEW_R1_CORRECTED_FREEZE",
        "initial_freeze_sha256": "0809a490ac45c4e576295ac92a84490608428cccdd434e47f4a9ada869b093bc",
        "freeze_revisions": [
            "Specify optional notch Q=30 before first detector output; initial freeze retained in scratch.",
            "Correct analytic chirp inflection roots from phase crossings to x-second-derivative zeros and specify exact stochastic generator; earlier freeze retained.",
            "Predeclare 10 of 100 seeds per no-oscillator generator for bounded cycle/burst scoring; all 100 retain waveform scoring.",
            "Correct scoring-edge censoring after a retained failed battery: evaluate stationary truth at least four samples beyond measured guard, allow two-sample pairing across the evaluation edge, and exclude unmatched scoring-edge rows. Detector settings and two-sample hard gate unchanged.",
            "Add analytic raised-cosine packet derivative truth so noisy packet missed/extra landmarks and signed bias have a fixed denominator before final scoring.",
            "Review R1 correction before rerun: label chirp roots by analytic first/second derivative crossing; keep the same analytic roots and detector parameters.",
            "Review R1 correction before rerun: pair truth and detection with context, censor each crossing-edge pair on both sides, and require matched+missed=eligible truth and matched+extra=eligible detection; preserve raw core and censored counts.",
            "Review R1 coverage amendment before rerun: score cycles and both burst definitions for all original seeds 0-99 of each no-oscillator generator; retain the earlier 10-seed receipt separately. No new noise realizations or threshold changes."],
        "method_sha256": "7aefc9cb2fee774bc24d1ec3a6a85c467311e4e8660e2388792cfa7dde2df10c",
        "independent_review_status": "original_changes_required; root_resolved; continuation_not_run",
        "sample_convention": "t=n/fs, n=0..N-1; nearest truth index=floor(t*fs+0.5); intervals half-open",
        "duration_and_trial_units": {"noise": "one seed x generator, 20 seconds at 250 Hz", "packet": "one seed x noise level, 30 seconds at 250 Hz", "stationary": "one rate x frequency x phase, 30 seconds"},
        "configurations": {"primary": {"bandpass_hz": [1, 40], "smoothing_ms": 31, "notch_hz": None},
                           "waveform_sensitivities": {"smoothing_ms": [21, 31, 51], "bandpass_hz": [[0.5, 40], [1, 40], [1, 30]]},
                           "cycle_bands_hz": [[4, 8], [8, 13], [13, 30]],
                           "line_comparisons": ["none", "50Hz_notch", "60Hz_notch"], "notch_quality_factor": 30,
                           "resampling": [{"native_fs_hz": 250, "output_fs_hz": 200, "polyphase_up_down": [4, 5]},
                                          {"native_fs_hz": 250, "output_fs_hz": 500, "polyphase_up_down": [2, 1]}]},
        "stationary_sine": sine,
        "analytic_chirp": {"fs_hz": 250, "duration_seconds": 30, "f0_hz": 3, "f1_hz": 20,
                           "phase_radians": 0, "amplitude_uv": 20,
                           "generator": "20*sin(2*pi*(3*t+0.5*(17/30)*t*t))", "truth": chirp_truth(250, 30, 3, 20, 0)},
        "asymmetric_cycles": {"fs_hz": 250, "duration_seconds": 30, "frequency_hz": 8,
                               "generator": "20*(sin(theta)+0.25*sin(2*theta)); theta=2*pi*8*t",
                               "truth": asymmetric_truth(250, 30, 8)},
        "finite_packets": packet,
        "packet_analytic_truth": packet_truth(),
        "no_oscillator_controls": controls,
        "control_cycle_burst_seed_subset": list(range(100)),
        "review_r1_scoring_contract": {"core_start_sample": "guard+tolerance_samples+2",
            "core_end_sample_exclusive": "N-guard-tolerance_samples-2",
            "pairing": "one-to-one by family and polarity/direction within tolerance using context rows",
            "edge_rule": "a pair with exactly one member in the core is censored on both sides; matched pairs require both members in core",
            "denominators": "eligible_truth=core_truth-crossing_edge_truth; eligible_detected=core_detected-crossing_edge_detected; matched+missed=eligible_truth; matched+extra=eligible_detected",
            "counts": "retain raw core, eligible and crossing-edge-censored counts separately"},
        "targeted_fixtures": {
            "flat_uv": [0, 5], "affine_uv": "5+0.2*t", "near_flat_uv": "5+1e-10*sin(2*pi*8*t)",
            "short_n_samples": [2, 20], "spike": "one +100uv sample at15s on zero baseline",
            "step": "0uv before15s, 20uv from15s", "clipped": "clip 20*sin(2*pi*8*t) to[-8,8]uv",
            "gain_offset_polarity": ["x", "2*x+7", "-x"],
            "native_reference": "four native 250Hz contacts: x0=20sin(2pi8t), x1=10sin(2pi8t+pi/5), x2=5sin(2pi5t), x3=3sin(2pi5t+pi/3); compare original and common-average references, and x0-x1 pair",
            "line_hz": [50, 60], "line_amplitude_uv": 20,
            "gap": "30s 8Hz sine; invalid samples[3000:3250); whole support cannot span",
            "clock_reset": "two distinct 15s timing segments with second segment resetting to0; no matching across segments",
            "plateau_direct_sign": "unit derivative arrays: adjacent opposite signs, maximal zero run, unqualified one-sample flank",
            "zero_valid_duration": "all-invalid mask, rate null"},
        "measurements": {"stationary": "max native sample localization error by family with exact denominator", "nonstationary": "signed bias, missed/extra counts and boundary error by fixture", "noise_and_artifact": "accepted derivative landmarks / guarded valid minute; cycle and burst detections labeled false only for no-oscillator controls, reported per generator, library, band, and 100 fixed trials", "packets": "hit if burst interval intersects known packet; false burst if no intersection, with fixed 10 trials per noise level", "matching": "directional fractions, 2m/(nA+nB), signed/absolute lag, before/after counts, common duration"},
        "stationary_scoring_edge": {"interior_start_sample": "guard+4", "interior_end_sample_exclusive": "N-guard-4", "pair_tolerance_samples": 2, "reason": "ensure root and detector may differ by2 samples at evaluation edge without artificial missed/extra"},
        "hard_gates": {"stationary_max_error_samples": 2, "affine_abstention": True,
                       "accepted_support_crosses_gap": False, "units": "sample/second/microvolt and derivative units correct",
                       "matching": "one-to-one maximum-cardinality minimum-total-absolute-error, explicit overflow and unknown-clock abstention, null empty-empty"},
        "failure_policy": "retain failed settings and exclude failed branches from future confirmatory use; no threshold tuning after freeze",
        "real_smoke": "only input/exposed-fixture.npz after every synthetic hard gate passes; curator JSON remains outside numeric discovery"
    }
    return protocol


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT)
    destination = parser.parse_args().output
    if destination.exists():
        raise SystemExit(f"Refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    destination.write_bytes(payload)
    print(f"{destination} {len(payload)} bytes sha256={hashlib.sha256(payload).hexdigest()}")
