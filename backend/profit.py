"""
profit.py
Given model probabilities and the saved profit/yield/price tables,
return the top-N profitable crops for the given conditions.

Changes vs v1
─────────────
- get_top_crops: filters low-confidence crops BEFORE profit ranking
  (threshold: MIN_CONFIDENCE_THRESHOLD = 0.05 i.e. 5%)
- Profit composite score computed ONLY on the filtered candidate set
- Stability guard: if no crop clears the threshold, returns only the
  single highest-probability crop (prevents empty result)
- get_primary_prediction: unchanged — always returns the argmax crop
"""

import numpy as np

# Crops below this probability are excluded before any profit ranking.
# 5% is a sensible floor for a 22-class model (random baseline ≈ 4.5%).
MIN_CONFIDENCE_THRESHOLD = 0.05   # 5%


def get_top_crops(probabilities, label_encoder, profit_dict,
                  yield_dict, price_dict, top_n=3):
    class_names = label_encoder.classes_

    # Step 1 — pair every crop with its raw probability
    candidates = [
        (class_names[i], float(probabilities[i]))
        for i in range(len(probabilities))
    ]

    # Step 2 — sort by probability descending
    candidates.sort(key=lambda x: x[1], reverse=True)

    # Step 3 — filter: keep only crops above the confidence threshold
    filtered = [(crop, conf) for crop, conf in candidates
                if conf >= MIN_CONFIDENCE_THRESHOLD]

    # Stability guard: if nothing clears the threshold, return only the
    # single best crop rather than an empty list
    if not filtered:
        best_crop, best_conf = candidates[0]
        return [_build_record(1, best_crop, best_conf,
                              profit_dict, yield_dict, price_dict)]

    # Step 4 — cap at top_n BEFORE computing profit scores
    top_candidates = filtered[:top_n]

    # Step 5 — rank the filtered set by composite score (confidence × profit)
    top_candidates.sort(
        key=lambda x: x[1] * profit_dict.get(x[0], 0.0),
        reverse=True,
    )

    # Step 6 — build output records
    return [
        _build_record(rank, crop, conf, profit_dict, yield_dict, price_dict)
        for rank, (crop, conf) in enumerate(top_candidates, start=1)
    ]


def _build_record(rank, crop, conf, profit_dict, yield_dict, price_dict):
    """
    Build one output dict. Used by both the normal path and the
    stability fallback so the output shape is always identical.

    Approximate mapping note: some crops share a FAOSTAT entry
    (e.g. kidneybeans / mothbeans / mungbean / blackgram all map to
    "Beans, dry") — profit figures for these are indicative, not exact.
    """
    return {
        "rank":            rank,
        "crop":            crop,
        "confidence":      round(conf * 100, 2),   # 0-1 → percentage
        "yield_kg_ha":     round(float(yield_dict.get(crop, 0.0)), 2),
        "price_usd_tonne": int(price_dict.get(crop, 0)),
        "profit_usd_ha":   round(float(profit_dict.get(crop, 0.0)), 2),
    }


def get_primary_prediction(probabilities, label_encoder):
    """Always returns the argmax crop — unchanged from v1."""
    idx  = int(np.argmax(probabilities))
    conf = float(probabilities[idx])
    crop = label_encoder.classes_[idx]
    return crop, round(conf * 100, 2)