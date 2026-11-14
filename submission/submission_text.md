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

Ember Calendar is a web application that turns two decades of NASA satellite fire
detections into one consistent monthly burning-activity calendar for any region on Earth. It
harmonizes MODIS and VIIRS active-fire hotspots from NASA FIRMS onto a 0.25° grid and
calibrates VIIRS to MODIS on their overlapping years, so a change of sensor no longer looks
like a change in fire activity. Users draw an area of interest or type coordinates, choose a
date range, and immediately see a year-by-month heatmap of hotspot counts, the selected
month compared with its historical median, and a downloadable CSV of the harmonized data.
Emergency managers, land managers and scientists can use it to identify peak fire seasons,
exceptional years and anomalous months at a glance.

---

## Link to Project Demo

`[DEMO LINK — publicly accessible slide deck (max 7 slides), no login required]`

Suggested host: Google Slides (Anyone with the link → Viewer), Google Drive PDF, or GitHub
Releases. Test the link in a private browser window before submitting.

---

## Link to Final Project

`[REPOSITORY OR LIVE APP LINK — public, no login required]`

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
3. **Grid and aggregate.** Assign every detection to a 0.25° cell and aggregate to monthly
   counts per cell and per sensor. This common spatio-temporal unit removes the resolution
   mismatch.
4. **Harmonize.** On the years where both sensors are active (2012+ for FIRMS), estimate a
   global MODIS/VIIRS ratio and a per-cell ratio from total counts. Shrink each cell ratio
   toward the global value with a 6-month prior and clip it to 0.1–3.0. Build the final
   series using MODIS where it exists and calibrated VIIRS (`VIIRS × ratio`) elsewhere.
   Every output row keeps the original MODIS count, VIIRS count, ratio and a `source` flag,
   so the transformation is fully auditable.
5. **Explore.** The Streamlit app lets a user draw a rectangle or polygon on a map or enter
   west/south/east/north bounds, set a date range and a month of interest, then view:
   - a year × month burning-activity calendar on a perceptually uniform, colorblind-friendly
     ramp (cividis, with viridis as an option);
   - the selected month in the latest year versus the median of earlier years, with the
     percentage anomaly;
   - total hotspots and a CSV containing every selected cell-month, including sensor
     contributions and the calibration ratio.

**Why it is useful.** The calendar answers practical questions quickly: Which months are the
peak burning season here? Which years were exceptional? Is this month above or below the
historical median? Because the output is a consistent, downloadable table, it also supports
scientists and land managers who need a defensible, reproducible fire-activity series rather
than a screenshot.

**Validation and transparency.** The app ships with the calibration fit (VIIRS versus MODIS
monthly counts) and R² in the sidebar and in `data/harmonization_fit.png`, plus the
calibration ratio for every cell. On our calibration run with `<insert real data range>` the
overlap covered `<insert years>` and the global MODIS/VIIRS ratio was `<insert ratio>` with
R² = `<insert R² from data/meta.json>`. (The bundled demo dataset is synthetic and is
clearly labelled as such in the app; replace it with real FIRMS data for judging.)

**Limitations we are explicit about.** A single multiplicative ratio cannot fully remove
differences in resolution, diurnal sampling or small-fire sensitivity; cloud/smoke and sensor
degradation are not corrected; counts are detections, not burned area; and cells with little
overlap fall back to the global ratio. The README documents these caveats, the exact
algorithm and its assumptions.

**Roadmap.** Blend both sensors during the overlap instead of using MODIS alone, weight the
calibration by fire radiative power, add per-cell uncertainty bands, support VIIRS 750 m,
and deploy the app as a public service with an API for emergency operations centres.

---

## Use of Super Intelligence (SI)

We used an AI coding assistant during the hackathon for code scaffolding, documentation,
refactoring suggestions and design critique. The assistant did not generate data and is not
part of the runtime system: harmonization is deterministic statistics (confidence filtering,
0.25° monthly aggregation, per-cell ratio estimation with shrinkage, clipping) and the web
app performs no inference. All generated code was reviewed, tested and is reproducible from
the repository; the team takes full responsibility for it. No personal data, private data or
credentials were shared with the assistant, and no third-party model is trained on the
project or NASA data. A machine-learning gap-filler is listed only as future work and is not
used in the submitted application.

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
- Outputs: burning-activity calendar, anomaly vs historical median, CSV download
- Built for responders, land managers and scientists
- Visual: three annotated screenshots (map selection, calendar, anomaly chart)

### Slide 4 — How it works
- Pipeline: FIRMS CSVs → quality filter → 0.25° monthly counts → overlap calibration →
  harmonized series → Streamlit app
- MODIS confidence ≥ 30; VIIRS nominal/high
- MODIS is the reference; calibrated VIIRS fills gaps and continues after MODIS
- Visual: simple five-box pipeline diagram with one icon per step

### Slide 5 — Harmonization that you can audit
- Per-cell MODIS/VIIRS ratio, shrunk toward the global ratio and clipped to 0.1–3.0
- Overlap fit, R² and every cell's ratio are visible in the app and repository
- No artificial jump when the sensor changes
- Visual: `harmonization_fit.png` (scatter + fit + monthly totals)

### Slide 6 — Demo: a region's fire story
- Walk through one region: peak month, exceptional years, current month anomaly
- Show the accessible cividis calendar and the CSV export
- Note the honest caveats: detections ≠ burned area; ratio is an approximation
- Visual: live app screenshot with the anomaly chart highlighted

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
