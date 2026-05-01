"""
profit.py
Given model probabilities and the saved profit/yield/price tables,
return the top-N profitable crops for the given conditions.
"""

import numpy as np


def get_top_crops(probabilities, label_encoder, profit_dict,
                  yield_dict, price_dict, top_n=3):
    """
    Parameters
    ----------
    probabilities  : 1-D numpy array, len = n_classes (from model.predict_proba)
    label_encoder  : fitted LabelEncoder
    profit_dict    : {crop: profit_usd_ha}
    yield_dict     : {crop: yield_kg_ha}
    price_dict     : {crop: price_usd_tonne}
    top_n          : how many crops to return

    Returns
    -------
    list of dicts with keys: crop, confidence, yield_kg_ha,
                              price_usd_tonne, profit_usd_ha, rank
    """
    class_names = label_encoder.classes_

    # Build a scored list: weight profit by model confidence
    scored = []
    for idx, conf in enumerate(probabilities):
        crop = class_names[idx]
        profit = profit_dict.get(crop, 0)
        # Composite score = confidence × profit (rank by opportunity)
        composite = conf * profit
        scored.append({
            "crop":           crop,
            "confidence":     round(float(conf) * 100, 2),
            "yield_kg_ha":    round(yield_dict.get(crop, 0), 2),
            "price_usd_tonne": price_dict.get(crop, 0),
            "profit_usd_ha":  round(profit_dict.get(crop, 0), 2),
            "composite_score": composite,
        })

    # Sort by composite score descending
    scored.sort(key=lambda x: x["composite_score"], reverse=True)

    # Assign rank, drop helper field
    result = []
    for rank, item in enumerate(scored[:top_n], start=1):
        item["rank"] = rank
        item.pop("composite_score")
        result.append(item)

    return result


def get_primary_prediction(probabilities, label_encoder):
    """Return the single highest-confidence prediction with its score."""
    idx  = int(np.argmax(probabilities))
    conf = float(probabilities[idx])
    crop = label_encoder.classes_[idx]
    return crop, round(conf * 100, 2)
