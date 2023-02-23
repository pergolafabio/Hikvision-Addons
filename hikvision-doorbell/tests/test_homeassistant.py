
from home_assistant import sanitize_doorbell_name


def test_sanitize_name():
    # Check that we substitute - and whitespace with _
    sanitized = sanitize_doorbell_name("ds-kd800 3")
    assert "-" not in sanitized
    assert " " not in sanitized
    assert "_" in sanitized
