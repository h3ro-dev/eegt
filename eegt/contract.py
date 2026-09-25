"""The discovery boundary deliberately has no identity or context fields."""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class NumericRecording:
    samples_uv: np.ndarray  # channels x time, in microvolts
    sample_rate_hz: float
    valid_samples: np.ndarray  # engineering integrity only, channels x time

    def __post_init__(self):
        x = np.asarray(self.samples_uv)
        mask = np.asarray(self.valid_samples)
        if x.ndim != 2 or min(x.shape) < 1 or x.dtype.kind not in "fiu":
            raise ValueError("samples must be a nonempty numeric channels-by-time matrix")
        if not np.isfinite(self.sample_rate_hz) or self.sample_rate_hz <= 80:
            raise ValueError("sampling rate must exceed 80 Hz for the 1-40 Hz analysis")
        if mask.dtype.kind != "b" or mask.shape != x.shape:
            raise ValueError("validity mask must be Boolean and match samples")
        if np.any(mask & ~np.isfinite(x)):
            raise ValueError("nonfinite samples cannot be marked valid")
        # Own immutable copies; callers cannot mutate inputs after acceptance.
        x = np.array(x, dtype=np.float64, copy=True)
        mask = np.array(mask, dtype=bool, copy=True)
        x.flags.writeable = False
        mask.flags.writeable = False
        object.__setattr__(self, "samples_uv", x)
        object.__setattr__(self, "valid_samples", mask)

    @classmethod
    def from_payload(cls, payload):
        expected = {"samples_uv", "sample_rate_hz", "valid_samples"}
        if not isinstance(payload, dict) or set(payload) != expected:
            raise ValueError("numeric boundary accepts only samples_uv, sample_rate_hz, valid_samples")
        return cls(**payload)


def mw75_decoded(samples_uv, *, sample_rate_hz, channel_order, expected_channel_order,
                 units, sample_integrity):
    """Accept an already decoded Research Kit array, not a Bluetooth transport.

    Caller must explicitly supply verified contact order and packet integrity.
    Channel names are checked here and discarded before the model boundary.
    REF, DRL, IMU, counters and clinical/identity metadata are not model channels.
    """
    x = np.asarray(samples_uv)
    if x.ndim != 2 or x.shape[0] != 12:
        raise ValueError("MW75 decoded EEG requires exactly 12 channels")
    if sample_rate_hz != 500 or units != "uV":
        raise ValueError("MW75 boundary requires explicitly calibrated uV at 500 Hz")
    if len(channel_order) != 12 or len(set(channel_order)) != 12:
        raise ValueError("12 distinct ordered contacts are required")
    if tuple(channel_order) != tuple(expected_channel_order):
        raise ValueError("channel order differs from verified capture contract")
    integrity = np.asarray(sample_integrity)
    if integrity.dtype.kind != "b" or integrity.shape != (x.shape[1],):
        raise ValueError("one explicit integrity Boolean per decoded sample is required")
    mask = np.broadcast_to(integrity, x.shape) & np.isfinite(x)
    return NumericRecording(x, 500.0, mask)
