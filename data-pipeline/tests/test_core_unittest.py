import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from wine_pipeline.analysis import iqr_outlier_summary
from wine_pipeline.analysis import ratings_by_wine_category
from wine_pipeline.cleaning import clean_wines, parse_list_value
from wine_pipeline.deduplication import find_duplicate_candidates
from wine_pipeline.features import add_catalog_features
from wine_pipeline.io import load_or_create_ratings_sample, sample_ratings
from wine_pipeline.validation import clean_ratings, validate_ratings


class PipelineCoreTests(unittest.TestCase):
    def test_safe_list_parse_and_wine_cleaning(self):
        self.assertEqual(parse_list_value("[1, 2]")[0], [1, 2])
        source = pd.DataFrame({
            "WineID": ["1"], "WineName": [" Wine   X "], "Grapes": ["[1]"],
            "Vintages": ["[2020, 2019]"], "ABV": ["12.5"],
        })
        cleaned, errors = clean_wines(source)
        self.assertEqual(cleaned.loc[0, "WineName"], "Wine X")
        self.assertEqual(len(errors), 0)
        self.assertEqual(add_catalog_features(cleaned).loc[0, "VintageCount"], 2)

    def test_rating_cleaning_and_referential_validation(self):
        ratings = pd.DataFrame({
            "RatingID": [1, 1], "UserID": [2, 3], "WineID": [1, 9],
            "Vintage": [2020, 2020], "Rating": [4.5, 5.2],
            "Date": ["2020-01-01 00:00:00", "bad"],
        })
        cleaned, metrics = clean_ratings(ratings)
        report = validate_ratings(cleaned, [1])
        self.assertEqual(metrics["invalid_dates"], 1)
        self.assertEqual(report["invalid_rating_count"], 1)
        self.assertEqual(report["unmatched_wine_id_count"], 1)

    def test_outlier_detection_and_duplicate_candidates(self):
        self.assertEqual(iqr_outlier_summary(pd.Series([10, 11, 12, 12, 13, 100]))["outlier_count"], 1)
        wines = pd.DataFrame({
            "WineID": [1, 2], "WineName": ["Cabernet Reserve", "Cabernet Reserv"],
            "Country": ["Chile", "Chile"], "Type": ["Red", "Red"],
            "RegionName": ["Maipo", "Maipo"], "WineryName": ["A", "A"],
        })
        self.assertEqual(len(find_duplicate_candidates(wines)), 1)

    def test_category_aggregation_guards_join_cardinality(self):
        ratings = pd.DataFrame({"WineID": [1, 1, 2], "Rating": [4.0, 5.0, 3.0]})
        wines = pd.DataFrame({"WineID": [1, 2], "Type": ["Red", "White"]})
        summary = ratings_by_wine_category(ratings, wines, "Type", minimum_ratings=1)
        self.assertEqual(summary.loc[0, "rating_count"], 2)
        with self.assertRaises(ValueError):
            ratings_by_wine_category(ratings, pd.concat([wines, wines.iloc[[0]]]), "Type", 1)

    def test_presentation_notebook_code_cells_are_valid_python(self):
        notebook_path = Path(__file__).parents[1] / "memoria.ipynb"
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                compile("".join(cell["source"]), str(notebook_path), "exec")

    def test_seeded_chunk_sample_is_reproducible_and_cached(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "ratings.csv"
            pd.DataFrame({
                "RatingID": range(1, 1001), "UserID": range(1001, 2001),
                "WineID": range(1, 1001), "Vintage": [2020] * 1000,
                "Rating": [4.0] * 1000, "Date": ["2020-01-01 00:00:00"] * 1000,
            }).to_csv(source, index=False)
            first, metadata = sample_ratings(source, sample_size=40, seed=13, chunksize=100)
            again, _ = sample_ratings(source, sample_size=40, seed=13, chunksize=100)
            pd.testing.assert_frame_equal(first, again)
            self.assertEqual(metadata["source_rows_scanned"], 1000)
            self.assertTrue(metadata["is_random_sample"])

            sample_file = root / "sample.csv"
            manifest_file = root / "manifest.json"
            cached, _ = load_or_create_ratings_sample(source, sample_file, manifest_file, 40, 13)
            pd.testing.assert_frame_equal(first, cached)


if __name__ == "__main__":
    unittest.main()