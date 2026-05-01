"""
train_model.py
Trains a RandomForestClassifier on Crop_recommendation.csv,
evaluates it, and saves the artefacts to models/model.pkl
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, accuracy_score

from backend.preprocess import prepare_features, build_profit_table

# ── Paths ──────────────────────────────────────────────────────────────────
BASE       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE, "models", "model.pkl")


def train():
    print("=" * 60)
    print("  Smart Agriculture — ML Training Pipeline")
    print("=" * 60)

    # 1. Load & preprocess
    print("\n[1/5] Loading & preprocessing data …")
    X, y, le, scaler = prepare_features()
    print(f"      Samples : {X.shape[0]}")
    print(f"      Features: {X.shape[1]}")
    print(f"      Classes : {len(le.classes_)}  → {list(le.classes_)}")

    # 2. Train / test split
    print("\n[2/5] Splitting train/test (80/20) …")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # 3. Fit RandomForest
    print("\n[3/5] Training RandomForestClassifier …")
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_split=2,
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)

    # 4. Evaluate
    print("\n[4/5] Evaluating …")
    y_pred = rf.predict(X_test)
    acc    = accuracy_score(y_test, y_pred)
    cv_scores = cross_val_score(rf, X, y, cv=5, scoring="accuracy")

    print(f"\n      Test  accuracy : {acc * 100:.2f}%")
    print(f"      5-Fold CV mean : {cv_scores.mean() * 100:.2f}%  "
          f"(±{cv_scores.std() * 100:.2f}%)")
    print("\n      Classification report:")
    print(classification_report(y_test, y_pred,
                                target_names=le.classes_))

    # 5. Build profit table & save everything
    print("\n[5/5] Building profit table & saving model …")
    profit_df = build_profit_table()
    profit_dict = dict(zip(profit_df["crop"], profit_df["profit_usd_ha"]))
    yield_dict  = dict(zip(profit_df["crop"], profit_df["yield_kg_ha"]))
    price_dict  = dict(zip(profit_df["crop"], profit_df["price_usd_tonne"]))

    artefacts = {
        "model":        rf,
        "label_encoder": le,
        "scaler":       scaler,
        "profit":       profit_dict,
        "yield_kg_ha":  yield_dict,
        "price_usd_t":  price_dict,
        "accuracy":     round(acc * 100, 2),
        "cv_mean":      round(cv_scores.mean() * 100, 2),
    }
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(artefacts, f)

    print(f"\n      ✅  Model saved → {MODEL_PATH}")
    print(f"\n  Top 5 profitable crops:")
    print(profit_df[["crop","yield_kg_ha","price_usd_tonne","profit_usd_ha"]].head())
    print("\n" + "=" * 60)
    print("  Training complete!")
    print("=" * 60)
    return artefacts


if __name__ == "__main__":
    train()
