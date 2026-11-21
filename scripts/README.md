# Sky data build scripts

These scripts regenerate the files in `data/` from public astronomy catalogs.
The app itself does not need them at runtime — run them only to refresh the data
(e.g. to add newly confirmed exoplanets).

## 1. Download the source catalogs into one folder (e.g. `src/`)

| File | Source | License |
|---|---|---|
| `hyg.csv` | https://raw.githubusercontent.com/astronexus/HYG-Database/main/hyg/CURRENT/hygdata_v41.csv | CC BY-SA 4.0 |
| `ngc.csv` | https://raw.githubusercontent.com/mattiaverga/OpenNGC/master/database_files/NGC.csv | CC BY-SA 4.0 |
| `addendum.csv` | https://raw.githubusercontent.com/mattiaverga/OpenNGC/master/database_files/addendum.csv | CC BY-SA 4.0 |
| `oec.csv` | https://raw.githubusercontent.com/OpenExoplanetCatalogue/oec_tables/master/comma_separated/open_exoplanet_catalogue.txt | MIT |
| `d3c/constellations.lines.json` | https://raw.githubusercontent.com/ofrohn/d3-celestial/master/data/constellations.lines.json | BSD-3-Clause |
| `d3c/constellations.json` | https://raw.githubusercontent.com/ofrohn/d3-celestial/master/data/constellations.json | BSD-3-Clause |

## 2. Build

```bash
python3 scripts/build_sky.py src data          # stars, deep-sky, exoplanets, constellation lines
python3 scripts/build_stories.py data/sky-stories.json   # hand-written stories (stories_*.py)
```

Outputs: `sky-stars.b64.txt`, `sky-stars-info.json`, `sky-deep.json`, `sky-exo.json`,
`sky-conlines.json`, `sky-stories.json`.

Asteroid orbits (`ASTEROID_DATA` in `index.html`) come from the IAU Minor Planet Center.

## Attribution
When redistributing, keep credits for HYG Database (David Nash / astronexus), OpenNGC (Mattia Verga),
Open Exoplanet Catalogue (Hanno Rein et al.) and d3-celestial (Olaf Frohn), per their licenses.
