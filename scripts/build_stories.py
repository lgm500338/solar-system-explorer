import json, re, sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stories_stars import STARS
from stories_deep import MESSIER, DEEP_BY_ID, CONSTELLATIONS
assert len(CONSTELLATIONS) == 88, len(CONSTELLATIONS)
fix = lambda s: re.sub(r'(stars|together)\. (?=[a-z])', r'\1 ', s)
out = {
 'star': {k: [v[0], fix(v[1])] for k, v in STARS.items()},
 'm': {str(k): [v[0], fix(v[1])] for k, v in MESSIER.items()},
 'id': {k: [v[0], fix(v[1])] for k, v in DEEP_BY_ID.items()},
 'con': [[a, b] for a, b in CONSTELLATIONS],
}
json.dump(out, open(sys.argv[1], 'w'), ensure_ascii=False, separators=(',', ':'))
print(len(out['star']), len(out['m']), len(out['id']), len(out['con']))
for k in ('2','10','46','53','62'): print(out['m'][k][1])
