from scheduler_sim.profiling.synthetic_data import build_profiling_rows


def _rows_for_tool(rows, tool_name):
    return [row for row in rows if row["tool_name"] == tool_name]


def _latency(rows, *, cpu_core, cpu_memory_mb, gpu_memory_mb, input_size):
    for row in rows:
        if (
            row["cpu_core"] == cpu_core
            and row["cpu_memory_mb"] == cpu_memory_mb
            and row["gpu_memory_mb"] == gpu_memory_mb
            and row["input_size"] == input_size
        ):
            return row["latency"]
    raise AssertionError("matching profiling row not found")


def test_synthetic_profiling_rows_follow_anchor_ranges_and_ordering():
    rows = build_profiling_rows()

    text_to_speech_rows = _rows_for_tool(rows, "text_to_speech")
    assert _latency(
        text_to_speech_rows,
        cpu_core=0.4,
        cpu_memory_mb=192,
        gpu_memory_mb=256,
        input_size="large",
    ) > 1_000_000
    assert _latency(
        text_to_speech_rows,
        cpu_core=1.2,
        cpu_memory_mb=384,
        gpu_memory_mb=1024,
        input_size="large",
    ) < 500_000

    text_translation_rows = _rows_for_tool(rows, "text_translation")
    assert _latency(
        text_translation_rows,
        cpu_core=0.25,
        cpu_memory_mb=128,
        gpu_memory_mb=0,
        input_size="large",
    ) > 300_000
    assert _latency(
        text_translation_rows,
        cpu_core=1.0,
        cpu_memory_mb=384,
        gpu_memory_mb=0,
        input_size="large",
    ) < 150_000

    object_detection_rows = _rows_for_tool(rows, "object_detection")
    object_low = _latency(
        object_detection_rows,
        cpu_core=0.5,
        cpu_memory_mb=256,
        gpu_memory_mb=256,
        input_size="large",
    )
    object_high = _latency(
        object_detection_rows,
        cpu_core=1.5,
        cpu_memory_mb=512,
        gpu_memory_mb=1536,
        input_size="large",
    )
    assert object_low > 800_000
    assert object_high < 350_000

    image_captioning_rows = _rows_for_tool(rows, "image_captioning")
    image_low = _latency(
        image_captioning_rows,
        cpu_core=0.5,
        cpu_memory_mb=256,
        gpu_memory_mb=256,
        input_size="large",
    )
    image_high = _latency(
        image_captioning_rows,
        cpu_core=1.5,
        cpu_memory_mb=512,
        gpu_memory_mb=1536,
        input_size="large",
    )
    assert image_low > 1_100_000
    assert image_high < 650_000
    assert image_low - object_low > 200_000
    assert image_high - object_high > 200_000

    localization_rows = _rows_for_tool(rows, "localization_node")
    pointcloud_rows = _rows_for_tool(rows, "pointcloud_to_laserscan_node")
    navigation_rows = _rows_for_tool(rows, "navigation_algo_node")
    localization_latency = _latency(
        localization_rows,
        cpu_core=0.24,
        cpu_memory_mb=128,
        gpu_memory_mb=0,
        input_size="large",
    )
    pointcloud_latency = _latency(
        pointcloud_rows,
        cpu_core=0.55,
        cpu_memory_mb=192,
        gpu_memory_mb=0,
        input_size="large",
    )
    navigation_latency = _latency(
        navigation_rows,
        cpu_core=1.0,
        cpu_memory_mb=256,
        gpu_memory_mb=0,
        input_size="large",
    )
    assert localization_latency < pointcloud_latency < navigation_latency
