from __future__ import annotations

import argparse
import calendar
import json
from pathlib import Path

import numpy as np
import pandas as pd

CELL = 0.25
MIN_CONFIDENCE = 30
SHRINK_MONTHS = 6
RATIO_BOUNDS = (0.1, 3.0)
DEMO_BBOX = (-121.5, 36.0, -119.0, 38.5)
SENSORS = ("MODIS", "VIIRS")


def generate_synthetic(bbox=DEMO_BBOX, seed=42):
    rng = np.random.default_rng(seed)
    west, south, east, north = bbox
    lons = np.arange(west + CELL / 2, east, CELL)
    lats = np.arange(south + CELL / 2, north, CELL)
    if lons.size == 0 or lats.size == 0:
        raise ValueError("Bounding box is too small for a 0.25 degree grid")

    ny, nx = lats.size, lons.size
    spatial = 0.15 + rng.gamma(1.4, 0.45, size=(ny, nx))
    spatial *= np.linspace(0.65, 1.35, ny)[:, None]
    p_modis = np.clip(rng.normal(0.55, 0.08, size=(ny, nx)), 0.35, 0.75)
    p_viirs = np.clip(rng.normal(0.85, 0.06, size=(ny, nx)), 0.65, 0.97)
    season = np.array(
        [0.05, 0.06, 0.09, 0.14, 0.25, 0.55, 1.55, 2.00, 2.25, 1.25, 0.35, 0.12]
    )
    year_factor = {y: 1.0 + 0.035 * (y - 2013) for y in range(2013, 2027)}
    year_factor[2018] *= 1.7
    year_factor[2020] *= 2.4

    columns = {
        "latitude": [],
        "longitude": [],
        "acq_date": [],
        "acq_time": [],
        "satellite": [],
        "instrument": [],
        "confidence": [],
        "frp": [],
        "daynight": [],
        "type": [],
        "sensor": [],
    }

    for i in range(ny):
        for j in range(nx):
            for year in range(2013, 2027):
                for month in range(1, 13):
                    if year == 2026 and month > 10:
                        continue
                    mu = 1.1 * spatial[i, j] * season[month - 1] * year_factor[year]
                    latent = int(rng.poisson(mu * 1.6))
                    if latent == 0:
                        continue
                    modis_n = int(rng.binomial(latent, p_modis[i, j])) if year <= 2024 else 0
                    viirs_n = int(rng.binomial(latent, p_viirs[i, j]))
                    days = calendar.monthrange(year, month)[1]

                    for sensor, n in (("MODIS", modis_n), ("VIIRS", viirs_n)):
                        if n == 0:
                            continue
                        lat = lats[i] + rng.uniform(-CELL / 2, CELL / 2, n)
                        lon = lons[j] + rng.uniform(-CELL / 2, CELL / 2, n)
                        day = rng.integers(1, days + 1, n)
                        hour = rng.integers(0, 24, n)
                        minute = rng.integers(0, 60, n)
                        if sensor == "MODIS":
                            sat = rng.choice(["Terra", "Aqua"], n)
                            conf = rng.integers(15, 100, n)
                            inst = "MODIS"
                        else:
                            sat = rng.choice(["NPP", "NOAA-20", "NOAA-21"], n)
                            conf = rng.choice(["l", "n", "h"], n, p=[0.18, 0.48, 0.34])
                            inst = "VIIRS"

                        columns["latitude"].extend(lat.tolist())
                        columns["longitude"].extend(lon.tolist())
                        columns["acq_date"].extend(
                            [
                                f"{year:04d}-{month:02d}-{int(d):02d}"
                                for d in day
                            ]
                        )
                        columns["acq_time"].extend(
                            [f"{int(h):02d}{int(m):02d}" for h, m in zip(hour, minute)]
                        )
                        columns["satellite"].extend(sat.tolist())
                        columns["instrument"].extend([inst] * n)
                        columns["confidence"].extend(conf.tolist())
                        columns["frp"].extend(rng.lognormal(1.2, 1.0, n).round(1).tolist())
                        columns["daynight"].extend(rng.choice(["D", "N"], n).tolist())
                        columns["type"].extend([sensor] * n)
                        columns["sensor"].extend([sensor] * n)

    frame = pd.DataFrame(columns)
    frame["frp"] = frame["frp"].astype(float)
    return frame


def _confidence_numeric(series):
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    text = series.astype(str).str.strip().str.lower()
    mapping = {
        "l": 20.0,
        "low": 20.0,
        "n": 60.0,
        "nominal": 60.0,
        "h": 85.0,
        "high": 85.0,
    }
    mapped = text.map(mapping)
    return mapped.fillna(pd.to_numeric(text, errors="coerce"))


KNOWN_COLUMNS = {
    "latitude",
    "longitude",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "frp",
    "type",
    "sensor",
}


def _read_hotspots(path, sensor=None):
    wanted = lambda name: str(name).strip().lstrip("\ufeff").lower() in KNOWN_COLUMNS
    raw = pd.read_csv(path, usecols=wanted, low_memory=False)
    raw.columns = [str(c).strip().lstrip("\ufeff").lower() for c in raw.columns]
    for required in ("latitude", "longitude", "acq_date"):
        if required not in raw.columns:
            raise ValueError(f"{path} is missing required column '{required}'")

    instrument = raw.get("instrument", pd.Series("", index=raw.index))
    instrument = instrument.astype(str).str.upper()
    sensor_col = pd.Series("", index=raw.index, dtype=object)
    sensor_col[instrument.str.contains("VIIRS", na=False)] = "VIIRS"
    sensor_col[instrument.str.contains("MODIS", na=False)] = "MODIS"
    fire_type = raw.get("type", pd.Series("", index=raw.index)).astype(str).str.upper()
    sensor_col[(sensor_col == "") & fire_type.str.contains("VIIRS", na=False)] = "VIIRS"
    sensor_col[(sensor_col == "") & fire_type.str.contains("MODIS", na=False)] = "MODIS"
    if "sensor" in raw.columns:
        provided = raw["sensor"].astype(str).str.upper().str.strip()
        sensor_col = sensor_col.mask(sensor_col == "", provided)
    if sensor is not None:
        sensor_col = sensor_col.mask(sensor_col == "", sensor.upper())
    sensor_col = sensor_col.replace({"": np.nan})

    dates = pd.to_datetime(raw["acq_date"], errors="coerce")
    if "acq_time" in raw.columns:
        clock = (
            raw["acq_time"]
            .astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.replace(":", "", regex=False)
            .str.strip()
            .str.zfill(4)
        )
        hours = pd.to_numeric(clock.str[:2], errors="coerce").fillna(0)
        minutes = pd.to_numeric(clock.str[2:4], errors="coerce").fillna(0)
    else:
        hours = pd.Series(0, index=raw.index)
        minutes = pd.Series(0, index=raw.index)
    timestamp = dates + pd.to_timedelta(hours, unit="h") + pd.to_timedelta(minutes, unit="m")
    satellite = (
        raw["satellite"].astype(str)
        if "satellite" in raw.columns
        else pd.Series("", index=raw.index)
    )

    out = pd.DataFrame(
        {
            "latitude": pd.to_numeric(raw["latitude"], errors="coerce"),
            "longitude": pd.to_numeric(raw["longitude"], errors="coerce"),
            "acq_date": dates,
            "timestamp": timestamp,
            "confidence": _confidence_numeric(
                raw.get("confidence", pd.Series(np.nan, index=raw.index))
            ),
            "frp": pd.to_numeric(
                raw.get("frp", pd.Series(np.nan, index=raw.index)), errors="coerce"
            ),
            "satellite": satellite,
            "sensor": sensor_col,
        }
    )
    out = out[out["sensor"].isin(SENSORS)]
    out = out.dropna(subset=["latitude", "longitude", "acq_date", "timestamp"])
    out = out[
        out["latitude"].between(-90, 90) & out["longitude"].between(-180, 180)
    ]
    return out


def load_hotspots(paths, sensor=None):
    frames = []
    for path in paths:
        frames.append(_read_hotspots(Path(path), sensor=sensor))
    if not frames:
        raise ValueError("No hotspot files were provided")
    return pd.concat(frames, ignore_index=True)


def filter_quality(hotspots):
    keep = hotspots["confidence"].isna() | (
        hotspots["confidence"] >= MIN_CONFIDENCE
    )
    return hotspots[keep].copy()


def prepare_detections(hotspots, tz_offset=0.0):
    df = hotspots.copy()
    df["timestamp"] = df["timestamp"] + pd.Timedelta(hours=float(tz_offset))
    df["year"] = df["timestamp"].dt.year.astype("int64")
    df["month"] = df["timestamp"].dt.month.astype("int64")
    df["local_date"] = df["timestamp"].dt.normalize()
    df["cell_lon"] = (np.floor(df["longitude"] / CELL) * CELL + CELL / 2).round(3)
    df["cell_lat"] = (np.floor(df["latitude"] / CELL) * CELL + CELL / 2).round(3)
    subset = [
        "latitude",
        "longitude",
        "timestamp",
        "confidence",
        "frp",
        "satellite",
        "sensor",
    ]
    return df.drop_duplicates(subset=subset)


def aggregate_monthly(prepared):
    keys = ["cell_lat", "cell_lon", "year", "month", "sensor"]
    raw = (
        prepared.groupby(keys)
        .size()
        .rename("detections")
        .reset_index()
    )
    unique = prepared.drop_duplicates(
        subset=["cell_lat", "cell_lon", "local_date", "sensor"]
    )
    deduplicated = (
        unique.groupby(keys)
        .size()
        .rename("cell_days")
        .reset_index()
    )
    out = raw.merge(deduplicated, on=keys, how="outer")
    out[["detections", "cell_days"]] = (
        out[["detections", "cell_days"]].fillna(0).astype("int64")
    )
    return out


def calibrate(monthly, value_col="cell_days"):
    wide = (
        monthly.pivot_table(
            index=["cell_lat", "cell_lon", "year", "month"],
            columns="sensor",
            values=value_col,
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )
    for sensor in SENSORS:
        if sensor not in wide.columns:
            wide[sensor] = 0
    wide[list(SENSORS)] = wide[list(SENSORS)].astype(int)

    modis_years = set(wide.loc[wide["MODIS"] > 0, "year"].unique())
    viirs_years = set(wide.loc[wide["VIIRS"] > 0, "year"].unique())
    common_years = sorted(modis_years & viirs_years)

    if common_years:
        y0, y1 = int(common_years[0]), int(common_years[-1])
        overlap = wide[(wide["year"] >= y0) & (wide["year"] <= y1)].copy()
    else:
        y0 = y1 = None
        overlap = wide.iloc[0:0].copy()

    total_modis = float(overlap["MODIS"].sum())
    total_viirs = float(overlap["VIIRS"].sum())
    global_ratio = total_modis / total_viirs if total_viirs > 0 else 1.0

    per_cell = (
        overlap.groupby(["cell_lat", "cell_lon"])
        .agg(
            modis_sum=("MODIS", "sum"),
            viirs_sum=("VIIRS", "sum"),
            months=("VIIRS", lambda s: int((s > 0).sum())),
        )
        .reset_index()
    )
    if per_cell.empty:
        per_cell = pd.DataFrame(
            columns=["cell_lat", "cell_lon", "modis_sum", "viirs_sum", "months"]
        )
    per_cell["ratio_cell"] = np.where(
        (per_cell["viirs_sum"] > 0) & (per_cell["modis_sum"] > 0),
        per_cell["modis_sum"] / per_cell["viirs_sum"].replace(0, np.nan),
        np.nan,
    )
    per_cell["weight"] = per_cell["months"] / (per_cell["months"] + SHRINK_MONTHS)
    per_cell["ratio"] = (
        per_cell["weight"] * per_cell["ratio_cell"].fillna(global_ratio)
        + (1 - per_cell["weight"]) * global_ratio
    ).clip(*RATIO_BOUNDS)
    per_cell = per_cell[
        ["cell_lat", "cell_lon", "ratio", "ratio_cell", "months"]
    ].rename(columns={"months": "overlap_months"})

    x = overlap["VIIRS"].to_numpy(dtype=float)
    y = overlap["MODIS"].to_numpy(dtype=float)
    mask = x > 0
    if mask.sum() >= 10:
        slope, intercept = np.polyfit(x[mask], y[mask], 1)
        predicted = slope * x[mask] + intercept
        ss_res = float(((y[mask] - predicted) ** 2).sum())
        ss_tot = float(((y[mask] - y[mask].mean()) ** 2).sum())
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    else:
        slope = float(global_ratio)
        intercept = 0.0
        r2 = float("nan")

    stats = {
        "metric": value_col,
        "overlap_start": y0,
        "overlap_end": y1,
        "overlap_cell_months": int(len(overlap)),
        "modis_total_overlap": total_modis,
        "viirs_total_overlap": total_viirs,
        "global_ratio_modis_over_viirs": float(global_ratio),
        "fit_slope": float(slope),
        "fit_intercept": float(intercept),
        "fit_r2": float(r2),
        "shrink_months": SHRINK_MONTHS,
        "min_confidence": MIN_CONFIDENCE,
        "grid_degrees": CELL,
    }
    return wide, per_cell, stats, overlap


def _harmonized_metric(wide, per_cell, stats, suffix):
    out = wide.merge(per_cell, on=["cell_lat", "cell_lon"], how="left")
    if "ratio_cell" not in out.columns:
        out["ratio_cell"] = np.nan
    if "overlap_months" not in out.columns:
        out["overlap_months"] = 0
    out["ratio"] = (
        pd.to_numeric(out["ratio"], errors="coerce")
        .fillna(stats["global_ratio_modis_over_viirs"])
        .clip(*RATIO_BOUNDS)
    )
    modis_present = out["MODIS"] > 0
    out["count"] = np.where(
        modis_present, out["MODIS"], out["VIIRS"] * out["ratio"]
    ).round(2)
    out["calibration_basis"] = np.where(
        out["ratio_cell"].notna(), "cell", "global"
    )
    out = out.rename(
        columns={
            "MODIS": f"modis_{suffix}",
            "VIIRS": f"viirs_{suffix}",
            "ratio": f"ratio_{suffix}",
            "count": f"count_harmonized_{suffix}",
            "ratio_cell": f"ratio_cell_{suffix}",
            "overlap_months": f"overlap_months_{suffix}",
            "calibration_basis": f"calibration_basis_{suffix}",
        }
    )
    return out[
        [
            "cell_lat",
            "cell_lon",
            "year",
            "month",
            f"modis_{suffix}",
            f"viirs_{suffix}",
            f"ratio_{suffix}",
            f"ratio_cell_{suffix}",
            f"overlap_months_{suffix}",
            f"calibration_basis_{suffix}",
            f"count_harmonized_{suffix}",
        ]
    ]


def harmonize_series(
    wide_cell_days,
    per_cell_cell_days,
    stats_cell_days,
    wide_detections,
    per_cell_detections,
    stats_detections,
):
    cell_days = _harmonized_metric(
        wide_cell_days, per_cell_cell_days, stats_cell_days, "cell_days"
    )
    detections = _harmonized_metric(
        wide_detections, per_cell_detections, stats_detections, "detections"
    )
    keys = ["cell_lat", "cell_lon", "year", "month"]
    out = cell_days.merge(detections, on=keys, how="outer")
    out["source"] = np.where(
        out["modis_cell_days"] > 0,
        "modis",
        np.where(out["viirs_cell_days"] > 0, "viirs_calibrated", "none"),
    )
    out = out[out["source"] != "none"]
    out["year"] = out["year"].astype("int64")
    out["month"] = out["month"].astype("int64")
    out["overlap_months"] = (
        pd.to_numeric(out["overlap_months_cell_days"], errors="coerce")
        .fillna(0)
        .astype("int64")
    )
    out["calibration_basis"] = (
        out["calibration_basis_cell_days"].fillna("global")
    )
    out["days_in_month"] = pd.to_datetime(
        dict(year=out["year"], month=out["month"], day=1)
    ).dt.days_in_month.astype("int64")
    out["cell_days_per_day"] = (
        out["count_harmonized_cell_days"] / out["days_in_month"]
    ).round(3)
    out["detections_per_day"] = (
        out["count_harmonized_detections"] / out["days_in_month"]
    ).round(3)
    columns = [
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
    for column in (
        "modis_cell_days",
        "viirs_cell_days",
        "modis_detections",
        "viirs_detections",
    ):
        out[column] = out[column].fillna(0).astype("int64")
    return out[columns].sort_values(["year", "month", "cell_lat", "cell_lon"])


def plot_fit(wide, harmonized, stats, path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    y0 = stats.get("overlap_start")
    y1 = stats.get("overlap_end")
    if y0 is not None:
        overlap = wide[(wide["year"] >= y0) & (wide["year"] <= y1)]
    else:
        overlap = wide.iloc[0:0]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    ax = axes[0]
    x = overlap["VIIRS"].to_numpy(dtype=float)
    y = overlap["MODIS"].to_numpy(dtype=float)
    if len(x) > 20000:
        pick = np.random.default_rng(0).choice(len(x), 20000, replace=False)
        x, y = x[pick], y[pick]
    ax.scatter(x, y, s=10, alpha=0.25, color="#0072B2", linewidths=0)
    if len(x) > 0:
        upper = max(float(x.max()), float(y.max()), 1.0)
        grid = np.linspace(0, upper, 100)
        slope = stats["fit_slope"]
        intercept = stats["fit_intercept"]
        ax.plot(
            grid,
            slope * grid + intercept,
            color="#D55E00",
            linewidth=2,
            label=f"MODIS = {slope:.2f} x VIIRS + {intercept:.2f}",
        )
        ax.plot(grid, grid, linestyle="--", color="#555555", linewidth=1, label="1:1")
    else:
        upper = 1.0
    ax.set_xlim(0, upper)
    ax.set_ylim(0, upper)
    ax.set_xlabel("VIIRS fire cell-days per 0.25 deg cell-month")
    ax.set_ylabel("MODIS fire cell-days per 0.25 deg cell-month")
    ax.set_title(
        f"VIIRS-to-MODIS overlap fit, cell-days ({y0 or 'n/a'}-{y1 or 'n/a'})",
        fontsize=11,
    )
    ax.text(
        0.03,
        0.97,
        (
            f"R2 = {stats['fit_r2']:.3f}\n"
            f"ratio = {stats['global_ratio_modis_over_viirs']:.2f}\n"
            f"cell-months = {stats['overlap_cell_months']:,}"
        ),
        transform=ax.transAxes,
        va="top",
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", edgecolor="#cccccc"),
    )
    if len(x) > 0:
        ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=0.25)

    ax2 = axes[1]
    totals = (
        harmonized.groupby(["year", "month"])
        .agg(
            modis=("modis_cell_days", "sum"),
            viirs=("viirs_cell_days", "sum"),
            harmonized=("count_harmonized_cell_days", "sum"),
        )
        .reset_index()
    )
    if not totals.empty:
        dates = pd.to_datetime(dict(year=totals["year"], month=totals["month"], day=1))
        ax2.plot(dates, totals["modis"], color="#0072B2", linewidth=1.2, label="MODIS")
        ax2.plot(dates, totals["viirs"], color="#D55E00", linewidth=1.2, label="VIIRS")
        ax2.plot(
            dates,
            totals["harmonized"],
            color="#000000",
            linewidth=1.6,
            linestyle="--",
            label="Harmonized",
        )
        if y0 is not None and y1 is not None:
            ax2.axvspan(
                pd.Timestamp(y0, 1, 1),
                pd.Timestamp(y1, 12, 31),
                color="#999999",
                alpha=0.12,
                label="Calibration overlap",
            )
    ax2.set_title("Monthly fire cell-days in the calibrated region", fontsize=11)
    ax2.set_ylabel("Fire cell-days per month")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def run_pipeline(
    hotspots,
    outdir,
    synthetic=False,
    bbox=None,
    region=None,
    source_files=(),
    dedup=True,
    tz_offset=0.0,
    parquet=True,
    export_hotspots=False,
    end_month=None,
    start_month=None,
):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    filtered = filter_quality(hotspots)
    if filtered.empty:
        raise ValueError("No hotspots left after quality filtering")

    prepared = prepare_detections(filtered, tz_offset=tz_offset)
    if start_month is not None:
        floor = pd.Period(str(start_month), freq="M")
        prepared = prepared[
            prepared["year"] * 100 + prepared["month"]
            >= floor.year * 100 + floor.month
        ]
    if end_month is not None:
        cutoff = pd.Period(str(end_month), freq="M")
        prepared = prepared[
            prepared["year"] * 100 + prepared["month"]
            <= cutoff.year * 100 + cutoff.month
        ]
    monthly = aggregate_monthly(prepared)
    if monthly.empty:
        raise ValueError("No hotspots left after temporal aggregation")

    wide_cell_days, per_cell_cell_days, stats_cell_days, _ = calibrate(
        monthly, "cell_days"
    )
    wide_detections, per_cell_detections, stats_detections, _ = calibrate(
        monthly, "detections"
    )
    harmonized = harmonize_series(
        wide_cell_days,
        per_cell_cell_days,
        stats_cell_days,
        wide_detections,
        per_cell_detections,
        stats_detections,
    )

    harmonized.to_csv(outdir / "harmonized_monthly.csv", index=False)
    per_cell_cell_days.to_csv(outdir / "cell_calibration.csv", index=False)
    plot_fit(
        wide_cell_days,
        harmonized,
        stats_cell_days,
        outdir / "harmonization_fit.png",
    )

    parquet_path = outdir / "harmonized_monthly.parquet"
    wrote_parquet = False
    if parquet and not harmonized.empty:
        try:
            harmonized.to_parquet(parquet_path, index=False)
            wrote_parquet = True
        except (ImportError, ValueError, OSError):
            wrote_parquet = False

    hotspot_path = None
    if export_hotspots:
        spot_columns = [
            "latitude",
            "longitude",
            "timestamp",
            "sensor",
            "satellite",
            "confidence",
            "frp",
            "cell_lat",
            "cell_lon",
            "year",
            "month",
        ]
        spots = prepared[spot_columns].copy()
        spots["acq_date"] = spots["timestamp"].dt.date
        try:
            hotspot_path = outdir / "hotspots.parquet"
            spots.to_parquet(hotspot_path, index=False)
        except (ImportError, ValueError, OSError):
            hotspot_path = outdir / "hotspots.csv"
            spots.to_csv(hotspot_path, index=False)

    last = harmonized.iloc[-1] if not harmonized.empty else None
    meta = {
        "synthetic": bool(synthetic),
        "bbox": list(bbox) if bbox is not None else None,
        "region": str(region) if region is not None else None,
        "source_files": [Path(p).name for p in source_files],
        "raw_hotspots": int(len(hotspots)),
        "filtered_hotspots": int(len(filtered)),
        "sensors": sorted(filtered["sensor"].unique().tolist()),
        "years": sorted(
            int(y) for y in harmonized["year"].dropna().unique().tolist()
        ),
        "metric": "cell_days",
        "default_metric": "cell_days" if dedup else "detections",
        "metrics": ["cell_days", "detections"],
        "tz_offset_hours": float(tz_offset),
        "max_year_month": (
            f"{int(last['year'])}-{int(last['month']):02d}" if last is not None else None
        ),
        "start_month": str(start_month) if start_month is not None else None,
        "end_month": str(end_month) if end_month is not None else None,
        "parquet": wrote_parquet,
        "hotspot_file": hotspot_path.name if hotspot_path is not None else None,
        "calibration": stats_cell_days,
        "calibration_detections": stats_detections,
    }
    (outdir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def run_demo(
    outdir,
    seed=42,
    dedup=True,
    tz_offset=0.0,
    parquet=True,
    export_hotspots=True,
):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    synthetic = generate_synthetic(seed=seed)
    raw_path = outdir / "synthetic_hotspots.csv"
    synthetic.to_csv(raw_path, index=False)
    hotspots = load_hotspots([raw_path])
    return run_pipeline(
        hotspots,
        outdir,
        synthetic=True,
        bbox=DEMO_BBOX,
        source_files=[raw_path.name],
        dedup=dedup,
        tz_offset=tz_offset,
        parquet=parquet,
        export_hotspots=export_hotspots,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Harmonize MODIS and VIIRS active-fire hotspots into a "
        "monthly 0.25 degree burning-activity series."
    )
    parser.add_argument("--demo", action="store_true", help="Generate and run synthetic data")
    parser.add_argument("--modis", nargs="+", help="MODIS FIRMS CSV file(s)")
    parser.add_argument("--viirs", nargs="+", help="VIIRS FIRMS CSV file(s)")
    parser.add_argument("--outdir", default="data", help="Output directory")
    parser.add_argument(
        "--region",
        help="Human-readable region name stored in meta.json (e.g. Argentina)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Synthetic data seed")
    parser.add_argument(
        "--no-dedup",
        action="store_true",
        help="Make raw detections the default metric (both metrics are always written)",
    )
    parser.add_argument(
        "--tz-offset",
        type=float,
        default=0.0,
        help="Hours to add to UTC acquisition time before assigning months (e.g. -8)",
    )
    parser.add_argument(
        "--no-parquet",
        action="store_true",
        help="Do not write the optional Parquet copy of the harmonized table",
    )
    parser.add_argument(
        "--export-hotspots",
        action="store_true",
        help="Also write hotspot-level records for download in the app (can be large)",
    )
    parser.add_argument(
        "--start-month",
        metavar="YYYY-MM",
        help="Drop records before this local month",
    )
    parser.add_argument(
        "--end-month",
        metavar="YYYY-MM",
        help="Drop records after this local month (useful to exclude a partial month)",
    )
    args = parser.parse_args()
    for option in ("start_month", "end_month"):
        value = getattr(args, option)
        if value is not None:
            try:
                pd.Period(value, freq="M")
            except ValueError:
                parser.error(f"--{option.replace('_', '-')} must use YYYY-MM format")
    if args.start_month is not None and args.end_month is not None:
        if pd.Period(args.start_month, freq="M") > pd.Period(args.end_month, freq="M"):
            parser.error("--start-month must not be after --end-month")

    if args.demo:
        meta = run_demo(
            args.outdir,
            seed=args.seed,
            dedup=not args.no_dedup,
            tz_offset=args.tz_offset,
            parquet=not args.no_parquet,
            export_hotspots=True,
        )
    else:
        if not args.modis or not args.viirs:
            parser.error("Provide --modis and --viirs files, or use --demo")
        hotspots = pd.concat(
            [
                load_hotspots(args.modis, sensor="MODIS"),
                load_hotspots(args.viirs, sensor="VIIRS"),
            ],
            ignore_index=True,
        )
        meta = run_pipeline(
            hotspots,
            args.outdir,
            synthetic=False,
            bbox=None,
            region=args.region,
            source_files=list(args.modis) + list(args.viirs),
            dedup=not args.no_dedup,
            tz_offset=args.tz_offset,
            parquet=not args.no_parquet,
            export_hotspots=args.export_hotspots,
            end_month=args.end_month,
            start_month=args.start_month,
        )

    cal = meta["calibration"]
    print(f"Hotspots kept: {meta['filtered_hotspots']:,} of {meta['raw_hotspots']:,}")
    print(
        f"Default metric: {meta['default_metric']} "
        f"(both cell_days and detections are written)"
    )
    print(f"Sensors: {', '.join(meta['sensors'])}")
    print(
        "Overlap: "
        f"{cal['overlap_start']}-{cal['overlap_end']} | "
        f"ratio MODIS/VIIRS = {cal['global_ratio_modis_over_viirs']:.3f} | "
        f"slope = {cal['fit_slope']:.3f} | R2 = {cal['fit_r2']:.3f}"
    )
    print(f"Wrote outputs to {Path(args.outdir).resolve()}")


if __name__ == "__main__":
    main()
