import pandas as pd

from wine_pipeline.analysis import (
    bivariate_analysis,
    build_wine_rating_features,
    iqr_outlier_summary,
    multivariate_analysis,
)
from wine_pipeline.deduplication import find_duplicate_candidates
from wine_pipeline.export import write_frame
from wine_pipeline.features import add_catalog_features


def test_features_preserve_source_fields_and_add_counts():
    source = pd.DataFrame({"WineID": [1], "Grapes": [["A", "B"]], "Vintages": [[2020, "N.V."]]})
    result = add_catalog_features(source)
    assert result.loc[0, "WineID"] == 1
    assert result.loc[0, "GrapeCount"] == 2
    assert result.loc[0, "VintageCount"] == 1
    assert result.loc[0, "HasNonVintage"]
    assert result.loc[0, "Vintages"] == ["2020", "N.V."]
    assert "GrapeCount" not in source


def test_catalog_with_special_vintages_roundtrips_as_parquet(tmp_path):
    source = pd.DataFrame({"WineID": [1], "Vintages": [[2020, "N.V."]]})
    path = write_frame(add_catalog_features(source), tmp_path / "catalog.parquet")
    result = pd.read_parquet(path)
    assert list(result.loc[0, "Vintages"]) == ["2020", "N.V."]


def test_duplicate_candidates_require_multiple_matching_attributes():
    wines = pd.DataFrame({
        "WineID": [1, 2, 3], "WineName": ["Cabernet Reserve", "Cabernet Reserv", "Cabernet Reserve"],
        "Country": ["Chile", "Chile", "France"], "Type": ["Red", "Red", "Red"],
        "RegionName": ["Maipo", "Maipo", "Bordeaux"], "WineryName": ["A", "A", "B"],
    })
    candidates = find_duplicate_candidates(wines)
    assert len(candidates) == 1
    assert set(candidates.loc[0, ["WineID_A", "WineID_B"]]) == {1, 2}


def test_iqr_flags_extremes_without_modifying_values():
    values = pd.Series([10, 11, 12, 12, 13, 100])
    report = iqr_outlier_summary(values)
    assert report["outlier_count"] == 1
    assert values.iloc[-1] == 100


def test_bivariate_and_multivariate_analysis_uses_wine_level_features_not_ids():
    ratings = pd.DataFrame({
        "WineID": [1, 1, 1, 1, 1, 2, 2],
        "Rating": [4.0, 4.5, 4.0, 5.0, 4.5, 3.5, 3.0],
    })
    wines = pd.DataFrame({
        "WineID": [1, 2], "ABV": [12.0, 14.0], "Type": ["Red", "White"],
        "Country": ["Chile", "France"], "GrapeCount": [1, 2], "VintageCount": [2, 3],
    })
    wine_features = build_wine_rating_features(ratings, wines, minimum_ratings=2)
    bivariate = bivariate_analysis(ratings, wines, wine_features, minimum_category_ratings=1)
    multivariate = multivariate_analysis(wine_features)

    assert len(wine_features) == 2
    assert bivariate["abv_vs_mean_rating"]["spearman_rho"] == -1.0
    assert len(bivariate["rating_by_type"]) == 2
    assert "WineID" not in multivariate["features"]
    assert multivariate["spearman_correlation"]["ABV"]["MeanRating"] == -1.0