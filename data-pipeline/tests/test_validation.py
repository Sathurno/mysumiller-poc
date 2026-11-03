import pandas as pd

from wine_pipeline.validation import clean_ratings, validate_ratings


def test_rating_cleaning_and_validation_reports_bad_values_and_foreign_keys():
    source = pd.DataFrame({
        "RatingID": ["1", "1", "3"], "UserID": ["10", "11", "12"],
        "WineID": ["7", "99", "7"], "Vintage": ["2020", "N.V.", "2018"],
        "Rating": ["4.5", "5.2", "2.5"],
        "Date": ["2020-01-02 10:00:00", "bad date", "2018-03-01 09:00:00"],
    })
    cleaned, metrics = clean_ratings(source)
    report = validate_ratings(cleaned, [7])
    assert metrics["invalid_dates"] == 1
    assert report["duplicate_rating_ids"] == 2
    assert report["invalid_rating_count"] == 1
    assert report["unmatched_wine_id_count"] == 1
    assert report["half_star_compatible_count"] == 2
    assert report["incompatible_half_star_count"] == 0


def test_validation_does_not_mutate_input():
    source = pd.DataFrame({"RatingID": [1], "UserID": [3], "WineID": [4], "Vintage": [2020],
                           "Rating": [4.0], "Date": ["2020-01-01 00:00:00"]})
    original = source.copy(deep=True)
    clean_ratings(source)
    pd.testing.assert_frame_equal(source, original)