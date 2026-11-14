# Ember Calendar

**One consistent record of when and where Earth burns.**

Ember Calendar is a Streamlit web application that harmonizes NASA FIRMS active-fire
hotspots from MODIS (Terra/Aqua) and VIIRS (Suomi NPP) into a single monthly
burning-activity series on a 0.25° grid. The bundled deployment covers **Argentina,
January 2012–October 2026** (3.54 million quality-filtered detections); the pipeline can be
pointed at any FIRMS regional extract. Users pick an area of interest, a date range and a
month, then get:

- a year × month **burning-activity calendar heatmap** (cividis by default, viridis optional),
- the selected month compared with its **historical median**, with the percentage anomaly,
- two switchable metrics — **fire cell-days** (platform-independent, one detection per cell
  per sensor per day) and **raw hotspot detections** — both calibrated and both exported,
- regional totals, a **downloadable monthly CSV**, and an optional **hotspot-level CSV** for
  the selected area and period,
- **calibration reliability** information: per-cell ratio, overlap months, and whether a
  cell used a cell-specific or the global ratio,
- the **VIIRS-to-MODIS calibration fit** and diagnostics in the sidebar.

Built for the 2026 NASA Space Apps Challenge, *Harmonization of MODIS and VIIRS Hot Spots*.
Target users: early-warning and emergency responders, scientists, land managers and
firefighters.

**Live app:** <https://harmonization-of-modis-and-viirs-hot.onrender.com> (free Render
instance; the first visit may take about 30 seconds while it wakes up).

## Quick start

Requires Python 3.10+ (tested on 3.12).

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

The repository already contains the harmonized Argentina table, so the quick start needs no
downloads. To regenerate the optional synthetic demo (small 2.5° × 2.5° box in central
California, 2013–2026) instead:

```powershell
python harmonize.py --demo
```

`--demo` writes CSV, Parquet, a calibration table, a fit plot and a small hotspot-level file.
If no harmonized file is present at all, the app falls back to this demo and shows a visible
"Demo mode" banner. The submitted deployment uses the real Argentina extract.

Run the unit tests with:

```powershell
python -m unittest discover -s tests -v
```

## Deploying

The live app runs on Render (free web service, Python 3):

- Build command: `pip install -r requirements.txt`
- Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
- First visit after idle may take ~30 seconds while the free instance wakes up.

The committed `data/harmonized_monthly.parquet` (2.4 MB), `data/harmonized_monthly.csv`
(21 MB), `data/cell_calibration.csv`, `data/meta.json` and `data/harmonization_fit.png` are
enough for the app to start without running the pipeline. Do **not** commit the raw FIRMS
CSVs or a multi-million-row hotspot file. The app only falls back to a synthetic demo when
no harmonized file exists.

After deploying, open the URL in a private browser window and confirm the map, calendar,
anomaly chart and CSV download work before submitting the link.

## The bundled real dataset

The submitted deployment uses NASA FIRMS detections for **Argentina**, downloaded from the
public FIRMS archive mirror
<https://huggingface.co/datasets/hotspot-harmonizers/firms>:

| Item | Value |
| --- | --- |
| Period | January 2012–October 2026, local time (UTC−3) |
| Sensors | MODIS Terra/Aqua + VIIRS Suomi NPP 375 m |
| Quality-filtered hotspots | 3,536,296 of 3,838,615 (92.1%) |
| 0.25° grid cells | 4,133 |
| Cell-months | 199,587 |
| Cell-day overlap | 2012–2026, ratio 0.489, slope 0.488, R² 0.597 |
| Detection overlap | ratio 0.300, slope 0.217, R² 0.783 |
| Cell-specific calibration | 99% of cells (the rest use the overall ratio) |

October 2026 is the last **complete** month in the extract, so the app does not compare a
partial month against full historical months. The raw FIRMS CSVs (308 MB) are not committed.

## Using other NASA FIRMS data

1. Download active-fire CSVs from NASA FIRMS:
   <https://firms.modaps.eosdis.nasa.gov/download/>
   Use **MODIS Collection 6.1** (or newer) and **VIIRS 375 m** (Suomi NPP and/or NOAA-20/21).
   You can request a global or regional extract and any date range; the 2012+ period is
   required for the MODIS/VIIRS overlap calibration.
2. Run the pipeline with the downloaded files (paths with spaces must be quoted). Pass
   `--start-month`/`--end-month` to exclude incomplete months:

```powershell
python harmonize.py `
  --modis "D:\firms\modis_argentina_*.csv" `
  --viirs "D:\firms\viirs_snpp_argentina_*.csv" `
  --outdir data --region Argentina --tz-offset -3 `
  --start-month 2012-01 --end-month 2026-10
```

3. Restart Streamlit. The app reads `data/harmonized_monthly.parquet` when present,
   otherwise `data/harmonized_monthly.csv`, plus `data/meta.json`.

Large global extracts can be several GB. The pipeline keeps only the columns it needs, but
for repeated global runs it is worth filtering by region/date upstream. A Parquet copy of
the harmonized table is written automatically and loaded by the app in preference to CSV,
which is much faster and more memory-efficient for millions of rows.

### Command-line options

| Flag | Meaning |
| --- | --- |
| `--demo` | Generate and harmonize synthetic data (no FIRMS files needed) |
| `--modis FILE [FILE ...]` | One or more MODIS FIRMS CSV files |
| `--viirs FILE [FILE ...]` | One or more VIIRS FIRMS CSV files |
| `--outdir DIR` | Output directory (default `data`) |
| `--region NAME` | Human-readable region name stored in `meta.json` and shown in the app |
| `--start-month YYYY-MM` | Drop records before this local month |
| `--end-month YYYY-MM` | Drop records after this local month (use it to exclude a partial month) |
| `--seed N` | Synthetic data seed (default 42) |
| `--no-dedup` | Make raw detections the default metric (both metrics are always written) |
| `--export-hotspots` | Also write hotspot-level records (`hotspots.parquet`/`.csv`) for the app download (can be large) |
| `--tz-offset HOURS` | Add this many hours to UTC acquisition time before assigning months (e.g. `-8`) |
| `--no-parquet` | Skip writing the Parquet copy |

### Outputs

| File | Contents |
| --- | --- |
| `data/harmonized_monthly.csv` | Main table: cell, year, month, both metric series (MODIS, VIIRS, harmonized, ratio), per-day values, days in month, overlap months, calibration basis, source |
| `data/harmonized_monthly.parquet` | Same table in Parquet (written when pyarrow is available; the app prefers it) |
| `data/cell_calibration.csv` | Per-cell cell-day calibration ratio, raw ratio and number of overlap months |
| `data/harmonization_fit.png` | Scatter of VIIRS vs MODIS cell-day counts, fitted line, R², and a monthly-total time series showing the sensor transition |
| `data/hotspots.parquet` or `.csv` | Optional hotspot-level records written with `--export-hotspots`; not bundled because the real extract has 3.5 million rows |
| `data/meta.json` | Dataset provenance: synthetic flag, region, bounding box, raw/filtered counts, sensors, years, date window, default metric, time zone offset, latest month, cell-day and detection calibration statistics |
| `data/synthetic_hotspots.csv` | Demo-only raw synthetic detections (created only by `--demo`) |

## Method

### 1. Quality filtering

- MODIS: keep detections with `confidence ≥ 30` (0–100 scale).
- VIIRS: confidence is nominal (`l`/`n`/`h`); map to 20/60/85 and keep `n` and `h`
  (`≥ 30`), which matches FIRMS guidance to discard low-confidence detections.
- Drop rows with missing coordinates/dates and coordinates outside valid ranges. Records
  with unknown confidence are kept (FIRMS files always provide it in practice).

### 2. Deduplication, local time and monthly aggregation

MODIS and VIIRS are both flown on multiple platforms (MODIS: Terra and Aqua; VIIRS: Suomi
NPP, NOAA-20, NOAA-21). Counting every detection would make the series depend on how many
satellites happened to be flying, and the VIIRS platform count changes over time (NOAA-20
from 2018, NOAA-21 from 2023), which would create a false upward trend. The pipeline
therefore computes **two metrics for every cell-month-sensor**:

- **fire cell-days**: one per 0.25° cell per sensor per day, after deduplicating identical
  records from overlapping FIRMS downloads (the default metric);
- **detections**: the raw detection count.

Both are calibrated and exported, and the app lets the user switch between them. Acquisition
timestamps are built from `acq_date` + `acq_time` (UTC) and can be shifted to local time with
`--tz-offset HOURS` before year/month assignment, so a fire late on the last day of a month
is attributed to the local month rather than the UTC month.

Every detection is assigned to a 0.25° cell (cell center = `floor(lon/0.25)*0.25 + 0.125`,
same for latitude). Counts are aggregated to `cell × year × month × sensor`. This removes
the resolution mismatch between MODIS (1 km) and VIIRS (375 m) and produces a stable
spatio-temporal unit for comparison. `days_in_month`, `cell_days_per_day` and
`detections_per_day` are included for rate-based analysis.

### 3. Overlap calibration (VIIRS → MODIS)

The overlap window is the intersection of years in which both sensors have detections
(2012–2026 in the bundled Argentina extract; 2012+ wherever both sensors are available).
Let `M` and `V` be the overlap counts for a cell-month.

- Global ratio: `r_global = ΣM / ΣV` over all overlap cell-months.
- Per-cell ratio: `r_cell = ΣM / ΣV` for the cell over the overlap, used only when both
  sums are positive.
- Shrinkage: `w = n / (n + 6)`, where `n` is the number of overlap months with VIIRS > 0,
  and `r = w · r_cell + (1 − w) · r_global`. The result is clipped to `[0.1, 3.0]`.
  Cells without a usable overlap ratio fall back to `r_global`.
- Diagnostics: ordinary least squares of `M` on `V` (intercept allowed), R², and
  `r_global` are written to `meta.json` and plotted in `harmonization_fit.png`. The
  calibration is run separately for the cell-day and detection metrics; both sets of
  statistics are stored in `meta.json`.

### 4. Building the harmonized series

For each metric, `harmonized = M` when MODIS detected at least one hotspot in that
cell-month; otherwise `harmonized = r · V` using the cell's calibrated ratio. In other words,
MODIS is the reference sensor where it exists, and calibrated VIIRS fills gaps during the
MODIS era and carries the series after MODIS ends. `source` records which path was used
(`modis` or `viirs_calibrated`). The output preserves both metrics
(`modis_cell_days`/`viirs_cell_days`/`count_harmonized_cell_days`/`ratio_cell_days` and the
`..._detections` equivalents), plus `overlap_months` and `calibration_basis`
(`cell` or `global`) so every value can be audited and low-confidence cells can be
identified. A single multiplicative ratio per cell makes the series continuous across the
sensor transition; no artificial jump is introduced when MODIS stops.

## App behaviour

- **Region selection:** draw a rectangle or polygon with the map's draw tool, or type west/
  south/east/north bounds in the sidebar. Bounds are clipped to the dataset extent.
- **Date range and month of interest:** both filter the calendar and the anomaly chart.
- **Count metric:** switch between fire cell-days (platform-independent) and raw hotspot
  detections; every chart, metric and the export follow the selection.
- **Calendar:** year rows × month columns, sum of harmonized counts across all cells in the
  selection. Blank cells mean no data, not zero.
- **Anomaly:** the latest year with data for the chosen calendar month is compared with the
  median of earlier years in the selected range (dashed line and percentage). If that month
  is the latest month in the dataset, the app warns that it may be partial.
- **Calibration reliability:** the app reports the share of selected cell-months that use a
  cell-specific ratio versus the global fallback, and the median number of overlap months.
- **CSV download:** every selected cell-month with both metrics, sensor contributions,
  per-day values, days in month, ratios, overlap months, calibration basis and source flag.
- **Hotspot-level download:** when `data/hotspots.parquet` (or `.csv`) exists, the app can
  filter individual detections to the chosen area and period and export them as CSV.
- **Accessibility:** cividis is the default color ramp (perceptually uniform and
  color-vision-deficiency friendly), viridis is offered as an alternative; charts use
  colorblind-safe orange/blue accent colors and text labels in addition to color.

## Testing

Nine unit tests cover confidence filtering, time parsing, both metrics, time-zone month
shifting, date-window filtering, single-sensor fallback, the full two-sensor pipeline,
raw-detection default mode, and CSV/Parquet consistency:

```powershell
python -m unittest discover -s tests -v
```

GitHub Actions runs the same suite on every push and pull request
(`.github/workflows/tests.yml`).

## Limitations and honest caveats

- MODIS (1 km, twice daily) and VIIRS (375 m, multiple platforms/overpasses) differ in
  spatial resolution, detection sensitivity, diurnal sampling and algorithm. A per-cell
  ratio makes counts comparable on average but cannot remove all small-fire, diurnal or
  biome-specific bias.
- Cell-day deduplication normalizes for the changing number of satellite platforms, but it
  can merge two distinct fires that occur in the same 0.25° cell on the same day. Raw
  detections are therefore also provided and can be selected as the default metric.
- The calibration assumes a stable MODIS/VIIRS relationship within each cell over time.
  It does not model trends in that relationship (sensor degradation, algorithm updates,
  new VIIRS platforms coming online). Cells with the `global` calibration basis are less
  reliable.
- Cloud/smoke masking, terrain, view angle and sensor degradation are not corrected beyond
  the confidence filter. The series counts **active-fire detections/cell-days**, not burned
  area or fire size.
- Cells with few overlap months are dominated by the global ratio, which may be inaccurate
  in regions with unusual detection behaviour.
- The most recent month can be partial; the app flags it when it is the dataset's latest
  month. Monthly totals are also not length-normalized in the calendar, but
  `cell_days_per_day` and `detections_per_day` are provided for rate-based comparison.
- The app loads the full harmonized table into memory. Parquet is used automatically and is
  strongly preferred for global multi-decade runs; for extremely large deployments a
  database or tiled aggregation would be the next step. Hotspot-level files can be large and
  are only loaded on request.
- Time-zone handling requires the user to choose an offset; a single offset cannot be
  correct for regions spanning multiple time zones.

## Future work

Blend both sensors during overlap instead of MODIS-only, weight calibration by FRP or
confidence, add per-cell uncertainty intervals, support VIIRS 750 m, cache tiles for offline
use, and expose a REST API for emergency operations centres.

## Repository layout

```
app.py                    Streamlit application
harmonize.py              Harmonization pipeline, optional synthetic demo, CLI
requirements.txt          Python dependencies
data/                     Generated datasets, calibration table, fit plot, metadata
submission/               Submission text and 7-slide demo outline
tests/                    Unit tests for the harmonization pipeline
.github/workflows/        CI that runs the tests
```

## Data sources and references

- NASA FIRMS — Fire Information for Resource Management System:
  <https://firms.modaps.eosdis.nasa.gov/>
- NASA LANCE / Earthdata for near-real-time MODIS and VIIRS active-fire products.
- Public FIRMS archive mirror used for the bundled Argentina extract:
  <https://huggingface.co/datasets/hotspot-harmonizers/firms>
- MODIS Collection 6.1 active fire product (MCD14ML), Giglio et al., 2016.
- VIIRS 375 m active fire product (VNP14IMG), Schroeder et al., 2014.
- NASA Space Apps Challenge 2026 challenge: *Harmonization of MODIS and VIIRS Hot Spots*.

All linked materials and the application content are in English. NASA FIRMS data are free
and open; please retain the FIRMS/Earthdata attribution when redistributing derived
products.
