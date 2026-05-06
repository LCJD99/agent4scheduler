from scheduler_sim.app import main


def test_main_returns_zero_for_help_mode():
    assert main(["--help"]) == 0
