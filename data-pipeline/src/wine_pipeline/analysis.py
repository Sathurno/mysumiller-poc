from pathlib import Path
from html import escape

import numpy as np
import pandas as pd


def iqr_outlier_summary(series: pd.Series) -> dict[str, float | int | None]:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return {"count": 0, "q1": None, "median": None, "q3": None, "iqr": None,
                "lower_fence": None, "upper_fence": None, "outlier_count": 0}
    q1 = float(values.quantile(0.25))
    median = float(values.median())
    q3 = float(values.quantile(0.75))
    spread = q3 - q1
    lower = q1 - 1.5 * spread
    upper = q3 + 1.5 * spread
    return {
        "count": int(values.size), "q1": q1, "median": median, "q3": q3,
        "iqr": spread, "lower_fence": lower, "upper_fence": upper,
        "outlier_count": int((values.lt(lower) | values.gt(upper)).sum()),
    }


def rating_analysis(ratings: pd.DataFrame) -> dict[str, object]:
    values = pd.to_numeric(ratings["Rating"], errors="coerce").dropna()
    counts_by_wine = ratings.groupby("WineID", dropna=True).size().rename("rating_count")
    counts_by_user = ratings.groupby("UserID", dropna=True).size().rename("rating_count")
    wine_means = ratings.groupby("WineID", dropna=True)["Rating"].agg(["mean", "count"])
    user_means = ratings.groupby("UserID", dropna=True)["Rating"].agg(["mean", "count"])
    return {
        "rating_count": int(values.size),
        "rating_describe": {key: float(value) for key, value in values.describe().items()},
        "rating_mode": [float(value) for value in values.mode().tolist()],
        "rating_skew": float(values.skew()) if len(values) > 2 else None,
        "rating_distribution": {str(key): int(value) for key, value in values.value_counts().sort_index().items()},
        "ratings_per_wine": {
            "wine_count": int(counts_by_wine.size),
            "median": float(counts_by_wine.median()) if len(counts_by_wine) else None,
            "p95": float(counts_by_wine.quantile(0.95)) if len(counts_by_wine) else None,
            "maximum": int(counts_by_wine.max()) if len(counts_by_wine) else None,
            "iqr": iqr_outlier_summary(counts_by_wine),
        },
        "ratings_per_user": {
            "user_count": int(counts_by_user.size),
            "median": float(counts_by_user.median()) if len(counts_by_user) else None,
            "p95": float(counts_by_user.quantile(0.95)) if len(counts_by_user) else None,
            "maximum": int(counts_by_user.max()) if len(counts_by_user) else None,
            "iqr": iqr_outlier_summary(counts_by_user),
        },
        "wine_mean_rating_sample_size": {
            "single_rating_wines": int((wine_means["count"] == 1).sum()),
            "median_ratings_per_wine": float(wine_means["count"].median()) if len(wine_means) else None,
        },
        "user_mean_rating_sample_size": {
            "single_rating_users": int((user_means["count"] == 1).sum()),
            "median_ratings_per_user": float(user_means["count"].median()) if len(user_means) else None,
        },
        "rating_iqr": iqr_outlier_summary(values),
    }


def catalog_analysis(wines: pd.DataFrame) -> dict[str, object]:
    fields = ["ABV", "Body", "Acidity", "Country", "RegionName", "WineryName", "Grapes", "Vintages", "Website"]
    completeness = {
        column: {
            "missing_count": int(wines[column].isna().sum()),
            "missing_percent": float(wines[column].isna().mean() * 100),
        }
        for column in fields if column in wines
    }
    categories = {}
    for column in ("Type", "Country", "Body", "Acidity"):
        if column in wines:
            categories[column] = {
                str(key): int(value)
                for key, value in wines[column].value_counts(dropna=False).head(20).items()
            }
    numeric = {}
    for column in ("ABV",):
        if column in wines:
            numeric[column] = iqr_outlier_summary(wines[column])
    missingness_by_category = {}
    for field in ("Website", "ABV", "Grapes", "Vintages"):
        if field not in wines:
            continue
        missing = wines[field].isna()
        grouped = []
        for dimension in ("Type", "Country"):
            if dimension in wines:
                summary = wines.assign(_missing=missing).groupby(dimension, dropna=False)["_missing"].agg(
                    records="size", missing_count="sum", missing_percent="mean"
                )
                grouped.append({
                    "dimension": dimension,
                    "groups": [
                        {"category": str(key), "records": int(row.records),
                         "missing_count": int(row.missing_count),
                         "missing_percent": float(row.missing_percent * 100)}
                        for key, row in summary.sort_values("missing_count", ascending=False).head(15).iterrows()
                    ],
                })
        missingness_by_category[field] = grouped
    return {
        "completeness": completeness,
        "top_categories": categories,
        "numeric_iqr": numeric,
        "missingness_by_category": missingness_by_category,
    }


def outlier_examples(
    frame: pd.DataFrame,
    column: str,
    context_columns: tuple[str, ...] = (),
    limit: int = 50,
) -> pd.DataFrame:
    summary = iqr_outlier_summary(frame[column])
    if summary["lower_fence"] is None:
        return frame.iloc[0:0].copy()
    values = pd.to_numeric(frame[column], errors="coerce")
    mask = values.lt(summary["lower_fence"]) | values.gt(summary["upper_fence"])
    columns = [name for name in (*context_columns, column) if name in frame.columns]
    examples = frame.loc[mask, columns].copy()
    examples.insert(0, "outlier_direction", np.where(values[mask] < summary["lower_fence"], "below_lower_fence", "above_upper_fence"))
    return examples.sort_values(column).head(limit)


def ratings_by_wine_category(
    ratings: pd.DataFrame,
    wines: pd.DataFrame,
    category: str,
    minimum_ratings: int = 20,
) -> pd.DataFrame:
    if wines["WineID"].duplicated().any():
        raise ValueError("WineID must be unique before joining ratings to the catalog")
    if category not in wines.columns:
        raise KeyError(category)
    joined = ratings.merge(
        wines[["WineID", category]], on="WineID", how="left", validate="many_to_one"
    )
    result = joined.groupby(category, dropna=False)["Rating"].agg(
        rating_count="count", mean_rating="mean", median_rating="median"
    )
    return result[result["rating_count"] >= minimum_ratings].sort_values(
        "rating_count", ascending=False
    ).reset_index()


def build_wine_rating_features(
    ratings: pd.DataFrame,
    wines: pd.DataFrame,
    minimum_ratings: int = 5,
) -> pd.DataFrame:
    if wines["WineID"].duplicated().any():
        raise ValueError("WineID must be unique before joining ratings to the catalog")
    rating_means = ratings.assign(Rating=pd.to_numeric(ratings["Rating"], errors="coerce"))
    rating_summary = rating_means.groupby("WineID", dropna=True)["Rating"].agg(
        MeanRating="mean", RatingCount="count"
    ).reset_index()
    catalog_columns = [
        column for column in ("WineID", "ABV", "Type", "Country", "GrapeCount", "VintageCount")
        if column in wines.columns
    ]
    joined = rating_summary.merge(
        wines[catalog_columns], on="WineID", how="inner", validate="one_to_one"
    )
    return joined.loc[joined["RatingCount"] >= minimum_ratings].reset_index(drop=True)


def bivariate_analysis(
    ratings: pd.DataFrame,
    wines: pd.DataFrame,
    wine_features: pd.DataFrame,
    minimum_category_ratings: int = 20,
) -> dict[str, object]:
    abv_ratings = wine_features[["ABV", "MeanRating"]].apply(pd.to_numeric, errors="coerce").dropna()
    rho = None
    if len(abv_ratings) >= 2 and abv_ratings.nunique().gt(1).all():
        rho = float(abv_ratings.corr(method="spearman").loc["ABV", "MeanRating"])
    return {
        "abv_vs_mean_rating": {
            "wine_count": int(len(abv_ratings)),
            "minimum_ratings_per_wine": int(wine_features["RatingCount"].min()) if len(wine_features) else None,
            "spearman_rho": rho,
            "interpretation_scope": "descriptive_association_in_rating_sample",
        },
        "rating_by_type": ratings_by_wine_category(
            ratings, wines, "Type", minimum_category_ratings
        ).to_dict(orient="records"),
        "rating_by_country": ratings_by_wine_category(
            ratings, wines, "Country", minimum_category_ratings
        ).to_dict(orient="records"),
    }


def multivariate_analysis(wine_features: pd.DataFrame) -> dict[str, object]:
    columns = [
        column for column in ("ABV", "GrapeCount", "VintageCount", "MeanRating", "RatingCount")
        if column in wine_features.columns
    ]
    numeric = wine_features[columns].apply(pd.to_numeric, errors="coerce")
    correlation = numeric.corr(method="spearman", min_periods=2)
    matrix = {
        row: {
            column: (float(value) if pd.notna(value) else None)
            for column, value in correlation.loc[row].items()
        }
        for row in correlation.index
    }
    return {
        "unit_of_analysis": "one_row_per_wine_in_rating_sample",
        "wine_count": int(len(wine_features)),
        "features": columns,
        "minimum_ratings_per_wine": int(wine_features["RatingCount"].min()) if len(wine_features) else None,
        "spearman_correlation": matrix,
    }


def plot_rating_by_category(
    summary: pd.DataFrame,
    category: str,
    output_path: Path,
    title: str,
    top_n: int = 12,
) -> Path:
    import matplotlib.pyplot as plt

    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = summary.nlargest(top_n, "rating_count").sort_values("mean_rating")
    figure, axis = plt.subplots(figsize=(9, max(4, 0.38 * len(data))), constrained_layout=True)
    axis.barh(data[category].astype(str), data["mean_rating"], color="#4B8063")
    for position, row in enumerate(data.itertuples(index=False)):
        axis.text(row.mean_rating, position, f"  n={row.rating_count}", va="center", fontsize=8)
    axis.set(title=title, xlabel="Rating medio (escala 1-5)", ylabel=category)
    axis.set_xlim(0, 5.7)
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
    return output_path


def plot_abv_rating_scatter(
    wine_features: pd.DataFrame,
    output_path: Path,
    max_points: int = 5_000,
    seed: int = 42,
) -> Path:
    import matplotlib.pyplot as plt

    data = wine_features[["ABV", "MeanRating", "RatingCount"]].dropna(subset=["ABV", "MeanRating"])
    if len(data) > max_points:
        data = data.sample(max_points, random_state=seed)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(8, 5), constrained_layout=True)
    axis.scatter(data["ABV"], data["MeanRating"], alpha=0.35, s=18, color="#3B719F")
    axis.set(title="ABV y rating medio por vino", xlabel="ABV (%)", ylabel="Rating medio (escala 1-5)")
    axis.set_ylim(0.8, 5.2)
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
    return output_path


def plot_correlation_heatmap(
    correlation: pd.DataFrame,
    output_path: Path,
) -> Path:
    import matplotlib.pyplot as plt

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(8, 6), constrained_layout=True)
    values = correlation.to_numpy(dtype=float)
    image = axis.imshow(values, cmap="RdBu_r", vmin=-1, vmax=1)
    labels = correlation.columns.tolist()
    axis.set_xticks(range(len(labels)), labels=labels, rotation=35, ha="right")
    axis.set_yticks(range(len(labels)), labels=labels)
    for row in range(len(labels)):
        for column in range(len(labels)):
            value = values[row, column]
            label = "NA" if np.isnan(value) else f"{value:.2f}"
            axis.text(column, row, label, ha="center", va="center", fontsize=8)
    axis.set_title("Correlaciones de Spearman entre atributos por vino")
    figure.colorbar(image, ax=axis, label="Correlación de Spearman")
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
    return output_path


def plot_feature_pairplot(
    wine_features: pd.DataFrame,
    output_path: Path,
    max_points: int = 2_000,
    seed: int = 42,
) -> Path:
    import matplotlib.pyplot as plt
    from pandas.plotting import scatter_matrix

    columns = [
        column for column in ("ABV", "GrapeCount", "VintageCount", "MeanRating", "RatingCount")
        if column in wine_features.columns
    ]
    data = wine_features[columns].apply(pd.to_numeric, errors="coerce").dropna()
    if len(data) > max_points:
        data = data.sample(max_points, random_state=seed)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    axes = scatter_matrix(data, figsize=(10, 10), diagonal="hist", alpha=0.35, s=12)
    figure = axes[0, 0].get_figure()
    figure.suptitle(f"Relaciones entre atributos por vino (n={len(data):,})")
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
    return output_path


def plot_outlier_diagnostics(
    frame: pd.DataFrame,
    column: str,
    output_path: Path,
    title: str | None = None,
    show: bool = False,
) -> Path:
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        svg_path = output_path.with_suffix(".svg")
        _write_svg_diagnostic(values, column, title or f"Diagnóstico de valores extremos: {column}", svg_path)
        if show:
            print(f"Figura SVG lista para visualizar: {svg_path}")
        return svg_path

    figure, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
    axes[0].hist(values, bins="auto", color="#4B8063", edgecolor="white")
    axes[0].set(title="Distribución", xlabel=column, ylabel="Frecuencia")
    axes[1].boxplot(values, vert=False, showfliers=True, patch_artist=True,
                    boxprops={"facecolor": "#D6A75D"})
    axes[1].set(title="Diagrama de caja", xlabel=column)
    figure.suptitle(title or f"Diagnóstico de valores extremos: {column}")
    figure.savefig(output_path, dpi=150)
    if show:
        plt.show()
    plt.close(figure)
    return output_path


def _write_svg_diagnostic(values: pd.Series, column: str, title: str, path: Path) -> None:
    numeric = values.to_numpy(dtype=float)
    if numeric.size == 0:
        numeric = np.array([0.0])
    minimum, maximum = float(numeric.min()), float(numeric.max())
    if minimum == maximum:
        maximum = minimum + 1.0
    bin_count = min(30, max(8, int(np.sqrt(numeric.size))))
    frequencies, edges = np.histogram(numeric, bins=bin_count, range=(minimum, maximum))
    max_frequency = max(1, int(frequencies.max()))
    q1, median, q3 = np.percentile(numeric, [25, 50, 75])
    spread = q3 - q1
    lower_fence, upper_fence = q1 - 1.5 * spread, q3 + 1.5 * spread
    whisker_low = max(minimum, float(numeric[numeric >= lower_fence].min()))
    whisker_high = min(maximum, float(numeric[numeric <= upper_fence].max()))

    def x_position(value: float) -> float:
        return 590 + (value - minimum) / (maximum - minimum) * 340

    bars = []
    plot_left, plot_top, plot_width, plot_height = 70, 95, 400, 190
    bar_width = plot_width / bin_count
    for index, frequency in enumerate(frequencies):
        height = int(frequency / max_frequency * plot_height)
        x = plot_left + index * bar_width
        y = plot_top + plot_height - height
        bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(1, bar_width - 1):.1f}" height="{height}" fill="#4B8063"/>')

    outliers = numeric[(numeric < lower_fence) | (numeric > upper_fence)]
    if outliers.size > 200:
        outliers = outliers[np.linspace(0, outliers.size - 1, 200, dtype=int)]
    outlier_marks = "".join(
        f'<circle cx="{x_position(float(value)):.1f}" cy="210" r="3" fill="#B64C3B"/>'
        for value in outliers
    )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="380" viewBox="0 0 1000 380">
<rect width="1000" height="380" fill="#FFFFFF"/>
<text x="500" y="38" text-anchor="middle" font-family="sans-serif" font-size="21" fill="#242B27">{escape(title)}</text>
<text x="270" y="72" text-anchor="middle" font-family="sans-serif" font-size="16" fill="#242B27">Distribución</text>
<text x="760" y="72" text-anchor="middle" font-family="sans-serif" font-size="16" fill="#242B27">Diagrama de caja</text>
<line x1="70" y1="285" x2="470" y2="285" stroke="#343B37"/>
<line x1="70" y1="95" x2="70" y2="285" stroke="#343B37"/>
{''.join(bars)}
<text x="270" y="330" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#242B27">{escape(column)}</text>
<text x="24" y="190" transform="rotate(-90 24 190)" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#242B27">Frecuencia</text>
<line x1="560" y1="210" x2="950" y2="210" stroke="#343B37"/>
<line x1="{x_position(whisker_low):.1f}" y1="210" x2="{x_position(whisker_high):.1f}" y2="210" stroke="#343B37" stroke-width="2"/>
<line x1="{x_position(whisker_low):.1f}" y1="195" x2="{x_position(whisker_low):.1f}" y2="225" stroke="#343B37" stroke-width="2"/>
<line x1="{x_position(whisker_high):.1f}" y1="195" x2="{x_position(whisker_high):.1f}" y2="225" stroke="#343B37" stroke-width="2"/>
<rect x="{x_position(float(q1)):.1f}" y="180" width="{max(1, x_position(float(q3)) - x_position(float(q1))):.1f}" height="60" fill="#D6A75D" stroke="#343B37"/>
<line x1="{x_position(float(median)):.1f}" y1="180" x2="{x_position(float(median)):.1f}" y2="240" stroke="#242B27" stroke-width="3"/>
{outlier_marks}
<text x="755" y="280" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#242B27">{escape(column)}</text>
<text x="760" y="350" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#B64C3B">Puntos rojos: observaciones fuera de 1,5 × IQR</text>
</svg>'''
    path.write_text(svg, encoding="utf-8")


def compare_count_scales(counts: pd.Series) -> pd.DataFrame:
    values = pd.to_numeric(counts, errors="coerce")
    return pd.DataFrame({"count": values, "log1p_count": np.log1p(values)})