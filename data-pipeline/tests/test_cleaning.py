import pandas as pd

from wine_pipeline.cleaning import clean_wines, normalize_text, parse_list_value, parse_vintage_list


def test_normalizes_spaces_and_known_null_tokens_but_preserves_none_text():
    assert normalize_text("  Serra   Gaúcha ") == "Serra Gaúcha"
    assert pd.isna(normalize_text(" N/A "))
    assert normalize_text("None") == "None"


def test_parses_lists_without_evaluating_arbitrary_expressions():
    assert parse_list_value("['Muscat/Moscato']") == (["Muscat/Moscato"], None)
    parsed, error = parse_list_value("__import__('os').system('echo unsafe')")
    assert parsed is None
    assert error.startswith("invalid list literal")


def test_clean_wines_preserves_input_and_reports_parse_errors():
    source = pd.DataFrame({
        "WineID": ["100001"], "WineName": [" Casa   Perini "], "ABV": ["7.5"],
        "Grapes": ["['Muscat']"], "Harmonize": ["bad list"], "Vintages": ["[2020, 'N.V.']"],
    })
    original = source.copy(deep=True)
    cleaned, errors = clean_wines(source)
    pd.testing.assert_frame_equal(source, original)
    assert str(cleaned.loc[0, "WineID"]) == "100001"
    assert cleaned.loc[0, "WineName"] == "Casa Perini"
    assert cleaned.loc[0, "Grapes"] == ["Muscat"]
    assert pd.isna(cleaned.loc[0, "Harmonize"])
    assert errors.loc[0, "column"] == "Harmonize"


def test_parses_vintages_and_keeps_non_vintage_marker():
    assert parse_vintage_list([2020, "2019", "N.V.", "not-a-year"]) == [2020, 2019, "N.V."]