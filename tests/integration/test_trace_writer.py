from scheduler_sim.trace.writer import TraceWriter


def test_trace_writer_emits_required_files(tmp_path):
    writer = TraceWriter(output_dir=tmp_path)

    writer.write_experiment_meta({"experiment_id": "exp_001"})
    writer.write_trace_summary({"critical_task_metrics": {}, "agent_task_metrics": {}})

    assert (tmp_path / "experiment_meta.json").exists()
    assert (tmp_path / "trace_summary.json").exists()
