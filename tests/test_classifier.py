from execution.classifier import (
    IMPORTANT_CATEGORY,
    LOW_VALUE_CATEGORY,
    extract_low_value_signals,
    normalize_category,
)


def test_normalize_category_marks_low_value_variants() -> None:
    assert normalize_category("Category: LowValue") == LOW_VALUE_CATEGORY
    assert normalize_category("Category: marketing clutter") == LOW_VALUE_CATEGORY
    assert normalize_category("This looks promotional") == LOW_VALUE_CATEGORY


def test_normalize_category_defaults_to_important() -> None:
    assert normalize_category("Category: Important") == IMPORTANT_CATEGORY
    assert normalize_category("") == IMPORTANT_CATEGORY


def test_extract_low_value_signals_detects_common_clutter_markers() -> None:
    signals = extract_low_value_signals(
        "Deals Team <sales@example.com>",
        "View in browser: upgrade now",
        "unsubscribe and manage preferences",
    )
    assert "unsubscribe" in signals
    assert "manage preferences" in signals
    assert "view in browser" in signals
