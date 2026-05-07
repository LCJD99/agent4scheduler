import csv

import pytest

from scheduler_sim.domain.resources import ResourceVector
from scheduler_sim.profiling.estimator import ProfilingEstimator


def write_profiling_csv(path):
    rows = [
        ["image_captioning", 0.5, 256, 0, 0, "small", 6200, "success"],
        ["image_captioning", 1.0, 256, 0, 0, "small", 4100, "success"],
        ["image_captioning", 2.0, 256, 0, 0, "small", 2600, "success"],
        ["image_captioning", 0.5, 512, 0, 0, "medium", 7000, "success"],
        ["image_captioning", 1.0, 512, 0, 0, "medium", 4700, "success"],
        ["image_captioning", 2.0, 512, 0, 0, "medium", 3100, "success"],
        ["image_captioning", 0.5, 512, 0, 0, "large", 8300, "success"],
        ["image_captioning", 1.0, 512, 0, 0, "large", 5800, "success"],
        ["text_translation", 0.5, 128, 0, 0, "medium", 2200, "success"],
        ["text_translation", 1.0, 128, 0, 0, "medium", 1500, "success"],
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "tool_name",
                "cpu_core",
                "cpu_memory_mb",
                "gpu_memory_mb",
                "network_bandwidth_mbps",
                "input_size",
                "latency",
                "status",
            ]
        )
        writer.writerows(rows)


def test_estimator_predicts_positive_latency_for_known_tool(tmp_path):
    csv_path = tmp_path / "profiling.csv"
    write_profiling_csv(csv_path)
    estimator = ProfilingEstimator.from_csv(csv_path)

    light_latency = estimator.estimate_latency_us(
        tool_name="image_captioning",
        allocated_resources=ResourceVector(cpu_cores=0.5, memory_mb=512),
        scene_complexity="medium",
    )
    heavier_latency = estimator.estimate_latency_us(
        tool_name="image_captioning",
        allocated_resources=ResourceVector(cpu_cores=2.0, memory_mb=512),
        scene_complexity="medium",
    )

    assert light_latency > 0
    assert heavier_latency > 0
    assert light_latency > heavier_latency


def test_estimator_raises_for_unknown_tool(tmp_path):
    csv_path = tmp_path / "profiling.csv"
    write_profiling_csv(csv_path)
    estimator = ProfilingEstimator.from_csv(csv_path)

    with pytest.raises(KeyError):
        estimator.estimate_latency_us(
            tool_name="missing_tool",
            allocated_resources=ResourceVector(cpu_cores=1.0, memory_mb=128),
            scene_complexity="medium",
        )
