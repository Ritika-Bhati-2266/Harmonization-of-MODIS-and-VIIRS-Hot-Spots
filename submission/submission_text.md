# NASA Space Apps Challenge 2026 — Submission Text

Challenge: **Harmonization of MODIS and VIIRS Hot Spots**
Team: `<team name>`
Team members: `<names>`
Local Event: `<event name and city>`

> Replace every `<...>` placeholder and every `[BRACKETED LINK]` before pasting into the
> Project page. Copy each section into the matching form field. Keep everything in English.

---

## Project Name

**Ember Calendar**

Tagline: *One consistent record of when and where Earth burns.*

---

## High-Level Project Summary

Ember Calendar is a web application that turns NASA satellite fire detections into one
consistent monthly burning-activity calendar for a region of interest. It harmonizes MODIS and
VIIRS active-fire hotspots from NASA FIRMS onto a 0.25° grid and calibrates VIIRS to MODIS on
their overlapping years, so a change of sensor no longer looks like a change in fire
activity. The submitted build uses a real Argentina extract: 4,373,521 quality-filtered
detections from November 2000 to October 2026, aggregated into 301,741 cell-months across
4,221 grid cells. Users draw an area of interest or type coordinates, choose a date range, and
immediately see a year-by-month heatmap of harmonized burning activity, the selected month
compared with its historical median, and a downloadable CSV. Two calibrated metrics are
available — fire cell-days (platform-independent) and raw hotspot detections — together with
a reliability flag showing whether each cell used its own calibration or the overall
fallback. A hotspot-level CSV can be generated with the pipeline for any area and period.
Emergency managers, land managers and scientists can use it to identify peak fire seasons,
exceptional years and anomalous months at a glance.

---

## Link to Project Demo

`[DEMO LINK — publicly accessible slide deck (max 7 slides), no login required]`

Suggested host: Google Slides (Anyone with the link → Viewer), Google Drive PDF, or GitHub
Releases. Test the link in a private browser window before submitting.

---

## Link to Final Project

Live app: `https://harmonization-of-modis-and-viirs-hot.onrender.com`
Repository: `https://github.com/Ritika-Bhati-2266/Harmonization-of-MODIS-and-VIIRS-Hot-Spots`

Examples: the public GitHub repository (`app.py`, `harmonize.py`, `README.md`, sample data)
and, if deployed, the Streamlit Community Cloud URL. If you host a new website, submit a
FortiGuard Web Filter Classification request and test access from a private window.

---

## Detailed Project Description

**The problem.** Satellites have observed active fires for more than two decades, but the
record is split between MODIS (2000–present) and VIIRS (2012–present). The sensors differ in
spatial resolution, sensitivity and overpass schedule, so their hotspot counts cannot be
compared directly. Fire managers who want to know whether the current month is unusual, or
which years had the most burning, end up comparing apples with oranges exactly when a
consistent answer matters most.

**Our solution.** Ember Calendar is an end-to-end, reproducible pipeline plus an interactive
web app:

1. **Ingest.** Download MODIS Collection 6.1 and VIIRS 375 m active-fire CSVs from NASA
   FIRMS for any date range.
2. **Quality filter.** Keep MODIS confidence ≥ 30 and VIIRS nominal/high confidence
   (`n`/`h`), then drop invalid coordinates.
3. **Deduplicate, grid and aggregate.** Build full UTC timestamps from `acq_date` +
   `acq_time`, optionally shift to local time, and compute two metrics for every cell, month
   and sensor: (a) **fire cell-days**, at most one detection per 0.25° cell per sensor per
   day, after removing exact duplicates from overlapping FIRMS downloads, and (b) **raw
   hotspot detections**. The cell-day metric stops the series from depending on how many
   satellite platforms happened to be flying (MODIS Terra/Aqua, VIIRS Suomi NPP/NOAA-20/21);
   the raw metric preserves every detection. Both are calibrated and exported, and the app
   lets the user switch between them.
4. **Harmonize.** On the years where both sensors are active (2012+ for FIRMS), estimate a
   global MODIS/VIIRS ratio and a per-cell ratio from total counts, separately for each
   metric. Shrink each cell ratio toward the global value with a 6-month prior and clip it to
   0.1–3.0. Build the final series using MODIS where it exists and calibrated VIIRS
   (`VIIRS × ratio`) elsewhere. Every output row keeps both sensor series, both ratios, the
   number of overlap months, a `calibration_basis` flag (`cell` or `global`) and a `source`
   flag, so the transformation is fully auditable and low-confidence cells are identifiable.
5. **Explore.** The Streamlit app lets a user draw a rectangle or polygon on a map or enter
   west/south/east/north bounds, set a date range and a month of interest, then view:
   - a year × month burning-activity calendar on a perceptually uniform, colorblind-friendly
     ramp (cividis, with viridis as an option);
   - the selected month in the latest year versus the median of earlier years, with the
     percentage anomaly and a warning when the latest month may be partial;
   - annual totals with a 3-year moving average, so longer-term trends are visible without
     year-to-year noise;
   - a switchable count metric (fire cell-days or raw detections) that updates every chart;
   - total counts, a calibration-reliability note (share of cell-specific ratios and median
     overlap), and a CSV containing every selected cell-month, including both metrics,
     per-day rates, days in month and both calibration ratios;
   - an optional hotspot-level CSV filtered to the chosen area and period (generated with
     `--export-hotspots`; omitted from the bundled deployment because the real extract has
     3.5 million rows).

**Why it is useful.** The calendar answers practical questions quickly: Which months are the
peak burning season here? Which years were exceptional? Is this month above or below the
historical median? Because the output is a consistent, downloadable table, it also supports
scientists and land managers who need a defensible, reproducible fire-activity series rather
than a screenshot.

**Bundled real data.** The submitted app bundles a NASA FIRMS Argentina extract for November
2000–October 2026 (local UTC−3), using MODIS Terra/Aqua and VIIRS Suomi NPP 375 m. Of
4,714,843 raw detections, 4,373,521 pass the confidence filter (92.8%). They cover 4,221
0.25° cells and 301,741 cell-months. The 2012–2026 overlap contains 319,734 MODIS and
654,276 VIIRS cell-days. October 2026 is the last complete month, so the app never compares a
partial month with full historical months. The raw CSVs are not committed; the harmonized
table and provenance metadata are.

**Validation and transparency.** Nine unit tests cover the quality filter, timestamp and
time-zone handling, both metrics, date-window filtering, single-sensor fallback, the full
two-sensor pipeline, raw detection mode, and CSV/Parquet consistency; CI runs them on every
push. The app ships with the calibration fit (VIIRS versus MODIS cell-days) and R² in the
sidebar and in `data/harmonization_fit.png`, plus the calibration ratio and basis for every
cell. In the bundled run, the overlap covered 2012–2026 and the overall MODIS/VIIRS
cell-day ratio was **0.489** (slope 0.488, R² 0.597). The detection-based calibration is
also in `meta.json`: ratio **0.300**, slope 0.217, R² 0.783. Cell-specific ratios cover 99%
of cells; the rest use the overall fallback.

**Limitations we are explicit about.** A single multiplicative ratio cannot fully remove
differences in resolution, diurnal sampling or small-fire sensitivity; cell-day
deduplication makes counts platform-independent but can merge distinct fires in the same
cell on the same day; cloud/smoke and sensor degradation are not corrected; counts are
detections/cell-days, not burned area; and cells with little overlap fall back to the overall
ratio. Every row records which basis was used so users can filter or downweight less reliable
cells. The README documents these caveats, the exact algorithm and its assumptions.

**Roadmap.** Blend both sensors during the overlap instead of using MODIS alone, weight the
calibration by fire radiative power, add per-cell uncertainty intervals, support VIIRS 750 m,
and deploy the app as a public service with an API for emergency operations centres.

---

## Use of Super Intelligence (SI)

We used an AI coding assistant during the hackathon for code scaffolding, debugging,
documentation and design critique. The assistant did not generate data and is not part of the
runtime system: harmonization is deterministic statistics (confidence filtering, 0.25°
monthly aggregation, per-cell ratio estimation with shrinkage, clipping) and the web app
performs no inference. All generated code was reviewed, tested and is reproducible from the
repository; the team takes full responsibility for it.

In the SI disclosure form, the applicable options are:

- ☑ Coding, Debugging, or Troubleshooting
- ☑ Writing, Editing, or Translation
- ☑ Presentation, Video, or Audio (slide text and layout)

No SI-generated images, audio or video are included, so no watermark is required. All app
screenshots and the calibration plot are generated directly from the running project. No
personal data, private data or credentials were shared with the assistant, and no third-party
model is trained on the project or NASA data. A machine-learning gap-filler is listed only as
future work and is not used in the submitted application.

---

## NASA Data

All fire data come from **NASA FIRMS** (Fire Information for Resource Management System),
which distributes near-real-time and archival active-fire detections from NASA/NOAA
instruments through NASA LANCE and NASA Earthdata:

- **MODIS Collection 6.1** active-fire product (MCD14ML), Terra and Aqua, 2000–present,
  1 km, `confidence` 0–100.
- **VIIRS 375 m** active-fire product (VNP14IMG and NOAA-20/21 equivalents), Suomi NPP and
  NOAA-20/21, 2012–present, `confidence` nominal (l/n/h).
- Access: <https://firms.modaps.eosdis.nasa.gov/download/> (FIRMS area/date CSV extracts).
  Data are free and open; FIRMS/Earthdata attribution is retained in the README and app.
- Bundled extract: FIRMS Argentina CSVs (MODIS 2000–2026, VIIRS Suomi NPP 2012–2026) from the
  public FIRMS archive mirror
  <https://huggingface.co/datasets/hotspot-harmonizers/firms>.

The app derives everything from these hotspot records: 0.25° cell assignment, monthly counts,
the MODIS/VIIRS overlap calibration and the harmonized burning-activity calendar. No
non-NASA fire dataset is used.

---

## Space Agency Partner Data and Other References

Partner data: none beyond the NASA/NOAA JPSS VIIRS products distributed through FIRMS
(Suomi NPP, NOAA-20, NOAA-21). No commercial or restricted datasets were used.

References:

- Giglio, L., Schroeder, W., Justice, C. O. (2016). The Collection 6 MODIS active fire
  detection algorithm and fire products. *Remote Sensing of Environment*, 178, 31–41.
- Schroeder, W., Oliva, P., Giglio, L., Csiszar, I. A. (2014). The New VIIRS 375 m active
  fire detection data product: Algorithm description and initial assessment.
  *Remote Sensing of Environment*, 143, 85–96.
- NASA FIRMS: <https://firms.modaps.eosdis.nasa.gov/>
- NASA LANCE / Earthdata: <https://www.earthdata.nasa.gov/>
- NASA Space Apps Challenge 2026 challenge page: *Harmonization of MODIS and VIIRS Hot
  Spots*.

---

## Demo Outline — 7 Slides (slide deck, not a video)

Keep text short, font large, and every slide readable at a glance. Total: 7 slides including
title and intro. Add team name and member names on slide 1. Use English throughout.

### Slide 1 — Title
- **Ember Calendar** — *One consistent record of when and where Earth burns.*
- NASA Space Apps Challenge 2026 — Harmonization of MODIS and VIIRS Hot Spots
- Team name, member names, Local Event
- Visual: app screenshot behind the title, dark overlay for readability

### Slide 2 — The problem
- Two sensors, two decades: MODIS (2000–) and VIIRS (2012–)
- Different resolution, sensitivity and overpass times → counts are not comparable
- Fire managers still need a simple answer: *is this month unusual for this place?*
- Visual: split panel showing MODIS vs VIIRS scenes of the same fire

### Slide 3 — Our solution
- Web app: draw a region or type coordinates, pick a date range and month
- Outputs: burning-activity calendar, anomaly vs historical median, two calibrated metrics,
  monthly and hotspot-level CSV downloads
- Built for responders, land managers and scientists
- Visual: three annotated screenshots (map selection, calendar, anomaly chart)

### Slide 4 — How it works
- Pipeline: FIRMS CSVs → quality filter → dual metrics (cell-days + raw detections) →
  0.25° monthly counts → per-metric overlap calibration → harmonized series → Streamlit app
- MODIS confidence ≥ 30; VIIRS nominal/high; cell-day metric removes platform-count bias
- MODIS is the reference; calibrated VIIRS fills gaps and continues after MODIS
- Visual: simple pipeline diagram with one icon per step

### Slide 5 — Harmonization that you can audit
- Per-cell MODIS/VIIRS ratio, shrunk toward the global ratio and clipped to 0.1–3.0
- Every row carries its ratio, overlap months and a `cell`/`global` calibration-basis flag
- Overlap fit, R² and the reliability share are visible in the app and repository
- No artificial jump when the sensor changes
- Visual: `harmonization_fit.png` (scatter + fit + monthly totals)

### Slide 6 — Demo: a region's fire story
- Walk through one region: peak month, exceptional years, current month anomaly
- Switch between cell-days and raw detections; show the accessible cividis calendar
- Export the monthly CSV and a hotspot-level CSV for the same selection
- Note the honest caveats: detections ≠ burned area; global-basis cells are less certain
- Visual: live app screenshot with the anomaly chart and reliability note highlighted

### Slide 7 — Impact and next steps
- Gives responders and land managers a consistent, fast seasonal baseline
- Open, reproducible, NASA-data-only; works for any region on Earth
- Next: blend both sensors during overlap, FRP-weighted calibration, uncertainty bands, API
- Links to the public app/repository and demo; thank the organizers
- Visual: world map with a few selectable regions and the project QR/link

---

## Pre-submission checklist

- [ ] Replace all `<...>` placeholders (team, event, real calibration numbers).
- [ ] Replace the synthetic demo data with real FIRMS files and rerun `harmonize.py`.
- [ ] Run `python -m unittest discover -s tests -v` (all tests green).
- [ ] Make the demo link and final-project link public; test both in a private browser
      window with no login.
- [ ] Confirm all team members are confirmed participants at the same Local Event.
- [ ] Confirm the deck is ≤ 7 slides and all content is in English.
- [ ] Confirm no images/video/audio of anyone under 18 appear (Terms & Conditions).
- [ ] On the Project page: fill all required fields, tick *Terms and Conditions* and
      *Confirm All Work is Original*, then click **Submit for Judging** before
      **Sunday, November 15, 11:59 p.m. local time**.
- [ ] After submission, download the participant certificate from your profile
      (Letter paper size, PDF).
