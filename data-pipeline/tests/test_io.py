from pathlib import Path

from wine_pipeline.io import inspect_csv, iter_ratings, read_wines


def test_csv_io_handles_quotes_and_reads_ratings_in_chunks(tmp_path: Path):
    wines = tmp_path / "wines.csv"
    wines.write_text('WineID,WineName,Grapes\n1,"Wine, Reserve","[\'Grape\']"\n', encoding="utf-8")
    ratings = tmp_path / "ratings.csv"
    ratings.write_text("RatingID,UserID,WineID,Vintage,Rating,Date\n1,4,1,2020,4.5,2020-01-02 10:00:00\n", encoding="utf-8")

    assert read_wines(wines).loc[0, "WineName"] == "Wine, Reserve"
    assert len(list(iter_ratings(ratings, chunksize=1))) == 1
    profile = inspect_csv(ratings)
    assert profile["columns"] == ["RatingID", "UserID", "WineID", "Vintage", "Rating", "Date"]
    assert len(profile["sha256"]) == 64