from omni_analyst.app import run


def test_smoke_run():
    result = run("Test sorusu")
    assert "final_report" in result
