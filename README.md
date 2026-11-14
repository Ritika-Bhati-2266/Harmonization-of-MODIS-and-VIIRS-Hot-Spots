# Ember Calendar

**One consistent record of when and where Earth burns.**

Ember Calendar is a Streamlit web application that harmonizes NASA FIRMS active-fire
hotspots from MODIS (Terra/Aqua, 2000–present) and VIIRS (Suomi NPP, NOAA-20/21,
2012–present) into a single monthly burning-activity series on a 0.25° grid. Users pick an
area of interest, a date range and a month, then get:

- a year × month **burning-activity calendar heatmap** (cividis by default, viridis optional),
- the selected month compared with its **historical median**, with the percentage anomaly,
- regional totals and a **downloadable CSV** of the harmonized monthly counts, including the
  MODIS and VIIRS contributions and the calibration ratio used for each cell,
- the **VIIRS-to-MODIS calibration fit** and diagnostics in the sidebar.

Built for the 2026 NASA Space Apps Challenge, *Harmonization of MODIS and VIIRS Hot Spots*.
Target users: early-warning and emergency responders, scientists, land managers and
firefighters.

## Quick start

Requires Python 3.10+ (tested on 3.12).

```powershell
python -m pip install -r requirements.txt

python harmonize.py --demo
streamlit run app.py
```

`--demo` generates a small **synthetic** hotspot dataset for a 2.5° × 2.5° box in central
California (2013–2026), runs the full harmonization pipeline, and writes the demo outputs to
`data/`. This exists so the application and the pipeline can be demonstrated before real
FIRMS files are available. The app also generates this demo data automatically if
`data/harmonized_monthly.csv` is missing.

> The app shows a visible "Demo mode" banner whenever the dataset is synthetic. Replace the
> demo data before judging.

## Using real NASA FIRMS data

1. Download active-fire CSVs from NASA FIRMS:
   <https://firms.modaps.eosdis.nasa.gov/download/>
   Use **MODIS Collection 6.1** (or newer) and **VIIRS 375 m** (Suomi NPP and/or NOAA-20/21).
   You can request a global or regional extract and any date range; the 2012+ period is
   required for the MODIS/VIIRS overlap calibration.
2. Run the pipeline with the downloaded files (paths with spaces must be quoted):

```powershell
python harmonize.py `
  --modis "D:\firms\modis_global_2000-2026.csv" `
  --viirs "D:\firms\viirs_snpp_global_2012-2026.csv" "D:\firms\viirs_noaa20_global_2018-2026.csv" `
  --outdir data
```

3. Restart Streamlit. The app reads `data/harmonized_monthly.csv` and `data/meta.json`.

Large global extracts can be several GB. The pipeline keeps only the columns it needs, but
for repeated global runs it is worth filtering by region/date upstream. For multi-hundred-
million-row jobs, convert the harmonized output to Parquet and load that in the app instead
of CSV (see *Limitations*).

### Command-line options

| Flag | Meaning |
| --- | --- |
| `--demo` | Generate and harmonize synthetic data (no FIRMS files needed) |
| `--modis FILE [FILE ...]` | One or more MODIS FIRMS CSV files |
| `--viirs FILE [FILE ...]` | One or more VIIRS FIRMS CSV files |
| `--outdir DIR` | Output directory (default `data`) |
| `--seed N` | Synthetic data seed (default 42) |

### Outputs

| File | Contents |
| --- | --- |
| `data/harmonized_monthly.csv` | The app's input: cell, year, month, MODIS count, VIIRS count, harmonized count, calibration ratio, source |
| `data/cell_calibration.csv` | Per-cell calibration ratio, raw ratio and number of overlap months |
| `data/harmonization_fit.png` | Scatter of VIIRS vs MODIS cell-month counts, fitted line, R², and a monthly-total time series showing the sensor transition |
| `data/meta.json` | Dataset provenance: synthetic flag, bounding box, raw/filtered counts, sensors, years, calibration statistics |
| `data/synthetic_hotspots.csv` | Demo-only raw synthetic detections (not produced for real runs) |

## Method

### 1. Quality filtering

- MODIS: keep detections with `confidence ≥ 30` (0–100 scale).
- VIIRS: confidence is nominal (`l`/`n`/`h`); map to 20/60/85 and keep `n` and `h`
  (`≥ 30`), which matches FIRMS guidance to discard low-confidence detections.
- Drop rows with missing coordinates/dates and coordinates outside valid ranges. Records
  with unknown confidence are kept (FIRMS files always provide it in practice).

### 2. Gridding and monthly aggregation

Every detection is assigned to a 0.25° cell (cell center = `floor(lon/0.25)*0.25 + 0.125`,
same for latitude). Counts are aggregated to `cell × year × month × sensor`. This removes
the resolution mismatch between MODIS (1 km) and VIIRS (375 m) and produces a stable
spatio-temporal unit for comparison.

### 3. Overlap calibration (VIIRS → MODIS)

The overlap window is the intersection of years in which both sensors have detections
(2013–2024 in the demo; 2012–present for FIRMS MODIS/VIIRS). Let `M` and `V` be the
overlap counts for a cell-month.

- Global ratio: `r_global = ΣM / ΣV` over all overlap cell-months.
- Per-cell ratio: `r_cell = ΣM / ΣV` for the cell over the overlap, used only when both
  sums are positive.
- Shrinkage: `w = n / (n + 6)`, where `n` is the number of overlap months with VIIRS > 0,
  and `r = w · r_cell + (1 − w) · r_global`. The result is clipped to `[0.1, 3.0]`.
  Cells without a usable overlap ratio fall back to `r_global`.
- Diagnostics: ordinary least squares of `M` on `V` (intercept allowed), R², and
  `r_global` are written to `meta.json` and plotted in `harmonization_fit.png`.

### 4. Building the harmonized series

`count_harmonized = M` when MODIS detected at least one hotspot in that cell-month;
otherwise `count_harmonized = r · V` using the cell's calibrated ratio. In other words,
MODIS is the reference sensor where it exists, and calibrated VIIRS fills gaps during the
MODIS era and carries the series after MODIS ends. `source` records which path was used
(`modis` or `viirs_calibrated`), and `modis_count`, `viirs_count` and `ratio` are preserved
for transparency. A single multiplicative ratio per cell makes the series continuous across
the sensor transition; no artificial jump is introduced when MODIS stops.

## App behaviour

- **Region selection:** draw a rectangle or polygon with the map's draw tool, or type west/
  south/east/north bounds in the sidebar. Bounds are clipped to the dataset extent.
- **Date range and month of interest:** both filter the calendar and the anomaly chart.
- **Calendar:** year rows × month columns, sum of harmonized hotspots across all cells in
  the selection. Blank cells mean no data, not zero.
- **Anomaly:** the latest year with data for the chosen calendar month is compared with the
  median of earlier years in the selected range (dashed line and percentage).
- **CSV download:** every selected cell-month with sensor contributions, calibration ratio
  and source flag.
- **Accessibility:** cividis is the default color ramp (perceptually uniform and
  color-vision-deficiency friendly), viridis is offered as an alternative; charts use
  colorblind-safe orange/blue accent colors and text labels in addition to color.

## Limitations and honest caveats

- MODIS (1 km, twice daily) and VIIRS (375 m, multiple platforms/overpasses) differ in
  spatial resolution, detection sensitivity, diurnal sampling and algorithm. A per-cell
  ratio makes counts comparable on average but cannot remove all small-fire, diurnal or
  biome-specific bias.
- The calibration assumes a stable MODIS/VIIRS relationship within each cell over time.
  It does not model trends in that relationship (sensor degradation, algorithm updates,
  new VIIRS platforms coming online).
- Cloud/smoke masking, terrain, view angle and sensor degradation are not corrected beyond
  the confidence filter. The series counts **active-fire detections**, not burned area or
  fire size.
- Cells with few overlap months are dominated by the global ratio, which may be inaccurate
  in regions with unusual detection behaviour.
- The most recent month can be partial; monthly totals are not normalized by month length.
- The demo dataset is synthetic and must not be interpreted as real fire activity.
- CSV is fine for regional extracts; for global multi-decade runs, the 0.25° monthly table
  can reach millions of rows and should be stored as Parquet. The app currently loads the
  full table into memory.

## Future work

Blend both sensors during overlap instead of MODIS-only, weight calibration by FRP or
confidence, add per-cell uncertainty, support VIIRS 750 m, add a downloadable hotspot-level
CSV for the selection, cache tiles for offline use, and expose a REST API for emergency
operations centres.

## Repository layout

```
app.py                    Streamlit application
harmonize.py              Synthetic generator + harmonization pipeline + CLI
requirements.txt          Python dependencies
data/                     Generated datasets, calibration table, fit plot, metadata
submission/               Submission text and 7-slide demo outline
```

## Data sources and references

- NASA FIRMS — Fire Information for Resource Management System:
  <https://firms.modaps.eosdis.nasa.gov/>
- NASA LANCE / Earthdata for near-real-time MODIS and VIIRS active-fire products.
- MODIS Collection 6.1 active fire product (MCD14ML), Giglio et al., 2016.
- VIIRS 375 m active fire product (VNP14IMG), Schroeder et al., 2014.
- NASA Space Apps Challenge 2026 challenge: *Harmonization of MODIS and VIIRS Hot Spots*.

All linked materials and the application content are in English. NASA FIRMS data are free
and open; please retain the FIRMS/Earthdata attribution when redistributing derived
products.
