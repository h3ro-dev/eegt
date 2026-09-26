"""Prepare only the frozen first 30 seconds of accepted EESM19 development input."""
import hashlib
import json
from pathlib import Path
import numpy as np


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def array_hash(array):
    from eegt.pretrained_study import array_hash as prepared_array_hash
    return prepared_array_hash(array)


def read_window(raw_root,record,count=15000):
    """Decode verified little-endian FDT frames; caller enforces scientific freeze."""
    root=Path(raw_root).resolve()
    source=record['fdt_source']
    path=(root/source['path']).resolve()
    if not path.is_relative_to(root):
        raise ValueError('source escapes raw root')
    header=record['header']
    if (record['status']!='QUALIFIED' or record['stored_units']!='uV'
            or record['sample_rate_hz']!=500 or header['srate_hz']!=500
            or header['trials']!=1 or header['nbchan']!=13):
        raise ValueError('unsupported engineering source contract')
    if path.stat().st_size!=source['bytes'] or digest(path)!=source['sha256']:
        raise ValueError('changed FDT source')
    if source['bytes']!=header['pnts']*header['nbchan']*4 or header['pnts']<count:
        raise ValueError('incomplete frame support')
    picks=record['native_eeg_pick_indices']
    if len(picks)!=12 or len(set(picks))!=12 or any(i<0 or i>=13 for i in picks):
        raise ValueError('invalid native ear picks')
    channels={c['index_0based']:c for c in record['channels']}
    names=[header['channel_names'][i] for i in picks]
    if any(channels[i]['name']!=names[j] or channels[i]['type']!='EEG'
           or channels[i]['units']!='uV' or not channels[i]['included_in_ear_eeg']
           for j,i in enumerate(picks)):
        raise ValueError('undeclared or non-EEG channel')
    data=np.memmap(path,dtype='<f4',mode='r',shape=(header['pnts'],13),order='C')
    samples=np.array(data[:count,picks].T,dtype=np.float64,order='C')
    del data
    valid=np.isfinite(samples)
    # Preserve source-scan missing intervals and separate conservative zero-tail
    # exclusions. Neither is relabeled as a proved acquisition-clock gap.
    for row,index in enumerate(picks):
        for interval in channels[index]['missing_intervals']:
            start=max(0,int(interval['start_sample']))
            stop=min(count,int(interval['stop_sample']))
            if stop>start:
                valid[row,start:stop]=False
    for interval in record['common_zero_intervals']:
        start=max(0,int(interval['start_sample']))
        stop=min(count,int(interval['stop_sample']))
        if stop>start:
            valid[:,start:stop]=False
    return samples,valid,names


def prepare(root,raw_root,contract_path,destination):
    from eegt.validation_intake import require_accepted_freeze
    root=Path(root)
    # This is called before opening source samples; raw preparation is an empirical
    # action even though neither model nor detector is invoked here.
    require_accepted_freeze(root=root,phase='events')
    seal=json.loads((root/'results/013/RUN-SOURCE-MANIFEST.json').read_text())
    own_path=Path(__file__).resolve().relative_to(root.resolve()).as_posix()
    if seal['inputs'].get(own_path)!=digest(__file__):
        raise ValueError('engineering preparer is not in accepted freeze')
    contract_path=Path(contract_path).resolve()
    relative=contract_path.relative_to(root.resolve()).as_posix()
    if seal['inputs'].get(relative)!=digest(contract_path):
        raise ValueError('engineering contract is not in accepted freeze')
    contract=json.loads(contract_path.read_text())
    if contract['schema']!='eegt-013-engineering-input-contract/v1':
        raise ValueError('unknown engineering input schema')
    records=contract['records']
    if (len(records)!=2 or {r['source_session'] for r in records}!={'ses-005','ses-006'}
            or {r['source_person'] for r in records}!={'sub-001'}
            or contract['selection']!={'start_sample':0,'samples':15000,'seconds':30,'adaptive_replacement':False}):
        raise ValueError('engineering selection changed')
    destination=Path(destination).resolve()
    destination.relative_to(root.resolve())
    if destination.exists():
        raise FileExistsError(destination)
    arrays=[];masks=[];receipts=[]
    for record in sorted(records,key=lambda r:r['source_session']):
        samples,valid,names=read_window(raw_root,record)
        arrays.append(samples);masks.append(valid)
        receipts.append(dict(recording_id=record['recording_id'],source=record['fdt_source'],
            source_subject='001',session=record['source_session'].removeprefix('ses-'),
            channel_names=names,start_sample=0,stop_sample=15000,sample_rate_hz=500,
            native_array_sha256=array_hash(samples),valid_mask_sha256=array_hash(valid),
            invalid_samples_per_channel=(~valid).sum(axis=1).tolist(),
            source_mask_set_sha256=record['finite_mask_set_sha256']))
    destination.mkdir(parents=True)
    archive=destination/'engineering-native.npz'
    np.savez_compressed(archive,samples_uv=np.stack(arrays),valid=np.stack(masks))
    receipt=dict(schema='eegt-013-engineering-preparation/v1',status='PREPARED',
        contract_sha256=digest(contract_path),run_source_manifest_sha256=digest(root/'results/013/RUN-SOURCE-MANIFEST.json'),
        array_path=archive.relative_to(root.resolve()).as_posix(),array_sha256=digest(archive),records=receipts,
        sample_rate_hz=500,channel_names=receipts[0]['channel_names'],
        inference='DESCRIPTIVE_ONLY',encoder_status='NOT_EVALUATED_FOR_12_CONTACTS')
    (destination/'engineering-prepared.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    return receipt


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True)
    parser.add_argument('--raw-root',required=True)
    parser.add_argument('--contract',required=True)
    parser.add_argument('--destination',required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.root,args.raw_root,args.contract,args.destination),
                     indent=2,allow_nan=False))
