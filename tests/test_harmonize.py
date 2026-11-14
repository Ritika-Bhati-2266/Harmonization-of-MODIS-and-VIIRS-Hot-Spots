import tempfile
import unittest
from pathlib import Path

import pandas as pd

import harmonize as h


def write_hotspots(tmp, rows, name="hotspots.csv"):
    path = Path(tmp) / name
    pd.DataFrame(rows).to_csv(path, index=False)
    return h.load_hotspots([path])


def prepared(tmp, rows, tz_offset=0.0):
    with tempfile.TemporaryDirectory() as folder:
        hot = h.filter_quality(write_hotspots(folder, rows))
    return h.prepare_detections(hot, tz_offset=tz_offset)


class ReadAndFilterTest(unittest.TestCase):
    def test_confidence_filter(self):
        rows = [
            {
                "latitude": 36.1,
                "longitude": -121.1,
                "acq_date": "2020-08-01",
                "acq_time": 1200,
                "confidence": 10,
                "frp": 1.0,
                "satellite": "Terra",
                "instrument": "MODIS",
            },
            {
                "latitude": 36.2,
                "longitude": -121.2,
                "acq_date": "2020-08-01",
                "acq_time": 1200,
                "confidence": 80,
                "frp": 1.0,
                "satellite": "Terra",
                "instrument": "MODIS",
            },
            {
                "latitude": 36.3,
                "longitude": -121.3,
                "acq_date": "2020-08-01",
                "acq_time": 1200,
                "confidence": "l",
                "frp": 1.0,
                "satellite": "NPP",
                "instrument": "VIIRS",
            },
            {
                "latitude": 36.4,
                "longitude": -121.4,
                "acq_date": "2020-08-01",
                "acq_time": 1200,
                "confidence": "h",
                "frp": 1.0,
                "satellite": "NPP",
                "instrument": "VIIRS",
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            hot = write_hotspots(tmp, rows)
        kept = h.filter_quality(hot)
        self.assertEqual(len(kept), 2)
        self.assertEqual(set(kept["sensor"]), {"MODIS", "VIIRS"})

    def test_parses_clock_into_timestamp(self):
        rows = [
            {
                "latitude": 36.1,
                "longitude": -121.1,
                "acq_date": "2020-01-31",
                "acq_time": "2330",
                "confidence": 80,
                "instrument": "MODIS",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            hot = write_hotspots(tmp, rows)
        self.assertEqual(hot.iloc[0]["timestamp"], pd.Timestamp("2020-01-31 23:30"))


class AggregationTest(unittest.TestCase):
    def rows(self):
        return [
            {
                "latitude": 36.1,
                "longitude": -121.1,
                "acq_date": "2020-08-01",
                "acq_time": 1200,
                "confidence": 80,
                "frp": 3.0,
                "satellite": "Terra",
                "instrument": "MODIS",
            },
            {
                "latitude": 36.12,
                "longitude": -121.12,
                "acq_date": "2020-08-01",
                "acq_time": 1330,
                "confidence": 85,
                "frp": 8.0,
                "satellite": "Aqua",
                "instrument": "MODIS",
            },
        ]

    def test_cell_day_and_detection_metrics(self):
        monthly = h.aggregate_monthly(prepared(None, self.rows()))
        self.assertEqual(int(monthly["cell_days"].sum()), 1)
        self.assertEqual(int(monthly["detections"].sum()), 2)

    def test_tz_offset_can_shift_month(self):
        rows = [
            {
                "latitude": 36.1,
                "longitude": -121.1,
                "acq_date": "2020-01-31",
                "acq_time": "2330",
                "confidence": 80,
                "instrument": "MODIS",
            }
        ]
        utc = h.aggregate_monthly(prepared(None, rows, tz_offset=0))
        shifted = h.aggregate_monthly(prepared(None, rows, tz_offset=2))
        self.assertEqual(int(utc.iloc[0]["month"]), 1)
        self.assertEqual(int(shifted.iloc[0]["month"]), 2)
        self.assertEqual(int(shifted.iloc[0]["year"]), 2020)


class PipelineTest(unittest.TestCase):
    def build_hotspots(self, tmp, seed=11):
        frame = h.generate_synthetic(bbox=(-121.5, 36.0, -120.5, 37.0), seed=seed)
        path = Path(tmp) / "both.csv"
        frame.to_csv(path, index=False)
        return h.load_hotspots([path])

    def test_single_sensor_falls_back_to_global_ratio(self):
        with tempfile.TemporaryDirectory() as tmp:
            frame = h.generate_synthetic(bbox=(-121.5, 36.0, -120.5, 37.0), seed=7)
            frame = frame[frame["sensor"] == "MODIS"]
            path = Path(tmp) / "modis_only.csv"
            frame.to_csv(path, index=False)
            hot = h.load_hotspots([path])
            outdir = Path(tmp) / "out"
            meta = h.run_pipeline(hot, outdir, parquet=False)
            self.assertIsNone(meta["calibration"]["overlap_start"])
            self.assertEqual(meta["calibration"]["global_ratio_modis_over_viirs"], 1.0)
            self.assertGreater(meta["filtered_hotspots"], 0)
            self.assertTrue((outdir / "harmonized_monthly.csv").exists())
            self.assertTrue((outdir / "harmonization_fit.png").exists())

    def test_full_pipeline_with_both_sensors(self):
        with tempfile.TemporaryDirectory() as tmp:
            hot = self.build_hotspots(tmp)
            outdir = Path(tmp) / "out"
            meta = h.run_pipeline(
                hot, outdir, parquet=True, dedup=True, export_hotspots=True
            )
            cal = meta["calibration"]
            self.assertEqual(cal["overlap_start"], 2013)
            self.assertEqual(cal["overlap_end"], 2024)
            self.assertGreater(cal["global_ratio_modis_over_viirs"], 0)
            self.assertLess(cal["global_ratio_modis_over_viirs"], 3)
            self.assertEqual(meta["default_metric"], "cell_days")
            self.assertEqual(meta["metrics"], ["cell_days", "detections"])
            self.assertEqual(meta["max_year_month"], "2026-10")
            self.assertEqual(meta["hotspot_file"], "hotspots.parquet")
            result = pd.read_csv(outdir / "harmonized_monthly.csv")
            self.assertTrue(
                {
                    "modis_cell_days",
                    "viirs_cell_days",
                    "count_harmonized_cell_days",
                    "ratio_cell_days",
                    "modis_detections",
                    "viirs_detections",
                    "count_harmonized_detections",
                    "ratio_detections",
                    "cell_days_per_day",
                    "detections_per_day",
                    "source",
                }
                <= set(result.columns)
            )
            self.assertGreaterEqual(
                result["count_harmonized_detections"].sum(),
                result["count_harmonized_cell_days"].sum(),
            )
            self.assertGreater(len(result), 0)
            self.assertTrue((outdir / "harmonized_monthly.parquet").exists())
            self.assertTrue((outdir / "hotspots.parquet").exists())
            spots = pd.read_parquet(outdir / "hotspots.parquet")
            self.assertTrue(
                {"latitude", "longitude", "timestamp", "sensor", "acq_date"}
                <= set(spots.columns)
            )
            self.assertGreater(len(spots), 0)

    def test_raw_detections_can_be_default_metric(self):
        with tempfile.TemporaryDirectory() as tmp:
            hot = self.build_hotspots(tmp, seed=5)
            meta = h.run_pipeline(hot, Path(tmp) / "out", parquet=False, dedup=False)
            self.assertEqual(meta["default_metric"], "detections")
            self.assertEqual(meta["calibration"]["metric"], "cell_days")
            self.assertEqual(meta["calibration_detections"]["metric"], "detections")

    def test_start_end_month_and_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            hot = self.build_hotspots(tmp, seed=9)
            outdir = Path(tmp) / "out"
            meta = h.run_pipeline(
                hot,
                outdir,
                parquet=False,
                start_month="2020-01",
                end_month="2020-12",
                region="Testland",
            )
            result = pd.read_csv(outdir / "harmonized_monthly.csv")
            self.assertEqual(result["year"].unique().tolist(), [2020])
            self.assertEqual(meta["years"], [2020])
            self.assertEqual(meta["start_month"], "2020-01")
            self.assertEqual(meta["end_month"], "2020-12")
            self.assertEqual(meta["region"], "Testland")

    def test_parquet_matches_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            hot = self.build_hotspots(tmp, seed=3)
            outdir = Path(tmp) / "out"
            h.run_pipeline(hot, outdir, parquet=True)
            csv = pd.read_csv(outdir / "harmonized_monthly.csv")
            parquet = pd.read_parquet(outdir / "harmonized_monthly.parquet")
            pd.testing.assert_frame_equal(
                csv.reset_index(drop=True), parquet.reset_index(drop=True)
            )


if __name__ == "__main__":
    unittest.main()
