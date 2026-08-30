#!/usr/bin/env python3
import argparse, json, html, re, sys
from pathlib import Path

SECRET_PATH = re.compile(r'(?:^|[._-])(token|secret|password|passwd|api[_-]?key|authorization|cookie)(?:$|[._-])', re.I)
SIMPLE_KEY = re.compile(r'^[A-Za-z_][A-Za-z0-9_-]*$')

def child_path(path, key):
    key = str(key)
    if SIMPLE_KEY.fullmatch(key):
        return f'{path}.{key}' if path else key
    return f'{path}[{json.dumps(key, ensure_ascii=False)}]' if path else json.dumps(key, ensure_ascii=False)

def kind(v):
    if v is None: return 'null'
    if isinstance(v, bool): return 'bool'
    if isinstance(v, int): return 'int'
    if isinstance(v, float): return 'float'
    if isinstance(v, str): return 'string'
    if isinstance(v, dict): return 'object'
    if isinstance(v, list): return 'array'
    return type(v).__name__

def strict_json_loads(text):
    def unique_object(pairs):
        out={}
        for key,value in pairs:
            if key in out:
                raise ValueError(f'duplicate JSON object key: {key}')
            out[key]=value
        return out
    def reject_constant(value):
        raise ValueError(f'non-finite JSON number not allowed: {value}')
    return json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)

def load_records(path):
    text = Path(path).read_text(encoding='utf-8')
    if Path(path).suffix.lower() == '.jsonl':
        records=[]
        for line_no,line in enumerate(text.splitlines(),1):
            if not line.strip(): continue
            try: records.append(strict_json_loads(line))
            except ValueError as e: raise ValueError(f'line {line_no}: {e}') from e
        return records
    data = strict_json_loads(text)
    return data if isinstance(data, list) else [data]

def walk(v, path, seen, stats):
    seen.add(path)
    row = stats.setdefault(path, {'types':{}, 'present':0, 'examples':[]})
    t = kind(v); row['types'][t] = row['types'].get(t,0)+1
    if len(row['examples']) < 3 and not isinstance(v,(dict,list)):
        example = '<redacted>' if SECRET_PATH.search(path) else str(v)[:80]
        row['examples'].append(example)
    if isinstance(v, dict):
        for k, x in v.items():
            walk(x, child_path(path, k), seen, stats)
    elif isinstance(v, list):
        for x in v:
            walk(x, f'{path}[]', seen, stats)

def infer(records):
    stats = {}
    total = len(records)
    for rec in records:
        seen = set()
        walk(rec, '$', seen, stats)
        for p in seen:
            stats[p]['present'] += 1
    for p, row in stats.items():
        row['required_ratio'] = round(row['present']/total, 4) if total else 0
    return {'records': total, 'paths': stats}

def compare(a, b):
    out = []
    for p in sorted(set(a['paths']) | set(b['paths'])):
        x, y = a['paths'].get(p), b['paths'].get(p)
        if x is None:
            out.append({'path':p,'change':'added','severity':'info'})
            continue
        if y is None:
            out.append({'path':p,'change':'removed','severity':'high'})
            continue
        xt, yt = set(x['types']), set(y['types'])
        if xt != yt:
            out.append({'path':p,'change':f'types {sorted(xt)} → {sorted(yt)}','severity':'high'})
        drift = abs(x['required_ratio'] - y['required_ratio'])
        if drift >= .25:
            out.append({'path':p,'change':f"required {x['required_ratio']:.0%} → {y['required_ratio']:.0%}",'severity':'medium'})
    return out

def render(report, changes=None):
    if changes is None:
        rows=''.join(f"<tr><td>{html.escape(p)}</td><td>{html.escape(', '.join(r['types']))}</td><td>{r['required_ratio']:.0%}</td></tr>" for p,r in sorted(report['paths'].items()))
        body=f"<p>{report['records']} records</p><table><tr><th>path</th><th>types</th><th>present</th></tr>{rows}</table>"
    else:
        rows=''.join(f"<tr><td>{html.escape(x['severity'])}</td><td>{html.escape(x['path'])}</td><td>{html.escape(x['change'])}</td></tr>" for x in changes)
        body=f"<p>{len(changes)} drift signals</p><table><tr><th>severity</th><th>path</th><th>change</th></tr>{rows}</table>"
    return '<!doctype html><meta charset="utf-8"><style>body{font:15px system-ui;max-width:1100px;margin:auto;padding:40px;background:#f0eadf}table{width:100%;border-collapse:collapse;background:#fffaf2}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left}th{background:#e4eadc}</style><h1>Data Shape Guard</h1>'+body

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    i=sub.add_parser('infer'); i.add_argument('file'); i.add_argument('--json',default='shape.json'); i.add_argument('--html',default='shape.html')
    c=sub.add_parser('compare'); c.add_argument('baseline'); c.add_argument('current'); c.add_argument('--json',default='shape-drift.json'); c.add_argument('--html',default='shape-drift.html')
    a=ap.parse_args()
    try:
        if a.cmd=='infer':
            r=infer(load_records(a.file)); Path(a.json).write_text(json.dumps(r,ensure_ascii=False,indent=2)); Path(a.html).write_text(render(r),encoding='utf-8'); print(f"records={r['records']} paths={len(r['paths'])}")
        else:
            ra=infer(load_records(a.baseline)); rb=infer(load_records(a.current)); ch=compare(ra,rb); Path(a.json).write_text(json.dumps(ch,ensure_ascii=False,indent=2)); Path(a.html).write_text(render(rb,ch),encoding='utf-8'); print(f'drift={len(ch)}')
    except (ValueError, json.JSONDecodeError) as e:
        print(f'ERROR: {e}',file=sys.stderr); return 2
    return 0
if __name__=='__main__': raise SystemExit(main())
