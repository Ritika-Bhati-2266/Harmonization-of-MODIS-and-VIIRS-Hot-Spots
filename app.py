from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CSV_PATH = DATA_DIR / "harmonized_monthly.csv"
PARQUET_PATH = DATA_DIR / "harmonized_monthly.parquet"
META_PATH = DATA_DIR / "meta.json"
FIT_PATH = DATA_DIR / "harmonization_fit.png"
HOTSPOTS_PARQUET = DATA_DIR / "hotspots.parquet"
HOTSPOTS_CSV = DATA_DIR / "hotspots.csv"
GITHUB_URL = (
    "https://github.com/Ritika-Bhati-2266/Harmonization-of-MODIS-and-VIIRS-Hot-Spots"
)


def data_path():
    if PARQUET_PATH.exists():
        return PARQUET_PATH
    return CSV_PATH


def hotspot_path():
    if HOTSPOTS_PARQUET.exists():
        return HOTSPOTS_PARQUET
    if HOTSPOTS_CSV.exists():
        return HOTSPOTS_CSV
    return None

MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
MONTHS_SHORT = [m[:3] for m in MONTHS]

st.set_page_config(
    page_title="Ember Calendar - Harmonized Fire Hotspot Atlas",
    layout="wide",
)

st.markdown(
    """
<style>
:root {
    --ink: #20242a;
    --muted: #666f78;
    --accent: #d55e00;
    --accent-dark: #a84700;
    --accent-soft: #fdf1e8;
    --surface: #ffffff;
    --canvas: #faf8f4;
    --line: #e8e2d8;
}
html, body, [data-testid="stAppViewContainer"] {
    background: var(--canvas);
    color: var(--ink);
    font-family: "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}
[data-testid="stHeader"] {
    background: transparent;
}
[data-testid="stAppDeployButton"] {
    display: none;
}
.block-container {
    padding-top: 1.6rem;
    padding-bottom: 3rem;
    max-width: 1250px;
}
[data-testid="stSidebar"] {
    background: #f3efe7;
    border-right: 1px solid var(--line);
    min-width: 335px !important;
    max-width: 335px !important;
}
[data-testid="stSidebar"] .block-container {
    padding-top: 1.4rem;
}
[data-testid="stSidebar"] h3 {
    color: var(--ink);
    font-size: 1.02rem;
    letter-spacing: 0.01em;
}
.hero {
    padding: 1.7rem 1.9rem 1.5rem;
    border: 1px solid var(--line);
    border-radius: 22px;
    background:
        radial-gradient(120% 140% at 100% 0%, #fbe6d5 0%, rgba(251, 230, 213, 0) 55%),
        linear-gradient(135deg, #ffffff 0%, #fdf9f3 100%);
    box-shadow: 0 14px 40px rgba(64, 45, 24, 0.07);
    margin-bottom: 1.1rem;
}
.kicker {
    color: var(--accent-dark);
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    margin-bottom: 0.45rem;
}
.hero h1 {
    color: var(--ink);
    font-size: clamp(2.1rem, 4vw, 3.1rem);
    font-weight: 800;
    letter-spacing: -0.03em;
    line-height: 1.04;
    margin: 0 0 0.55rem 0;
}
.hero p {
    color: var(--muted);
    font-size: 1.02rem;
    line-height: 1.55;
    max-width: 60rem;
    margin: 0;
}
.pill-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    margin-top: 1rem;
}
.pill {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 999px;
    color: var(--muted);
    font-size: 0.78rem;
    font-weight: 600;
    padding: 0.28rem 0.7rem;
}
.pill-accent {
    background: var(--accent-soft);
    border-color: #f3cdb2;
    color: var(--accent-dark);
}
.section-head {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    margin: 1.7rem 0 0.55rem;
}
.section-head .step {
    align-items: center;
    background: var(--ink);
    border-radius: 10px;
    color: #ffffff;
    display: inline-flex;
    flex: 0 0 auto;
    font-size: 0.8rem;
    font-weight: 700;
    height: 1.55rem;
    justify-content: center;
    margin-top: 0.15rem;
    width: 1.55rem;
}
.section-head h2 {
    color: var(--ink);
    font-size: 1.32rem;
    font-weight: 700;
    letter-spacing: -0.015em;
    line-height: 1.25;
    margin: 0;
}
.section-head p {
    color: var(--muted);
    font-size: 0.88rem;
    margin: 0.15rem 0 0;
}
[data-testid="stMetric"] {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 16px;
    box-shadow: 0 6px 18px rgba(64, 45, 24, 0.04);
    padding: 0.85rem 1rem;
}
[data-testid="stMetricLabel"] p {
    color: var(--muted);
    font-size: 0.8rem;
}
[data-testid="stMetricValue"] {
    color: var(--ink);
    font-weight: 700;
}
[data-testid="stPlotlyChart"], [data-testid="stFolium"] {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 18px;
    box-shadow: 0 8px 24px rgba(64, 45, 24, 0.05);
    overflow: hidden;
    padding: 0.35rem;
}
[data-testid="stFolium"] iframe {
    border-radius: 14px;
}
[data-testid="stSidebar"] [data-testid="stForm"] {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 0.9rem 0.85rem 0.35rem;
}
div[data-testid="stExpander"] {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 14px;
    overflow: hidden;
}
div[data-testid="stExpander"] summary {
    color: var(--ink);
    font-weight: 600;
}
button[kind="primary"], [data-testid="stDownloadButton"] button {
    background: var(--accent);
    border: 1px solid var(--accent);
    border-radius: 10px;
    color: #ffffff;
    font-weight: 600;
}
button[kind="primary"]:hover, [data-testid="stDownloadButton"] button:hover {
    background: var(--accent-dark);
    border-color: var(--accent-dark);
    color: #ffffff;
}
[data-testid="stAlert"] {
    border-radius: 14px;
}
.footer {
    border-top: 1px solid var(--line);
    color: var(--muted);
    font-size: 0.82rem;
    line-height: 1.6;
    margin-top: 2.3rem;
    padding-top: 1rem;
}
.footer a {
    color: var(--accent-dark);
    font-weight: 600;
    text-decoration: none;
}
.footer a:hover {
    text-decoration: underline;
}
@media (max-width: 720px) {
    .hero { padding: 1.2rem 1.1rem; }
    .block-container { padding-top: 1rem; }
    [data-testid="stSidebar"] {
        min-width: 88vw !important;
        max-width: 88vw !important;
    }
}
</style>
""",
    unsafe_allow_html=True,
)


def section_header(number, title, hint=""):
    st.markdown(
        f'<div class="section-head"><span class="step">{number}</span>'
        f"<div><h2>{title}</h2><p>{hint}</p></div></div>",
        unsafe_allow_html=True,
    )


def ensure_data():
    if not CSV_PATH.exists() and not PARQUET_PATH.exists():
        from harmonize import run_demo

        run_demo(DATA_DIR)


@st.cache_data(show_spinner=False)
def load_data(path, mtime):
    path = Path(path)
    if path.suffix == ".parquet":
        try:
            frame = pd.read_parquet(path)
        except Exception:
            if not CSV_PATH.exists():
                raise
            frame = pd.read_csv(CSV_PATH)
    else:
        frame = pd.read_csv(path)
    frame["date"] = pd.to_datetime(
        dict(year=frame["year"], month=frame["month"], day=1)
    )
    return frame


def load_meta():
    if META_PATH.exists():
        try:
            return json.loads(META_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


@st.cache_data(show_spinner=False)
def load_hotspots(path, mtime):
    path = Path(path)
    if path.suffix == ".parquet":
        spots = pd.read_parquet(path)
    else:
        spots = pd.read_csv(path, parse_dates=["timestamp", "acq_date"])
    if not pd.api.types.is_datetime64_any_dtype(spots["timestamp"]):
        spots["timestamp"] = pd.to_datetime(spots["timestamp"], errors="coerce")
    return spots


def data_bounds(frame):
    west = float(frame["cell_lon"].min() - 0.125)
    east = float(frame["cell_lon"].max() + 0.125)
    south = float(frame["cell_lat"].min() - 0.125)
    north = float(frame["cell_lat"].max() + 0.125)
    return [west, south, east, north]


def clamp_bounds(bounds, full):
    west, south, east, north = bounds
    west = max(min(west, full[2]), full[0])
    east = max(min(east, full[2]), full[0])
    south = max(min(south, full[3]), full[1])
    north = max(min(north, full[3]), full[1])
    if west >= east or south >= north:
        return list(full)
    return [west, south, east, north]


def zoom_for(span):
    if span > 60:
        return 2
    if span > 20:
        return 3
    if span > 6:
        return 4
    if span > 2:
        return 5
    if span > 0.5:
        return 7
    return 8


def collect_bounds(drawings):
    lons, lats = [], []

    def walk(node):
        if isinstance(node, (list, tuple)):
            if (
                len(node) >= 2
                and isinstance(node[0], (int, float))
                and isinstance(node[1], (int, float))
            ):
                lons.append(float(node[0]))
                lats.append(float(node[1]))
            else:
                for child in node:
                    walk(child)

    for feature in drawings or []:
        geometry = feature.get("geometry", feature) if isinstance(feature, dict) else {}
        walk(geometry.get("coordinates", []))
    if not lons or not lats:
        return None
    return [min(lons), min(lats), max(lons), max(lats)]


def region_map(bounds):
    try:
        import folium
        from folium.plugins import Draw
        from streamlit_folium import st_folium
    except Exception:
        return None

    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    fmap = folium.Map(
        location=center,
        zoom_start=zoom_for(max(bounds[2] - bounds[0], bounds[3] - bounds[1])),
        tiles="OpenStreetMap",
        control_scale=True,
    )
    folium.Rectangle(
        bounds=[[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
        color="#D55E00",
        weight=2,
        fill=True,
        fill_opacity=0.05,
    ).add_to(fmap)
    Draw(
        export=False,
        draw_options={
            "polyline": False,
            "circle": False,
            "circlemarker": False,
            "marker": False,
            "polygon": True,
            "rectangle": True,
        },
        edit_options={"edit": True, "remove": True},
    ).add_to(fmap)

    try:
        result = st_folium(
            fmap,
            height=380,
            use_container_width=True,
            returned_objects=["all_drawings"],
            key="region_map",
        )
    except TypeError:
        result = st_folium(
            fmap,
            height=380,
            width=760,
            returned_objects=["all_drawings"],
            key="region_map",
        )
    return (result or {}).get("all_drawings") or []


def calendar_heatmap(calendar, scale, unit, value_col):
    pivot = (
        calendar.pivot(index="year", columns="month", values=value_col)
        .reindex(columns=range(1, 13))
        .sort_index()
    )
    years = [str(int(y)) for y in pivot.index]
    short_unit = unit.replace("fire ", "")
    figure = go.Figure(
        go.Heatmap(
            z=pivot.to_numpy(),
            x=MONTHS_SHORT,
            y=years,
            colorscale=scale,
            xgap=1,
            ygap=1,
            colorbar=dict(
                title=dict(text=short_unit.capitalize(), side="right"),
                thickness=12,
                len=0.72,
                outlinewidth=0,
            ),
            hovertemplate="%{y} %{x}<br>%{z:,.0f} " + unit + "<extra></extra>",
        )
    )
    figure.update_layout(
        height=max(320, 28 * len(years) + 120),
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", size=13, color="#20242a"),
        xaxis=dict(side="top", showgrid=False, tickfont=dict(size=12)),
        yaxis=dict(
            autorange="reversed",
            title=None,
            showgrid=False,
            tickfont=dict(size=12),
        ),
        hoverlabel=dict(bgcolor="#ffffff", bordercolor="#e8e2d8", font_size=12),
    )
    return figure


def anomaly_chart(calendar, month, unit, value_col):
    rows = calendar[calendar["month"] == month].sort_values("year")
    if rows.empty:
        return None, None
    latest = rows.iloc[-1]
    baseline = rows[rows["year"] < latest["year"]][value_col]
    if baseline.empty:
        baseline = rows[value_col]
    median = float(baseline.median())
    current = float(latest[value_col])
    pct = (current - median) / median * 100 if median > 0 else float("nan")

    colors = [
        "#d55e00" if year == latest["year"] else "#b9c6d4"
        for year in rows["year"]
    ]
    figure = go.Figure(
        go.Bar(
            x=[str(int(y)) for y in rows["year"]],
            y=rows[value_col],
            marker_color=colors,
            marker_line_width=0,
            hovertemplate="%{x}<br>%{y:,.0f} " + unit + "<extra></extra>",
        )
    )
    if median > 0:
        figure.add_hline(
            y=median,
            line_dash="dash",
            line_color="#20242a",
            line_width=1.4,
            annotation_text=f"Median {median:,.0f}",
            annotation_position="top left",
            annotation_font=dict(size=12, color="#20242a"),
        )
    figure.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=24, b=10),
        yaxis_title=unit.capitalize(),
        xaxis_title=None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", size=13, color="#20242a"),
        showlegend=False,
        bargap=0.28,
        xaxis=dict(showgrid=False, tickfont=dict(size=12)),
        yaxis=dict(gridcolor="#ece7df", zeroline=False),
        hoverlabel=dict(bgcolor="#ffffff", bordercolor="#e8e2d8", font_size=12),
    )
    summary = {
        "month": month,
        "current_year": int(latest["year"]),
        "current": current,
        "median": median,
        "pct": pct,
    }
    return figure, summary


ensure_data()
meta = load_meta()
active_path = data_path()
mtime = active_path.stat().st_mtime
frame = load_data(active_path, mtime)
METRIC_CHOICES = {
    "cell_days": ("count_harmonized_cell_days", "fire cell-days"),
    "detections": ("count_harmonized_detections", "hotspot detections"),
}
default_metric = meta.get("default_metric", "cell_days")
if default_metric not in METRIC_CHOICES:
    default_metric = "cell_days"
full_bounds = data_bounds(frame)

if "bbox" not in st.session_state:
    st.session_state.bbox = list(full_bounds)

st.sidebar.markdown("### Location")
st.sidebar.caption(
    "Draw a rectangle or polygon on the map, or type bounds. "
    "Longitudes are negative in the western hemisphere."
)
sig = "_".join(f"{v:.3f}" for v in st.session_state.bbox)
with st.sidebar.form("bounds_form"):
    west = st.number_input(
        "West longitude", value=float(st.session_state.bbox[0]), format="%.3f", key=f"w_{sig}"
    )
    east = st.number_input(
        "East longitude", value=float(st.session_state.bbox[2]), format="%.3f", key=f"e_{sig}"
    )
    south = st.number_input(
        "South latitude", value=float(st.session_state.bbox[1]), format="%.3f", key=f"s_{sig}"
    )
    north = st.number_input(
        "North latitude", value=float(st.session_state.bbox[3]), format="%.3f", key=f"n_{sig}"
    )
    if st.form_submit_button("Apply bounds", use_container_width=True, type="primary"):
        st.session_state.bbox = clamp_bounds([west, south, east, north], full_bounds)
        st.rerun()

if st.sidebar.button("Reset to full dataset", use_container_width=True):
    st.session_state.bbox = list(full_bounds)
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### Time window")
first_date = frame["date"].min().date()
last_date = frame["date"].max().date()
picked = st.sidebar.date_input(
    "Date range (months)",
    value=(first_date, last_date),
    min_value=first_date,
    max_value=last_date,
    key="date_range",
)
if isinstance(picked, (tuple, list)):
    if len(picked) == 2:
        start_date, end_date = picked
    elif len(picked) == 1:
        start_date = end_date = picked[0]
    else:
        start_date, end_date = first_date, last_date
else:
    start_date = end_date = picked
start_month = pd.Timestamp(start_date).replace(day=1)
end_month = pd.Timestamp(end_date).replace(day=1)

latest_month = int(frame.loc[frame["date"].idxmax(), "month"])
month = st.sidebar.selectbox(
    "Month of interest",
    options=list(range(1, 13)),
    index=latest_month - 1,
    format_func=lambda m: MONTHS[m - 1],
    key="month_pick",
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Display")
metric_options = list(METRIC_CHOICES)
metric = st.sidebar.radio(
    "Count metric",
    options=metric_options,
    index=metric_options.index(default_metric),
    format_func=lambda key: METRIC_CHOICES[key][1].capitalize(),
    key="metric_pick",
    help=(
        "Fire cell-days count one detection per 0.25° cell per sensor per day and are "
        "independent of how many satellite platforms are flying. Hotspot detections are "
        "the raw detection counts. Both are always included in the CSV."
    ),
)
value_col, unit = METRIC_CHOICES[metric]
scale = st.sidebar.radio(
    "Calendar color ramp",
    options=["cividis", "viridis"],
    horizontal=True,
    help="Both ramps are perceptually uniform; cividis is optimized for color-vision deficiency.",
)

with st.sidebar.expander("Harmonization fit"):
    cal = meta.get("calibration", {})
    cal_det = meta.get("calibration_detections", {})
    if cal:
        st.write(
            f"Cell-days overlap: **{cal.get('overlap_start')}–{cal.get('overlap_end')}**  \n"
            f"Global MODIS/VIIRS ratio: **{cal.get('global_ratio_modis_over_viirs', float('nan')):.2f}**  \n"
            f"Slope: **{cal.get('fit_slope', float('nan')):.2f}**, R²: **{cal.get('fit_r2', float('nan')):.3f}**"
        )
    if cal_det:
        st.caption(
            "Raw detections calibration: "
            f"ratio {cal_det.get('global_ratio_modis_over_viirs', float('nan')):.2f}, "
            f"R² {cal_det.get('fit_r2', float('nan')):.3f}."
        )
    if FIT_PATH.exists():
        st.image(str(FIT_PATH))
    st.caption(
        "VIIRS counts are rescaled per 0.25° cell to MODIS-equivalent units. "
        "MODIS is used where available; calibrated VIIRS fills the rest. "
        "See README for method and limitations."
    )

st.sidebar.markdown(
    f'<div class="footer" style="margin-top:1.2rem;">'
    f'<a href="{GITHUB_URL}" target="_blank">View source on GitHub</a><br>'
    "NASA FIRMS MODIS + VIIRS · 0.25° harmonized grid</div>",
    unsafe_allow_html=True,
)

sensor_label = " + ".join(meta.get("sensors", [])) or "MODIS + VIIRS"
first_year = int(frame["year"].min())
last_year = int(frame["year"].max())
data_pill = "Synthetic demo" if meta.get("synthetic", False) else "NASA FIRMS data"
st.markdown(
    f"""
<div class="hero">
    <div class="kicker">NASA Space Apps Challenge 2026</div>
    <h1>Ember Calendar</h1>
    <p>
        One consistent record of when and where Earth burns. Explore a harmonized
        MODIS + VIIRS active-fire history for any region, spot its seasonal rhythm,
        and see whether the latest month is unusual.
    </p>
    <div class="pill-row">
        <span class="pill pill-accent">{data_pill}</span>
        <span class="pill">{sensor_label}</span>
        <span class="pill">{first_year}–{last_year}</span>
        <span class="pill">0.25° grid</span>
        <span class="pill">{len(frame):,} cell-months</span>
    </div>
</div>
""",
    unsafe_allow_html=True,
)
if meta.get("synthetic", False):
    st.info(
        "Demo mode: the bundled dataset is synthetic. Run "
        "`python harmonize.py --modis <MODIS.csv> --viirs <VIIRS.csv>` with NASA FIRMS "
        "downloads to replace it, or point the app at real data before judging.",
    )

section_header(
    1,
    "Choose a region",
    "Draw a rectangle or polygon on the map, or fine-tune the bounds in the sidebar.",
)
drawings = None
try:
    drawings = region_map(st.session_state.bbox)
except Exception as exc:
    st.warning(f"Interactive map unavailable ({exc}). Use the bounds fields in the sidebar.")

if drawings:
    drawn = collect_bounds(drawings)
    if drawn is not None:
        applied = clamp_bounds(drawn, full_bounds)
        signature = json.dumps(drawings, sort_keys=True)
        if st.session_state.get("draw_signature") != signature:
            st.session_state["draw_signature"] = signature
            st.session_state.bbox = applied
            st.rerun()

bounds = st.session_state.bbox
st.caption(
    f"Active bounds  ·  W {bounds[0]:.3f}  ·  S {bounds[1]:.3f}  ·  "
    f"E {bounds[2]:.3f}  ·  N {bounds[3]:.3f}"
)

selected = frame[
    (frame["cell_lon"] >= bounds[0])
    & (frame["cell_lon"] <= bounds[2])
    & (frame["cell_lat"] >= bounds[1])
    & (frame["cell_lat"] <= bounds[3])
    & (frame["date"] >= start_month)
    & (frame["date"] <= end_month)
].copy()

if selected.empty:
    st.warning("No harmonized hotspots in this selection. Widen the area or the date range.")
    st.stop()

cell_count = selected[["cell_lat", "cell_lon"]].drop_duplicates().shape[0]
month_count = selected[["year", "month"]].drop_duplicates().shape[0]
if "calibration_basis" in selected.columns and len(selected):
    cell_share = float((selected["calibration_basis"] == "cell").mean() * 100)
    median_overlap = (
        float(selected["overlap_months"].median())
        if "overlap_months" in selected.columns
        else float("nan")
    )
    calibration_value = f"{cell_share:.0f}%"
    calibration_help = (
        "Share of selected cell-months with a cell-specific MODIS/VIIRS ratio; the rest "
        f"use the global ratio. Median overlap: {median_overlap:.0f} months with both sensors."
    )
else:
    calibration_value = "n/a"
    calibration_help = "Calibration basis is not present in this dataset."

summary_cols = st.columns(4)
summary_cols[0].metric(
    "Grid cells",
    f"{cell_count:,}",
    help="0.25° cells with at least one harmonized month in this selection.",
)
summary_cols[1].metric(
    "Cell-months",
    f"{len(selected):,}",
    help="Rows in the monthly export for this selection.",
)
summary_cols[2].metric(
    "Months covered",
    f"{month_count:,}",
    help="Distinct calendar months with data across the selection.",
)
summary_cols[3].metric(
    "Cell-specific calibration",
    calibration_value,
    help=calibration_help,
)

calendar = (
    selected.groupby(["year", "month"], as_index=False)[value_col]
    .sum()
    .sort_values(["year", "month"])
)

section_header(
    2,
    "Burning-activity calendar",
    "Monthly harmonized activity across every selected 0.25° cell.",
)
figure = calendar_heatmap(calendar, scale, unit, value_col)
st.plotly_chart(figure, use_container_width=True)
st.caption(
    f"Each cell is the monthly total of harmonized {unit} across all 0.25° cells "
    "in your selection. Blank cells mean no data for that month."
)

section_header(
    3,
    f"{MONTHS[month - 1]} vs the historical median",
    "The latest year with data for this month compared with earlier years.",
)
anomaly_figure, summary = anomaly_chart(calendar, month, unit, value_col)
if anomaly_figure is None:
    st.info(f"No {MONTHS[month - 1]} data in this selection.")
else:
    total = selected[value_col].sum()
    metric_cols = st.columns(4)
    metric_cols[0].metric(f"{unit.capitalize()} in selection", f"{total:,.0f}")
    metric_cols[1].metric(
        f"{MONTHS_SHORT[month - 1]} {summary['current_year']}",
        f"{summary['current']:,.0f}",
    )
    metric_cols[2].metric(
        f"Median {MONTHS_SHORT[month - 1]}",
        f"{summary['median']:,.0f}",
    )
    anomaly = summary["pct"]
    metric_cols[3].metric(
        "Anomaly vs median",
        "n/a" if not np.isfinite(anomaly) else f"{anomaly:+.0f}%",
    )
    st.plotly_chart(anomaly_figure, use_container_width=True)
    st.caption(
        "The orange bar is the most recent year with data for this calendar month. "
        "The dashed line is the median of earlier years in the selected date range. "
        f"A positive anomaly means more {unit} than a typical year for this month."
    )
    latest_ym = f"{summary['current_year']}-{summary['month']:02d}"
    if meta.get("max_year_month") and latest_ym == meta["max_year_month"]:
        st.caption(
            "This is the most recent month in the dataset and may be partial; "
            "its anomaly will keep changing as new detections arrive."
        )

section_header(
    4,
    "Data and downloads",
    "Audit the numbers or take the harmonized table into your own analysis.",
)
export_columns = [
    "cell_lat",
    "cell_lon",
    "year",
    "month",
    "modis_cell_days",
    "viirs_cell_days",
    "count_harmonized_cell_days",
    "ratio_cell_days",
    "modis_detections",
    "viirs_detections",
    "count_harmonized_detections",
    "ratio_detections",
    "days_in_month",
    "cell_days_per_day",
    "detections_per_day",
    "overlap_months",
    "calibration_basis",
    "source",
]
export = selected[export_columns].sort_values(
    ["year", "month", "cell_lat", "cell_lon"]
)
filename = (
    f"burning_calendar_W{bounds[0]:.2f}_S{bounds[1]:.2f}_"
    f"E{bounds[2]:.2f}_N{bounds[3]:.2f}_"
    f"{start_month:%Y%m}-{end_month:%Y%m}.csv"
)
st.download_button(
    "Download harmonized monthly CSV",
    data=export.to_csv(index=False).encode("utf-8-sig"),
    file_name=filename,
    mime="text/csv",
)
with st.expander("Preview data table"):
    st.dataframe(export, use_container_width=True, height=320)

with st.expander("Hotspot-level download"):
    spot_file = hotspot_path()
    if spot_file is None:
        st.caption(
            "Hotspot-level records are not available for this dataset. Re-run "
            "`harmonize.py` with `--export-hotspots` to generate them (the demo "
            "dataset already includes a small file)."
        )
    elif st.checkbox(
        "Load hotspot-level records for this selection", key="load_spots"
    ):
        spots = load_hotspots(spot_file, spot_file.stat().st_mtime)
        start_ym = start_month.year * 100 + start_month.month
        end_ym = end_month.year * 100 + end_month.month
        spot_ym = spots["year"] * 100 + spots["month"]
        subset = spots[
            (spots["cell_lon"] >= bounds[0])
            & (spots["cell_lon"] <= bounds[2])
            & (spots["cell_lat"] >= bounds[1])
            & (spots["cell_lat"] <= bounds[3])
            & (spot_ym >= start_ym)
            & (spot_ym <= end_ym)
        ]
        st.write(f"{len(subset):,} filtered hotspot records in this selection.")
        if len(subset) > 1_000_000:
            st.warning(
                "This is a large selection; building the CSV may take a few seconds."
            )
        if len(subset):
            spot_columns = [
                "latitude",
                "longitude",
                "acq_date",
                "timestamp",
                "sensor",
                "satellite",
                "confidence",
                "frp",
                "cell_lat",
                "cell_lon",
            ]
            spot_name = (
                f"hotspots_W{bounds[0]:.2f}_S{bounds[1]:.2f}_"
                f"E{bounds[2]:.2f}_N{bounds[3]:.2f}_"
                f"{start_month:%Y%m}-{end_month:%Y%m}.csv"
            )
            st.download_button(
                "Download hotspot-level CSV",
                data=subset[spot_columns]
                .to_csv(index=False)
                .encode("utf-8-sig"),
                file_name=spot_name,
                mime="text/csv",
            )

with st.expander("Method, data and limitations"):
    st.markdown(
        """
**Data.** NASA FIRMS active-fire detections from MODIS (Terra/Aqua, 2000–present) and
VIIRS (Suomi NPP, NOAA-20/21, 2012–present).

**Quality filter.** MODIS confidence ≥ 30; VIIRS nominal/high confidence (l/n/h mapped to
20/60/85). Two metrics are computed and both are exported: **fire cell-days** (one detection
per 0.25° cell per sensor per day, used by default) and **hotspot detections** (raw detection
counts). Acquisition times are converted to local time with `--tz-offset` before months are
assigned.

**Harmonization.** On years where both sensors are active, a per-cell MODIS/VIIRS ratio is
estimated from total counts, shrunk toward the global ratio with a 6-month prior and clipped
to 0.1–3.0. The series uses MODIS where available and calibrated VIIRS (`VIIRS × ratio`)
elsewhere, so sensor changes do not create artificial jumps. The CSV records the ratio, the
number of overlap months and whether a cell-specific or global ratio was used.

**Limitations.** MODIS (1 km) and VIIRS (375 m) differ in resolution, overpass time and
sensitivity; a single multiplicative ratio cannot fully remove diurnal or small-fire bias.
Cell-day deduplication trades pixel-level counts for platform-independent counts and can
merge distinct fires in the same cell on the same day. Cloud cover, smoke, terrain and sensor
degradation are not corrected. Cells with little overlap get the global ratio, and the
calibration assumes the relationship is stable within a cell. Counts are not burned area,
and the most recent month may be partial.

**Privacy.** No personal data is used. See README for full method notes and references.
        """
    )

st.markdown(
    f"""
<div class="footer">
    <strong>Ember Calendar</strong> · NASA Space Apps Challenge 2026 ·
    Challenge: Harmonization of MODIS and VIIRS Hot Spots<br>
    Hotspot data: NASA FIRMS · Harmonized to a 0.25° grid ·
    <a href="{GITHUB_URL}" target="_blank">Source code and method notes</a><br>
    The bundled demo dataset is synthetic until real FIRMS files are supplied.
</div>
""",
    unsafe_allow_html=True,
)
