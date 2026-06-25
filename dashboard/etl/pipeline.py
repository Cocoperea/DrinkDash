import pandas as pd
import sqlite3
from pathlib import Path


def extract_csv(csv_path):
    return pd.read_csv(csv_path)


def transform(df):
    df = df.dropna()
    df.columns = [c.lower().strip() for c in df.columns]
    return df


def load_to_sqlite(df, db_path):
    conn = sqlite3.connect(db_path)
    df.to_sql("data", conn, if_exists="replace", index=False)
    conn.close()


def run_etl():
    base_dir = Path(__file__).resolve().parents[2]

    csv_path = base_dir / "data" / "sales_drinks.csv"
    db_path = base_dir / "data" / "drinkdash.db"

    df = extract_csv(csv_path)
    df = transform(df)
    load_to_sqlite(df, db_path)