from __future__ import annotations

import csv
import json
import os
import platform
import statistics
import subprocess  # nosec B404
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import psutil

from audio_engine import AudioEngine


@dataclass(frozen=True)
class PerformanceSample:
    elapsed_seconds: float
    process_rss_mib: float
    child_rss_mib: float
    combined_rss_mib: float
    system_used_mib: float
    system_available_mib: float
    process_cpu_normalized: float
    system_cpu_percent: float
    thread_count: int
    underruns: int
    overruns: int
    deadline_misses: int
    callback_ms: float
    output_peak: float
    limited_samples: int
    effective_latency_ms: float
    cpu_temperature_c: float | None
    cpu_clock_mhz: float | None
    throttled: str


class PerformanceMonitor:
    def __init__(
        self,
        engine: AudioEngine,
        report_path: str | Path,
        interval_seconds: float = 1.0,
        configuration: dict[str, Any] | None = None,
    ) -> None:
        self.engine = engine
        self.report_path = Path(report_path).expanduser().resolve()
        self.interval_seconds = interval_seconds
        self.configuration = configuration or {}
        self.process = psutil.Process(os.getpid())
        self.samples: list[PerformanceSample] = []
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.thread is not None:
            raise RuntimeError("performance monitor is already running")
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.process.cpu_percent(None)
        psutil.cpu_percent(None)
        self.stop_event.clear()
        self.thread = threading.Thread(
            target=self._run, name="performance-monitor", daemon=True
        )
        self.thread.start()

    def stop(self) -> dict[str, Any]:
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=max(2.0, self.interval_seconds * 2))
        self.thread = None
        self._write_csv()
        summary = self._summary()
        summary_path = self.report_path.with_suffix(".json")
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        return summary

    def _run(self) -> None:
        started = time.monotonic()
        self.samples.append(self._sample(0.0))
        while not self.stop_event.wait(self.interval_seconds):
            self.samples.append(self._sample(time.monotonic() - started))

    def _sample(self, elapsed: float) -> PerformanceSample:
        children = self.process.children(recursive=True)
        child_rss = sum(_safe_rss(child) for child in children)
        process_rss = self.process.memory_info().rss
        memory = psutil.virtual_memory()
        audio = self.engine.get_status()
        return PerformanceSample(
            elapsed_seconds=round(elapsed, 3),
            process_rss_mib=process_rss / 1024**2,
            child_rss_mib=child_rss / 1024**2,
            combined_rss_mib=(process_rss + child_rss) / 1024**2,
            system_used_mib=memory.used / 1024**2,
            system_available_mib=memory.available / 1024**2,
            process_cpu_normalized=self.process.cpu_percent(None),
            system_cpu_percent=psutil.cpu_percent(None),
            thread_count=self.process.num_threads(),
            underruns=audio.underruns,
            overruns=audio.overruns,
            deadline_misses=audio.deadline_misses,
            callback_ms=audio.callback_ms,
            output_peak=audio.output_peak,
            limited_samples=audio.limited_samples,
            effective_latency_ms=audio.latency_ms,
            cpu_temperature_c=_read_number(
                "/sys/class/thermal/thermal_zone0/temp", 1000
            ),
            cpu_clock_mhz=_read_number(
                "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq",
                1000,
            ),
            throttled=_read_throttled(),
        )

    def _write_csv(self) -> None:
        if not self.samples:
            return
        with self.report_path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=asdict(self.samples[0]).keys())
            writer.writeheader()
            writer.writerows(asdict(sample) for sample in self.samples)

    def _summary(self) -> dict[str, Any]:
        rss = [sample.combined_rss_mib for sample in self.samples]
        available = [sample.system_available_mib for sample in self.samples]
        cpu = [sample.process_cpu_normalized for sample in self.samples]
        temperatures = [
            sample.cpu_temperature_c
            for sample in self.samples
            if sample.cpu_temperature_c is not None
        ]
        window = min(600, max(1, len(rss) // 2))
        growth = (
            statistics.fmean(rss[-window:]) - statistics.fmean(rss[:window])
            if rss
            else 0.0
        )
        throttling = [sample.throttled for sample in self.samples if sample.throttled]
        criteria = {
            "combined_rss_below_4000_mib": bool(rss) and max(rss) < 4_000,
            "available_ram_at_least_2048_mib": bool(available)
            and min(available) >= 2_048,
            "memory_growth_below_50_mib": growth < 50 if len(rss) >= 1_200 else None,
            "process_cpu_average_below_50_percent": bool(cpu)
            and statistics.fmean(cpu) < 50,
            "process_cpu_p95_below_75_percent": bool(cpu) and _percentile(cpu, 95) < 75,
            "temperature_below_80_c": max(temperatures) < 80 if temperatures else None,
            "no_throttling": (
                all(value == "0x0" for value in throttling) if throttling else None
            ),
            "no_audio_stream_errors": not self.samples
            or (
                self.samples[-1].underruns == 0
                and self.samples[-1].overruns == 0
                and self.samples[-1].deadline_misses == 0
            ),
            "duration_at_least_1800_seconds": bool(self.samples)
            and self.samples[-1].elapsed_seconds >= 1_800,
        }
        return {
            "configuration": self.configuration,
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "power_measurement": "unavailable",
            "sample_count": len(self.samples),
            "duration_seconds": self.samples[-1].elapsed_seconds if self.samples else 0,
            "metrics": {
                "combined_rss_mib_average": _mean(rss),
                "combined_rss_mib_peak": max(rss, default=0),
                "memory_growth_mib": growth,
                "available_ram_mib_minimum": min(available, default=0),
                "process_cpu_average": _mean(cpu),
                "process_cpu_p95": _percentile(cpu, 95),
                "temperature_c_peak": max(temperatures, default=None),
                "limited_samples": self.samples[-1].limited_samples
                if self.samples
                else 0,
            },
            "acceptance": criteria,
            "passed": all(value is True for value in criteria.values()),
        }


def _safe_rss(process: psutil.Process) -> int:
    try:
        return process.memory_info().rss
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        return 0


def _read_number(path: str, divisor: float) -> float | None:
    try:
        return float(Path(path).read_text(encoding="ascii").strip()) / divisor
    except (OSError, ValueError):
        return None


def _read_throttled() -> str:
    executable = "/usr/bin/vcgencmd"
    if not Path(executable).is_file():
        return ""
    try:
        result = subprocess.run(  # nosec B603
            [executable, "get_throttled"],
            capture_output=True,
            check=False,
            timeout=2,
            text=True,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip().partition("=")[2]


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = round((percentile / 100) * (len(ordered) - 1))
    return ordered[index]
