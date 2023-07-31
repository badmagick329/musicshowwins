from pathlib import Path

import pandas as pd


def process_csv():
    CSV_DIR = Path(__file__).parent.parent / "data"
    csv_file = CSV_DIR / "2016_music_core_no_dates.csv"
    df = pd.read_csv(csv_file)
    new_df = pd.DataFrame(columns=["Date", "Artist", "Song"])
    for _, row in df.iterrows():
        count = int(row["Wins"])
        for _ in range(count):
            new_df.loc[len(new_df)] = {
                "Date": "-",
                "Artist": row["Artist"],
                "Song": row["Song"],
            }
    new_df.to_csv(CSV_DIR / "2016_music_core.csv", index=False)


def main():
    process_csv()


if __name__ == "__main__":
    main()
