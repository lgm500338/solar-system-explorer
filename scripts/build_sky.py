#!/usr/bin/env python3
"""우주로 하늘 데이터 빌드: HYG(별) + OpenNGC(은하·성운·성단) + Open Exoplanet Catalogue(외계행성)
출력: <out>/sky-stars.bin, sky-stars-info.json, sky-deep.json, sky-exo.json
"""
import csv, json, math, struct, sys, os

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)

CON = ["And","Ant","Aps","Aql","Aqr","Ara","Ari","Aur","Boo","CMa","CMi","CVn","Cae","Cam","Cap","Car","Cas","Cen","Cep","Cet","Cha","Cir","Cnc","Col","Com","CrA","CrB","Crt","Cru","Crv","Cyg","Del","Dor","Dra","Equ","Eri","For","Gem","Gru","Her","Hor","Hya","Hyi","Ind","LMi","Lac","Leo","Lep","Lib","Lup","Lyn","Lyr","Men","Mic","Mon","Mus","Nor","Oct","Oph","Ori","Pav","Peg","Per","Phe","Pic","PsA","Psc","Pup","Pyx","Ret","Scl","Sco","Sct","Ser","Sex","Sge","Sgr","Tau","Tel","TrA","Tri","Tuc","UMa","UMi","Vel","Vir","Vol","Vul"]
CON_IDX = {c.lower(): i for i, c in enumerate(CON)}

def con_index(c):
    return CON_IDX.get((c or '').strip().lower(), -1)

def fnum(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None

# ---------------- 별 (HYG v4.1) ----------------
stars = []
with open(os.path.join(SRC, 'hyg.csv'), newline='') as f:
    for r in csv.DictReader(f):
        if r['id'] == '0':
            continue  # 태양 제외
        mag = fnum(r['mag'])
        if mag is None:
            continue
        ra = fnum(r['ra']) * 15.0   # 시 -> 도
        dec = fnum(r['dec'])
        ci = fnum(r['ci'])
        dist_pc = fnum(r['dist'])
        ly = 0 if (dist_pc is None or dist_pc >= 99999 or dist_pc <= 0) else dist_pc * 3.26156
        if r['proper']:
            label = r['proper']
        elif r['bayer']:
            label = f"{r['bayer']} {r['con']}"
        elif r['flam']:
            label = f"{r['flam']} {r['con']}"
        elif r['hip']:
            label = f"HIP {r['hip']}"
        elif r['hd']:
            label = f"HD {r['hd']}"
        elif r['gl']:
            label = r['gl']
        else:
            label = f"HYG {r['id']}"
        stars.append(dict(ra=ra, dec=dec, mag=mag, ci=0.65 if ci is None else ci, ly=ly,
                          label=label, proper=r['proper'], spect=r['spect'] or '',
                          con=con_index(r['con']), hip=r['hip'], lum=fnum(r['lum'])))
stars.sort(key=lambda s: s['mag'])  # 밝은 별이 앞

import base64
_buf = bytearray()
class _W:
    def write(self, b): _buf.extend(b)
f = _W()
if True:
    for s in stars:
        ra16 = int(round(s['ra'] / 360.0 * 65535)) & 0xFFFF
        dec16 = max(-32767, min(32767, int(round(s['dec'] / 90.0 * 32767))))
        mag8 = max(0, min(255, int(round((s['mag'] + 2.0) * 10))))
        ci8 = max(0, min(255, int(round((s['ci'] + 0.5) * 80))))
        f.write(struct.pack('<HhBB', ra16, dec16, mag8, ci8))

with open(os.path.join(OUT, 'sky-stars.b64.txt'), 'w') as fo:
    fo.write(base64.b64encode(bytes(_buf)).decode('ascii'))

info = []
for s in stars:
    ly = (round(s['ly'], 2) if s['ly'] < 100 else int(round(s['ly']))) if s['ly'] else 0
    lum = round(s['lum'], 3 if s['lum'] and s['lum'] < 10 else 0) if s['lum'] else 0
    if lum and lum == int(lum):
        lum = int(lum)
    info.append([s['label'], ly, s['spect'][:8], s['con'], lum, None, int(s['hip']) if s['hip'] else 0])

# ---------------- 외계행성 (Open Exoplanet Catalogue) ----------------
def hms(s):
    p = s.split()
    return (float(p[0]) + float(p[1]) / 60 + float(p[2]) / 3600) * 15.0

def dms(s):
    p = s.split()
    sign = -1 if p[0].startswith('-') else 1
    return sign * (abs(float(p[0])) + float(p[1]) / 60 + float(p[2]) / 3600)

hosts = {}
order = []
with open(os.path.join(SRC, 'oec.csv'), newline='') as f:
    lines = [l for l in f if not l.startswith('#')]
for r in csv.reader(lines):
    if len(r) < 25 or r[24].strip() != 'Confirmed planets':
        continue
    name, ra_s, dec_s = r[0], r[16], r[17]
    if not ra_s or not dec_s:
        continue
    try:
        ra, dec = hms(ra_s), dms(dec_s)
    except (ValueError, IndexError):
        continue
    host = name.rsplit(' ', 1)[0] if ' ' in name else name
    if host not in hosts:
        dist = fnum(r[18])
        hosts[host] = dict(ra=ra, dec=dec, ly=int(round(dist * 3.26156)) if dist else 0,
                           temp=fnum(r[22]), rad=fnum(r[20]), planets=[])
        order.append(host)
    def rnd(v, n):
        return None if v is None else round(v, n)
    hosts[host]['planets'].append([
        name, rnd(fnum(r[2]), 4), rnd(fnum(r[3]), 4), rnd(fnum(r[4]), 3), rnd(fnum(r[5]), 4),
        int(r[14]) if r[14].isdigit() else None, r[13] or '', rnd(fnum(r[11]), 0)])

# HYG 별과 외계행성 모항성 매칭(가까운 별: 1.5 arcmin 이내 + 밝은 별) -> 별 정보에 행성 수 표시
def unit(ra, dec):
    a, d = math.radians(ra), math.radians(dec)
    return (math.cos(d) * math.cos(a), math.cos(d) * math.sin(a), math.sin(d))

grid = {}
for idx, s in enumerate(stars):
    if s['mag'] > 10:
        continue
    key = (int(s['ra']), int(s['dec'] + 90))
    grid.setdefault(key, []).append(idx)
host_star = {}
cos_lim = math.cos(math.radians(1.5 / 60))
for h in order:
    H = hosts[h]
    u = unit(H['ra'], H['dec'])
    best = None
    for dra in (-1, 0, 1):
        for ddec in (-1, 0, 1):
            for idx in grid.get(((int(H['ra']) + dra) % 360, int(H['dec'] + 90) + ddec), []):
                s = stars[idx]
                v = unit(s['ra'], s['dec'])
                c = u[0] * v[0] + u[1] * v[1] + u[2] * v[2]
                if c > cos_lim and (best is None or c > best[0]):
                    best = (c, idx)
    if best:
        host_star[h] = best[1]

exo = []
for k, h in enumerate(order):
    H = hosts[h]
    si = host_star.get(h, -1)
    if si >= 0:
        info[si][5] = k  # 별 정보 6번째 칸 = 외계행성계 인덱스
    exo.append([h, round(H['ra'], 4), round(H['dec'], 4), H['ly'], H['temp'] and int(H['temp']), si, H['planets'], H['rad'] and round(H['rad'], 3)])

with open(os.path.join(OUT, 'sky-stars-info.json'), 'w') as f:
    json.dump(info, f, ensure_ascii=False, separators=(',', ':'))
with open(os.path.join(OUT, 'sky-exo.json'), 'w') as f:
    json.dump(exo, f, ensure_ascii=False, separators=(',', ':'))

# ---------------- 은하·성운·성단 (OpenNGC) ----------------
KEEP = {'G': 0, 'GPair': 0, 'GTrpl': 0, 'GGroup': 0,
        'OCl': 1, '*Ass': 1, 'GCl': 2,
        'Neb': 3, 'HII': 3, 'EmN': 3, 'RfN': 3, 'Cl+N': 3, 'DrkN': 3,
        'PN': 4, 'SNR': 5, 'Nova': 5}

def sexa_ra(s):
    h, m, sec = s.split(':')
    return (float(h) + float(m) / 60 + float(sec) / 3600) * 15

def sexa_dec(s):
    d, m, sec = s.split(':')
    sign = -1 if d.startswith('-') else 1
    return sign * (abs(float(d)) + float(m) / 60 + float(sec) / 3600)

def pretty(name):
    for pre in ('NGC', 'IC'):
        if name.startswith(pre) and name[len(pre):len(pre)+4].isdigit():
            rest = name[len(pre):].lstrip('0')
            return f"{pre} {rest}"
    return name

deep = []
seen_m = set()
for fn in ('ngc.csv', 'addendum.csv'):
    with open(os.path.join(SRC, fn), newline='') as f:
        for r in csv.DictReader(f, delimiter=';'):
            t = r['Type']
            m = r['M'].lstrip('0') if r['M'] else ''
            if t not in KEEP and not (m == '40'):
                continue
            if not r['RA'] or not r['Dec']:
                continue
            if m:
                if m in seen_m:
                    continue
                seen_m.add(m)
            mag = fnum(r['V-Mag']) or fnum(r['B-Mag'])
            z = fnum(r['Redshift'])
            deep.append([pretty(r['Name']), KEEP.get(t, 1), round(sexa_ra(r['RA']), 4), round(sexa_dec(r['Dec']), 4),
                         None if mag is None else round(mag, 1), int(m) if m else 0,
                         (r['Common names'] or '').split(',')[0], con_index(r['Const']),
                         fnum(r['MajAx']) and round(fnum(r['MajAx']), 1), z and round(z, 5)])
deep.sort(key=lambda d: (0 if d[5] else 1, d[4] if d[4] is not None else 99))
with open(os.path.join(OUT, 'sky-deep.json'), 'w') as f:
    json.dump(deep, f, ensure_ascii=False, separators=(',', ':'))

n_pl = sum(len(e[6]) for e in exo)
print(f"stars={len(stars)} deep={len(deep)} exo_hosts={len(exo)} exo_planets={n_pl} matched_hosts={len(host_star)} messier={len(seen_m)}")

# ---------------- 별자리 선 (d3-celestial, BSD-3) ----------------
lines = json.load(open(os.path.join(SRC, 'd3c', 'constellations.lines.json')))
cinfo = json.load(open(os.path.join(SRC, 'd3c', 'constellations.json')))
def nra(x): return round(x + 360 if x < 0 else x, 3)
con_out = {}
for f in cinfo['features']:
    ab = f['id'][:3] if f['id'].startswith('Ser') else f['id']
    if ab not in con_out:
        d = f['properties']['display']
        con_out[ab] = {'c': [nra(d[0]), round(d[1], 2)], 'l': []}
for f in lines['features']:
    ab = f['id'][:3] if f['id'].startswith('Ser') else f['id']
    for poly in f['geometry']['coordinates']:
        con_out[ab]['l'].append([[nra(p[0]), round(p[1], 3)] for p in poly])
missing = [c for c in CON if c not in con_out]
with open(os.path.join(OUT, 'sky-conlines.json'), 'w') as fo:
    json.dump(con_out, fo, separators=(',', ':'))
print('constellations', len(con_out), 'missing', missing)
