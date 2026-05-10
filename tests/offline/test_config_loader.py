from offline.config_loader import load_offline_analyzer_config


def test_load_offline_analyzer_config_reads_required_fields(tmp_path):
    config_path = tmp_path / "configs" / "offline" / "trace_analyzer_openai.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        "\n".join(
            [
                "metadata:",
                "  name: trace_analyzer_openai",
                "",
                "provider:",
                "  api: openai",
                "  base_url: https://api.openai.com/v1",
                "  api_key_env: OPENAI_API_KEY",
                "",
                "model:",
                "  name: gpt-5.4",
                "  reasoning_effort: medium",
                "",
                "runtime:",
                "  timeout_s: 60",
                "  max_windows: 5",
                "",
            ]
        ),
        encoding="utf-8",
    )

    config = load_offline_analyzer_config(config_path)

    assert config.metadata_name == "trace_analyzer_openai"
    assert config.provider_api == "openai"
    assert config.base_url == "https://api.openai.com/v1"
    assert config.api_key_env == "OPENAI_API_KEY"
    assert config.model_name == "gpt-5.4"
    assert config.reasoning_effort == "medium"
    assert config.timeout_s == 60
    assert config.max_windows == 5
