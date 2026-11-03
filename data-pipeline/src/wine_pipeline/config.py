from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
QUALITY_DIR = REPORTS_DIR / "data_quality"
FIGURES_DIR = REPORTS_DIR / "figures"
SUMMARY_DIR = REPORTS_DIR / "summary"

WINES_FILE = RAW_DIR / "XWines_Full_100K_wines.csv"
RATINGS_FILE = RAW_DIR / "XWines_Full_21M_ratings.csv"
SOURCE_NAME = "xwines"
RANDOM_SEED = 42

WINE_COLUMNS = [
    "WineID", "WineName", "Type", "Elaborate", "Grapes", "Harmonize", "ABV",
    "Body", "Acidity", "Code", "Country", "RegionID", "RegionName",
    "WineryID", "WineryName", "Website", "Vintages",
]
RATING_COLUMNS = ["RatingID", "UserID", "WineID", "Vintage", "Rating", "Date"]