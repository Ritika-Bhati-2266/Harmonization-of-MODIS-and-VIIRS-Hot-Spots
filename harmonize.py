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


def _read_hotspots(path, sensor=None):
    raw = pd.read_csv(path, low_memory=False)
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    for required in ("latitude", "longitude", "acq_date"):
        if required not in raw.columns:
            raise ValueError(f"{path} is missing required column '{required}'")

    if "sensor" in raw.columns:
        sensor_col = raw["sensor"].astype(str).str.upper()
    else:
        instrument = raw.get("instrument", pd.Series("", index=raw.index))
        instrument = instrument.astype(str).str.upper()
        sensor_col = pd.Series("", index=raw.index, dtype=object)
        sensor_col[instrument.str.contains("VIIRS")] = "VIIRS"
        sensor_col[instrument.str.contains("MODIS")] = "MODIS"
        if sensor is not None:
            sensor_col[sensor_col == ""] = sensor.upper()

    out = pd.DataFrame(
        {
            "latitude": pd.to_numeric(raw["latitude"], errors="coerce"),
            "longitude": pd.to_numeric(raw["longitude"], errors="coerce"),
            "acq_date": pd.to_datetime(raw["acq_date"], errors="coerce"),
            "confidence": _confidence_numeric(
                raw.get("confidence", pd.Series(np.nan, index=raw.index))
            ),
            "frp": pd.to_numeric(
                raw.get("frp", pd.Series(np.nan, index=raw.index)), errors="coerce"
            ),
            "satellite": raw.get("satellite", "").astype(str),
            "sensor": sensor_col,
        }
    )
    out = out[out["sensor"].isin(SENSORS)]
    out = out.dropna(subset=["latitude", "longitude", "acq_date"])
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


def aggregate_monthly(hotspots):
    df = hotspots.copy()
    df["year"] = df["acq_date"].dt.year
    df["month"] = df["acq_date"].dt.month
    df["cell_lon"] = (np.floor(df["longitude"] / CELL) * CELL + CELL / 2).round(3)
    df["cell_lat"] = (np.floor(df["latitude"] / CELL) * CELL + CELL / 2).round(3)
    grouped = (
        df.groupby(["cell_lat", "cell_lon", "year", "month", "sensor"])
        .size()
        .rename("count")
        .reset_index()
    )
    return grouped


def calibrate(monthly):
    wide = (
        monthly.pivot_table(
            index=["cell_lat", "cell_lon", "year", "month"],
            columns="sensor",
            values="count",
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


def harmonize_series(wide, per_cell, stats):
    global_ratio = stats["global_ratio_modis_over_viirs"]
    out = wide.merge(per_cell, on=["cell_lat", "cell_lon"], how="left")
    out["ratio"] = out["ratio"].fillna(global_ratio).clip(*RATIO_BOUNDS)
    out["modis_count"] = out["MODIS"]
    out["viirs_count"] = out["VIIRS"]
    modis_present = out["MODIS"] > 0
    out["count_harmonized"] = np.where(
        modis_present, out["MODIS"], out["VIIRS"] * out["ratio"]
    )
    out["source"] = np.where(
        modis_present, "modis", np.where(out["VIIRS"] > 0, "viirs_calibrated", "none")
    )
    out = out[out["source"] != "none"]
    out["count_harmonized"] = out["count_harmonized"].round(2)
    columns = [
        "cell_lat",
        "cell_lon",
        "year",
        "month",
        "modis_count",
        "viirs_count",
        "count_harmonized",
        "ratio",
        "source",
    ]
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
    ax.set_xlabel("VIIRS hotspots per 0.25 deg cell-month")
    ax.set_ylabel("MODIS hotspots per 0.25 deg cell-month")
    ax.set_title(
        f"VIIRS-to-MODIS overlap fit ({y0 or 'n/a'}-{y1 or 'n/a'})",
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
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=0.25)

    ax2 = axes[1]
    totals = (
        harmonized.groupby(["year", "month"])
        .agg(
            modis=("modis_count", "sum"),
            viirs=("viirs_count", "sum"),
            harmonized=("count_harmonized", "sum"),
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
    ax2.set_title("Monthly hotspot totals in the calibrated region", fontsize=11)
    ax2.set_ylabel("Hotspots per month")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def run_pipeline(hotspots, outdir, synthetic=False, bbox=None, source_files=()):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    filtered = filter_quality(hotspots)
    if filtered.empty:
        raise ValueError("No hotspots left after quality filtering")

    monthly = aggregate_monthly(filtered)
    wide, per_cell, stats, _ = calibrate(monthly)
    harmonized = harmonize_series(wide, per_cell, stats)

    harmonized.to_csv(outdir / "harmonized_monthly.csv", index=False)
    per_cell.to_csv(outdir / "cell_calibration.csv", index=False)
    plot_fit(wide, harmonized, stats, outdir / "harmonization_fit.png")

    meta = {
        "synthetic": bool(synthetic),
        "bbox": list(bbox) if bbox is not None else None,
        "source_files": [str(p) for p in source_files],
        "raw_hotspots": int(len(hotspots)),
        "filtered_hotspots": int(len(filtered)),
        "sensors": sorted(filtered["sensor"].unique().tolist()),
        "years": sorted(
            int(y) for y in harmonized["year"].dropna().unique().tolist()
        ),
        "calibration": stats,
    }
    (outdir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def run_demo(outdir, seed=42):
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
    parser.add_argument("--seed", type=int, default=42, help="Synthetic data seed")
    args = parser.parse_args()

    if args.demo:
        meta = run_demo(args.outdir, seed=args.seed)
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
            source_files=list(args.modis) + list(args.viirs),
        )

    cal = meta["calibration"]
    print(f"Hotspots kept: {meta['filtered_hotspots']:,} of {meta['raw_hotspots']:,}")
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
