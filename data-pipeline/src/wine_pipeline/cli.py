import argparse
import logging

import pandas as pd

from .analysis import (
    bivariate_analysis,
    build_wine_rating_features,
    catalog_analysis,
    multivariate_analysis,
    outlier_examples,
    plot_abv_rating_scatter,
    plot_correlation_heatmap,
    plot_feature_pairplot,
    plot_outlier_diagnostics,
    plot_rating_by_category,
    rating_analysis,
)
from .cleaning import clean_wines
from .config import FIGURES_DIR, INTERIM_DIR, PROCESSED_DIR, QUALITY_DIR, RATINGS_FILE, SUMMARY_DIR, WINES_FILE
from .deduplication import find_duplicate_candidates
from .export import write_frame, write_json
from .features import add_catalog_features
from .io import load_or_create_ratings_sample, read_wines
from .profiling import profile_frame
from .validation import clean_ratings, validate_ratings, validate_schema

LOGGER = logging.getLogger("wine_pipeline")


def run_pipeline(command: str, rating_limit: int = 100_000, show: bool = False) -> None:
    for directory in (INTERIM_DIR, PROCESSED_DIR, QUALITY_DIR, FIGURES_DIR, SUMMARY_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    if not WINES_FILE.exists() or not RATINGS_FILE.exists():
        raise FileNotFoundError("Expected both X-Wines source CSVs under data/raw/")

    wines = read_wines(WINES_FILE)
    sample_ratings, sampling_metrics = load_or_create_ratings_sample(
        RATINGS_FILE,
        INTERIM_DIR / "xwines_ratings_sample_raw.csv",
        QUALITY_DIR / "ratings_sample_manifest.json",
        sample_size=rating_limit,
    )
    sample_scope = {
        "dataset": "X-Wines ratings",
        "scope": "reproducible_uniform_sample",
        "rows_loaded": int(len(sample_ratings)),
        "requested_rows": rating_limit,
        **sampling_metrics,
    }

    if command in {"profile", "all"}:
        write_json(profile_frame(wines, ["WineID"]) | {"scope": "full_catalog"}, QUALITY_DIR / "wines_profile.json")
        write_json(profile_frame(sample_ratings, ["RatingID"]) | {"scope": sample_scope}, QUALITY_DIR / "ratings_sample_profile.json")

    if command in {"clean", "all"}:
        cleaned_wines, parse_errors = clean_wines(wines)
        featured_wines = add_catalog_features(cleaned_wines)
        write_frame(featured_wines, PROCESSED_DIR / "xwines_catalog.parquet")
        write_frame(parse_errors, QUALITY_DIR / "wine_parse_errors.csv")
        cleaned_ratings, date_metrics = clean_ratings(sample_ratings)
        write_frame(cleaned_ratings, INTERIM_DIR / "xwines_ratings_sample.parquet")
        write_json({"rules": ["trim/collapse whitespace", "parse list fields safely", "preserve IDs and source columns"],
                    "wine_parse_error_count": int(len(parse_errors)), "rating_date_metrics": date_metrics,
                    "rating_scope": sample_scope}, QUALITY_DIR / "cleaning_metrics.json")

    cleaned_wines, wine_errors = clean_wines(wines)
    cleaned_ratings, date_metrics = clean_ratings(sample_ratings)
    if command in {"validate", "all"}:
        report = {
            "wines_schema": validate_schema(wines, "wines"),
            "ratings_schema": validate_schema(sample_ratings, "ratings"),
            "ratings": validate_ratings(cleaned_ratings, cleaned_wines["WineID"].dropna().unique()),
            "invalid_date_count": date_metrics["invalid_dates"],
            "catalog_scope": "full_catalog",
            "ratings_scope": sample_scope,
        }
        write_json(report, QUALITY_DIR / "validation_report.json")

    if command in {"analyze", "all"}:
        rating_metrics = rating_analysis(cleaned_ratings)
        catalog_metrics = catalog_analysis(cleaned_wines)
        featured_wines = add_catalog_features(cleaned_wines)
        wine_rating_features = build_wine_rating_features(cleaned_ratings, featured_wines)
        bivariate_metrics = bivariate_analysis(cleaned_ratings, featured_wines, wine_rating_features)
        multivariate_metrics = multivariate_analysis(wine_rating_features)
        category_metrics = {
            "Type": bivariate_metrics["rating_by_type"],
            "Country": bivariate_metrics["rating_by_country"],
        }
        write_json({"catalog": catalog_metrics, "ratings_sample": rating_metrics,
                    "ratings_by_category": category_metrics,
                    "bivariate": bivariate_metrics,
                    "multivariate": multivariate_metrics,
                    "ratings_scope": sample_scope}, SUMMARY_DIR / "eda_metrics.json")
        candidates = find_duplicate_candidates(cleaned_wines)
        write_frame(candidates, QUALITY_DIR / "wine_duplicate_candidates.csv")
        abv_context = ("WineID", "WineName", "Country", "RegionName", "Type", "WineryName")
        write_frame(outlier_examples(cleaned_wines, "ABV", abv_context), QUALITY_DIR / "abv_outlier_examples.csv")
        abv_figure = plot_outlier_diagnostics(cleaned_wines, "ABV", FIGURES_DIR / "abv_outliers.png", show=show)
        rating_figure = plot_outlier_diagnostics(cleaned_ratings, "Rating", FIGURES_DIR / "ratings_outliers.png", show=show)
        counts = cleaned_ratings.groupby("WineID").size().rename("rating_count").reset_index()
        wine_count_figure = plot_outlier_diagnostics(counts, "rating_count", FIGURES_DIR / "sample_ratings_per_wine.png", show=show)
        user_counts = cleaned_ratings.groupby("UserID").size().rename("rating_count").reset_index()
        user_count_figure = plot_outlier_diagnostics(user_counts, "rating_count", FIGURES_DIR / "sample_ratings_per_user.png", show=show)
        type_summary = pd.DataFrame(bivariate_metrics["rating_by_type"])
        country_summary = pd.DataFrame(bivariate_metrics["rating_by_country"])
        type_figure = plot_rating_by_category(type_summary, "Type", FIGURES_DIR / "rating_by_type.png", "Rating por tipo de vino")
        country_figure = plot_rating_by_category(country_summary, "Country", FIGURES_DIR / "rating_by_country.png", "Rating por país (principales grupos)")
        abv_rating_figure = plot_abv_rating_scatter(wine_rating_features, FIGURES_DIR / "abv_vs_mean_rating.png")
        correlation = pd.DataFrame(multivariate_metrics["spearman_correlation"], dtype=float).T
        correlation_figure = plot_correlation_heatmap(correlation, FIGURES_DIR / "wine_feature_correlation.png")
        pairplot_figure = plot_feature_pairplot(wine_rating_features, FIGURES_DIR / "wine_feature_pairplot.png")
        write_json({"abv": str(abv_figure), "ratings": str(rating_figure),
                "ratings_per_wine": str(wine_count_figure),
            "ratings_per_user": str(user_count_figure),
            "rating_by_type": str(type_figure), "rating_by_country": str(country_figure),
            "abv_vs_mean_rating": str(abv_rating_figure),
            "wine_feature_correlation": str(correlation_figure),
            "wine_feature_pairplot": str(pairplot_figure)}, SUMMARY_DIR / "figure_manifest.json")
        LOGGER.info("Saved EDA results for the full catalog and %s rows from a reproducible rating sample", len(cleaned_ratings))


def main() -> None:
    parser = argparse.ArgumentParser(description="Local X-Wines data quality and EDA pipeline")
    parser.add_argument("command", choices=["profile", "clean", "validate", "analyze", "all"])
    parser.add_argument("--rating-limit", type=int, default=100_000)
    parser.add_argument("--show", action="store_true", help="Display diagnostic plots interactively")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run_pipeline(args.command, args.rating_limit, args.show)


if __name__ == "__main__":
    main()