"""Independently compare decoded volts with native EEGLAB float32 values.

This checks digital unit conversion, not the original amplifier's physical
calibration. Source metadata declares the native values in microvolts.
"""
import argparse
import json
from pathlib import Path
import sqlite3

import mne
import numpy as np
from mne._fiff.constants import FIFF

from .acquire import ROOT,digest
from .corpus import atomic_json,safe_path


def verify_conversion(raw,fdt_path,picks):
    n_ch=len(raw.ch_names);n_time=raw.n_times
    if fdt_path.stat().st_size!=n_ch*n_time*4:raise ValueError('native FDT byte layout disagrees with decoder shape')
    if any(raw.info['chs'][i]['unit']!=FIFF.FIFF_UNIT_V for i in picks):raise ValueError('decoder did not declare EEG in volts')
    direct=np.memmap(fdt_path,dtype='<f4',mode='r',shape=(n_time,n_ch))
    errors=[];checked=0
    for start in sorted(set([0,max(0,n_time//2-16),max(0,n_time-32)])):
        stop=min(n_time,start+32)
        native=np.asarray(direct[start:stop,picks],dtype=np.float64).T
        decoded=raw.get_data(picks=picks,start=start,stop=stop)*1e6
        if not np.array_equal(np.isfinite(native),np.isfinite(decoded)):raise ValueError('native and decoded finite masks differ')
        finite=np.isfinite(native)
        if not np.allclose(native[finite],decoded[finite],rtol=1e-12,atol=1e-9):raise ValueError('native microvolts do not match decoded volts times 1e6')
        errors.append(float(np.max(np.abs(native[finite]-decoded[finite]))) if finite.any() else 0.)
        checked+=int(finite.sum())
    del direct
    if not checked:raise ValueError('no finite native values in conversion probes')
    return dict(checked_values=checked,maximum_absolute_error_uv=max(errors),native_dtype='little-endian float32',decoder_unit='V',conversion_to_uv=1e6)


def run(root=ROOT):
    root=Path(root);db=sqlite3.connect(root/'results/corpus-v1/corpus.sqlite');db.row_factory=sqlite3.Row
    out=dict(schema='eegt-digital-calibration/v1',corpus_sha256=digest(root/'results/corpus-v1/corpus.sqlite'),code_sha256=digest(Path(__file__)),mne_version=mne.__version__,records=[],limitation='Digital decoding/unit conversion checked at start, middle and end; physical sensor calibration and undocumented acquisition errors remain unknown.')
    for rec in db.execute('SELECT * FROM recordings ORDER BY dataset_id,source_subject').fetchall():
        row=dict(recording_id=rec['recording_id'],status='SOURCE_QUARANTINED')
        if rec['status']=='QUALIFIED':
            files=db.execute('SELECT * FROM source_files WHERE recording_id=?',(rec['recording_id'],)).fetchall()
            paths={Path(f['path']).suffix:safe_path(root/'data/cache'/rec['dataset_id'],f['path']) for f in files}
            for f in files:
                if digest(safe_path(root/'data/cache'/rec['dataset_id'],f['path']))!=f['sha256']:raise ValueError('raw changed before digital conversion check')
            raw=mne.io.read_raw_eeglab(paths['.set'],preload=False,verbose='ERROR')
            try:
                channel_rows=db.execute("SELECT name FROM channels WHERE recording_id=? AND UPPER(type)='EEG' ORDER BY channel_index",(rec['recording_id'],)).fetchall()
                picks=[raw.ch_names.index(c['name']) for c in channel_rows]
                row.update(status='PASS',**verify_conversion(raw,paths['.fdt'],picks))
            finally:raw.close()
        out['records'].append(row)
        print(json.dumps(row),flush=True)
    db.close();atomic_json(root/'results/corpus-v1/calibration.json',out,immutable=True)
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args();run(a.root)
