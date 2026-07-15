#!/usr/bin/env python3
"""Measure warm Cortex query latency and peak memory usage.

Examples:
    uv run python benchmark_query.py "What is this project about?"
    uv run python benchmark_query.py --runs 5 --json "summarize my notes"

The models are loaded before measurement, so this reports steady-state query
cost rather than download or model-startup cost.  It exercises the same core
pipeline used by the shell: retrieval, prompt construction, and LLM response.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import threading
import time
from dataclasses import asdict, dataclass


def _rss_bytes() -> int | None:
    """Return this process's resident memory on Linux without extra packages."""
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024  # kB -> bytes
    except (FileNotFoundError, ValueError, IndexError):
        pass
    return None


def _gpu_memory_bytes() -> int | None:
    """Return GPU memory used by this process when nvidia-smi is available."""
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-compute-apps=pid,used_memory",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None

    used_mib = 0
    found = False
    for line in completed.stdout.splitlines():
        try:
            pid, memory = (value.strip() for value in line.split(",", maxsplit=1))
            if int(pid) == os.getpid():
                used_mib += int(memory)
                found = True
        except (ValueError, IndexError):
            continue
    return used_mib * 1024 * 1024 if found else 0


class MemorySampler:
    """Sample RSS (and CUDA process memory, if available) while a query runs."""

    def __init__(self, interval_seconds: float = 0.01) -> None:
        self.interval_seconds = interval_seconds
        self.peak_rss = _rss_bytes()
        self.peak_gpu = _gpu_memory_bytes()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self) -> None:
        gpu_next_sample = 0.0
        while not self._stop.wait(self.interval_seconds):
            rss = _rss_bytes()
            if rss is not None:
                self.peak_rss = max(self.peak_rss or 0, rss)

            # nvidia-smi is comparatively expensive, so sample it less often.
            if time.monotonic() >= gpu_next_sample:
                gpu = _gpu_memory_bytes()
                if gpu is not None:
                    self.peak_gpu = max(self.peak_gpu or 0, gpu)
                gpu_next_sample = time.monotonic() + 0.2

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> tuple[int | None, int | None]:
        self._stop.set()
        self._thread.join()
        return self.peak_rss, self.peak_gpu


@dataclass
class Run:
    retrieval_seconds: float
    generation_seconds: float
    total_seconds: float
    result_count: int
    response_characters: int
    peak_rss_bytes: int | None
    peak_gpu_bytes: int | None


def _format_bytes(value: int | None) -> str:
    if value is None:
        return "unavailable"
    return f"{value / (1024 * 1024):.1f} MiB"


def benchmark(query: str, runs: int, k: int) -> list[Run]:
    # Import after argument handling, since these modules configure model access.
    from cortex.reasoning.prompt import build_prompt
    from cortex.retrieval.search import search
    from cortex.shared.models import start_server, stop_server, warm_up_models

    print("Starting Chroma and warming models (not included in results)...")
    start_server()
    models = warm_up_models()
    llm = models.get("llm")
    if llm is None:
        stop_server()
        raise RuntimeError("LLM warm-up failed; see Cortex logs for the cause.")

    measurements: list[Run] = []
    try:
        for number in range(1, runs + 1):
            sampler = MemorySampler()
            sampler.start()

            started = time.perf_counter()
            retrieval_started = started
            results = search(query, k=k)
            retrieval_seconds = time.perf_counter() - retrieval_started

            prompt = build_prompt(query, results)
            generation_started = time.perf_counter()
            answer = llm.generate(prompt)
            generation_seconds = time.perf_counter() - generation_started
            total_seconds = time.perf_counter() - started
            peak_rss, peak_gpu = sampler.stop()

            run = Run(
                retrieval_seconds=retrieval_seconds,
                generation_seconds=generation_seconds,
                total_seconds=total_seconds,
                result_count=len(results),
                response_characters=len(answer),
                peak_rss_bytes=peak_rss,
                peak_gpu_bytes=peak_gpu,
            )
            measurements.append(run)
            print(
                f"Run {number}/{runs}: {run.total_seconds:.2f}s total "
                f"({run.retrieval_seconds:.2f}s retrieval, "
                f"{run.generation_seconds:.2f}s generation), "
                f"peak RSS {_format_bytes(run.peak_rss_bytes)}"
            )
    finally:
        stop_server()
    return measurements


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Query to send through Cortex's retrieval and LLM pipeline")
    parser.add_argument("--runs", type=int, default=3, help="Measured runs after warm-up (default: 3)")
    parser.add_argument("--k", type=int, default=5, help="Maximum retrieval results (default: 5)")
    parser.add_argument("--json", action="store_true", help="Print machine-readable measurements")
    args = parser.parse_args()
    if args.runs < 1 or args.k < 1:
        parser.error("--runs and --k must both be at least 1")

    measurements = benchmark(args.query, args.runs, args.k)
    if args.json:
        print(json.dumps([asdict(run) for run in measurements], indent=2))
        return

    print("\nSummary (warm queries)")
    for label, values in (
        ("Retrieval", [run.retrieval_seconds for run in measurements]),
        ("Generation", [run.generation_seconds for run in measurements]),
        ("End-to-end", [run.total_seconds for run in measurements]),
    ):
        print(f"{label}: mean {statistics.mean(values):.2f}s, median {statistics.median(values):.2f}s")

    peak_rss = max((run.peak_rss_bytes or 0) for run in measurements)
    gpu_values = [run.peak_gpu_bytes for run in measurements if run.peak_gpu_bytes is not None]
    print(f"Peak process RSS: {_format_bytes(peak_rss)}")
    if gpu_values:
        print(f"Peak GPU memory (this process): {_format_bytes(max(gpu_values))}")
    else:
        print("Peak GPU memory: unavailable (nvidia-smi not found or no CUDA process)")


if __name__ == "__main__":
    main()
