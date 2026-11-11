import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from audio_engine import AudioSnapshot
from performance import PerformanceMonitor


class FakeEngine:
    def get_status(self) -> AudioSnapshot:
        return AudioSnapshot(state="playing", output_peak=0.5, latency_ms=5.33)


class PerformanceMonitorTests(unittest.TestCase):
    def test_monitor_writes_csv_and_json_reports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "benchmark.csv"
            monitor = PerformanceMonitor(
                FakeEngine(),
                report,
                interval_seconds=0.01,
                configuration={"scenario": "test"},
            )
            with (
                patch("performance._read_number", return_value=None),
                patch("performance._read_throttled", return_value=""),
            ):
                monitor.start()
                time.sleep(0.035)
                summary = monitor.stop()

            self.assertTrue(report.is_file())
            self.assertTrue(report.with_suffix(".json").is_file())
            self.assertGreaterEqual(summary["sample_count"], 2)
            saved = json.loads(report.with_suffix(".json").read_text())
            self.assertEqual(saved["configuration"]["scenario"], "test")
            self.assertEqual(saved["power_measurement"], "unavailable")
            self.assertIsNone(saved["acceptance"]["temperature_below_80_c"])
            self.assertFalse(saved["passed"])


if __name__ == "__main__":
    unittest.main()
