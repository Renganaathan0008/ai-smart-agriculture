"""
preprocess.py
Loads Crop_recommendation.csv + FAOSTAT_data.csv,
cleans + merges yield data, returns features/labels for training.
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
import os

# ── Paths ──────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CROP_CSV   = os.path.join(BASE, "data", "Crop_recommendation.csv")
FAOSTAT_CSV = os.path.join(BASE, "data", "FAOSTAT_data.csv")

# ── Crop name mapping: Crop_recommendation label → FAOSTAT Item name ───────
CROP_MAP = {
    "rice":        "Rice",
    "maize":       "Maize (corn)",
    "chickpea":    "Chick peas, dry",
    "kidneybeans": "Beans, dry",
    "pigeonpeas":  "Pigeon peas, dry",
    "mothbeans":   "Beans, dry",
    "mungbean":    "Beans, dry",
    "blackgram":   "Beans, dry",
    "lentil":      "Lentils, dry",
    "pomegranate": "Other fruits, n.e.c.",
    "banana":      "Bananas",
    "mango":       "Mangoes, guavas and mangosteens",
    "grapes":      "Grapes",
    "watermelon":  "Watermelons",
    "muskmelon":   "Cantaloupes and other melons",
    "apple":       "Apples",
    "orange":      "Oranges",
    "papaya":      "Papayas",
    "coconut":     "Coconuts, in shell",
    "cotton":      "Seed cotton, unginned",
    "jute":        "Jute, raw or retted",
    "coffee":      "Coffee, green",
}

# Approximate market price (USD / tonne) when FAOSTAT has no price column
PRICE_PER_TONNE = {
    "rice":        300,
    "maize":       200,
    "chickpea":    600,
    "kidneybeans": 700,
    "pigeonpeas":  550,
    "mothbeans":   500,
    "mungbean":    700,
    "blackgram":   650,
    "lentil":      600,
    "pomegranate": 1200,
    "banana":      400,
    "mango":       800,
    "grapes":      900,
    "watermelon":  200,
    "muskmelon":   250,
    "apple":       1000,
    "orange":      500,
    "papaya":      350,
    "coconut":     450,
    "cotton":      700,
    "jute":        300,
    "coffee":      2500,
}


def load_crop_recommendation():
    """Return raw crop recommendation DataFrame."""
    df = pd.read_csv(CROP_CSV)
    df.columns = df.columns.str.strip()
    df.dropna(inplace=True)
    return df


def load_faostat_yield():
    """
    Return dict: {faostat_item_name: avg_yield_kg_per_ha}
    FAOSTAT yield unit is typically hg/ha → convert to kg/ha (÷10).
    """
    df = pd.read_csv(FAOSTAT_CSV)
    df.columns = df.columns.str.strip()

    yield_df = df[df["Element"] == "Yield"].copy()
    # Keep only recent years for relevance
    yield_df = yield_df[yield_df["Year"] >= 2018]
    yield_df["Value"] = pd.to_numeric(yield_df["Value"], errors="coerce")
    yield_df.dropna(subset=["Value"], inplace=True)

    # Average across areas & years
    avg_yield = (
        yield_df.groupby("Item")["Value"]
        .mean()
        .reset_index()
        .rename(columns={"Value": "yield_hg_ha"})
    )
    avg_yield["yield_kg_ha"] = avg_yield["yield_hg_ha"] / 10.0
    return dict(zip(avg_yield["Item"], avg_yield["yield_kg_ha"]))


def build_profit_table():
    """
    Return DataFrame with columns: [crop, yield_kg_ha, price_usd_tonne, profit_usd_ha]
    profit = yield (kg/ha) × price (USD/kg)
    """
    fao_yield = load_faostat_yield()
    rows = []
    for crop, fao_item in CROP_MAP.items():
        y = fao_yield.get(fao_item, None)
        # Fallback yield from dataset statistics if FAOSTAT missing
        if y is None or y <= 0:
            y = 2000.0   # conservative fallback kg/ha
        price_usd_tonne = PRICE_PER_TONNE.get(crop, 400)
        price_usd_kg    = price_usd_tonne / 1000.0
        profit          = y * price_usd_kg
        rows.append({
            "crop":             crop,
            "yield_kg_ha":      round(y, 2),
            "price_usd_tonne":  price_usd_tonne,
            "profit_usd_ha":    round(profit, 2),
        })
    return pd.DataFrame(rows).sort_values("profit_usd_ha", ascending=False)


def prepare_features():
    """
    Returns (X, y, label_encoder, scaler)
      X      – scaled numpy array  (n_samples, 7)
      y      – encoded int labels  (n_samples,)
      le     – fitted LabelEncoder
      scaler – fitted StandardScaler
    """
    df = load_crop_recommendation()
    feature_cols = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]

    X_raw = df[feature_cols].values
    y_raw = df["label"].values

    le = LabelEncoder()
    y  = le.fit_transform(y_raw)

    scaler = StandardScaler()
    X      = scaler.fit_transform(X_raw)

    return X, y, le, scaler


if __name__ == "__main__":
    X, y, le, scaler = prepare_features()
    print(f"Feature matrix : {X.shape}")
    print(f"Classes        : {le.classes_}")
    pt = build_profit_table()
    print("\nProfit table (top 5):")
    print(pt.head())
