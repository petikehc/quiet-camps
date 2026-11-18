import pytest

import quiet_camps


def test_main(capsys: pytest.CaptureFixture[str]) -> None:
    quiet_camps.main()

    captured = capsys.readouterr()
    assert captured.out == "Hello from quiet-camps!\n"
