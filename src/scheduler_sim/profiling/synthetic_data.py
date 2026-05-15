import csv
import hashlib
import random
from pathlib import Path


ROW_ORDER = [
    ("localization_node", 0.12, 96, 0, 0.0),
    ("localization_node", 0.24, 128, 0, 0.0),
    ("localization_node", 0.45, 160, 0, 0.0),
    ("pointcloud_to_laserscan_node", 0.3, 128, 0, 0.0),
    ("pointcloud_to_laserscan_node", 0.55, 192, 0, 0.0),
    ("pointcloud_to_laserscan_node", 0.9, 256, 0, 0.0),
    ("navigation_algo_node", 0.6, 160, 0, 0.0),
    ("navigation_algo_node", 1.0, 256, 0, 0.0),
    ("navigation_algo_node", 1.5, 320, 0, 0.0),
    ("text_translation", 0.25, 128, 0, 0.0),
    ("text_translation", 0.5, 256, 0, 0.0),
    ("text_translation", 1.0, 384, 0, 0.0),
    ("text_to_speech", 0.4, 192, 256, 0.0),
    ("text_to_speech", 0.75, 256, 512, 0.0),
    ("text_to_speech", 1.2, 384, 1024, 0.0),
    ("object_detection", 0.5, 256, 256, 0.0),
    ("object_detection", 1.0, 384, 768, 0.0),
    ("object_detection", 1.5, 512, 1536, 0.0),
    ("image_captioning", 0.5, 256, 256, 0.0),
    ("image_captioning", 1.0, 384, 768, 0.0),
    ("image_captioning", 1.5, 512, 1536, 0.0),
]

SCENE_FACTORS = {
    "small": 0.86,
    "medium": 1.0,
    "large": 1.18,
}

LATENCY_MODELS = {
    "localization_node": {
        "base_s": 0.0065,
        "cpu_power": 0.58,
        "memory_power": 0.08,
        "gpu_power": 0.0,
        "noise": 0.05,
    },
    "pointcloud_to_laserscan_node": {
        "base_s": 0.0105,
        "cpu_power": 0.62,
        "memory_power": 0.12,
        "gpu_power": 0.0,
        "noise": 0.06,
    },
    "navigation_algo_node": {
        "base_s": 0.0117,
        "cpu_power": 0.72,
        "memory_power": 0.14,
        "gpu_power": 0.0,
        "noise": 0.07,
    },
    "text_translation": {
        "base_s": 0.085,
        "cpu_power": 0.82,
        "memory_power": 0.28,
        "gpu_power": 0.0,
        "noise": 0.07,
    },
    "text_to_speech": {
        "base_s": 0.34,
        "cpu_power": 0.68,
        "memory_power": 0.10,
        "gpu_power": 0.34,
        "noise": 0.08,
    },
    "object_detection": {
        "base_s": 0.237,
        "cpu_power": 0.18,
        "memory_power": 0.08,
        "gpu_power": 0.62,
        "noise": 0.07,
    },
    "image_captioning": {
        "base_s": 0.49,
        "cpu_power": 0.18,
        "memory_power": 0.08,
        "gpu_power": 0.62,
        "noise": 0.07,
    },
}


def build_profiling_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for tool_name, cpu_core, cpu_memory_mb, gpu_memory_mb, network_mbps in ROW_ORDER:
        for input_size in ("small", "medium", "large"):
            latency_us = _latency_us(
                tool_name=tool_name,
                cpu_core=cpu_core,
                cpu_memory_mb=cpu_memory_mb,
                gpu_memory_mb=gpu_memory_mb,
                input_size=input_size,
            )
            rows.append(
                {
                    "tool_name": tool_name,
                    "cpu_core": cpu_core,
                    "cpu_memory_mb": cpu_memory_mb,
                    "gpu_memory_mb": gpu_memory_mb,
                    "network_bandwidth_mbps": network_mbps,
                    "input_size": input_size,
                    "latency": latency_us,
                    "status": "success",
                }
            )
    return rows


def write_profiling_csv(path: str | Path) -> Path:
    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "tool_name",
                "cpu_core",
                "cpu_memory_mb",
                "gpu_memory_mb",
                "network_bandwidth_mbps",
                "input_size",
                "latency",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(build_profiling_rows())
    return csv_path


def _latency_us(
    *,
    tool_name: str,
    cpu_core: float,
    cpu_memory_mb: int,
    gpu_memory_mb: int,
    input_size: str,
) -> int:
    model = LATENCY_MODELS[tool_name]
    cpu_ref = _max_value(tool_name, 1)
    memory_ref = _max_value(tool_name, 2)
    gpu_ref = max(1, _max_value(tool_name, 3))
    scene_factor = SCENE_FACTORS[input_size]
    cpu_term = (cpu_ref / cpu_core) ** model["cpu_power"]
    memory_term = (memory_ref / cpu_memory_mb) ** model["memory_power"]
    if model["gpu_power"] > 0:
        gpu_term = (gpu_ref / max(1, gpu_memory_mb)) ** model["gpu_power"]
    else:
        gpu_term = 1.0
    jitter = 1.0 + _rng(tool_name, cpu_core, cpu_memory_mb, gpu_memory_mb, input_size).uniform(
        -model["noise"],
        model["noise"],
    )
    latency_s = model["base_s"] * scene_factor * cpu_term * memory_term * gpu_term * jitter
    return int(round(latency_s * 1_000_000))


def _max_value(tool_name: str, index: int) -> float:
    return max(
        float(row[index])
        for row in ROW_ORDER
        if row[0] == tool_name
    )


def _rng(
    tool_name: str,
    cpu_core: float,
    cpu_memory_mb: int,
    gpu_memory_mb: int,
    input_size: str,
) -> random.Random:
    key = f"{tool_name}|{cpu_core}|{cpu_memory_mb}|{gpu_memory_mb}|{input_size}"
    seed = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:16], 16)
    return random.Random(seed)
