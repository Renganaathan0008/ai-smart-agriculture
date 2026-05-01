"""
explain.py
Rule-based explanation generator — no LLM, no external calls.
Produces a human-readable paragraph explaining why a crop was recommended
based on the user's input conditions.
"""

# ── Per-crop known preferences ──────────────────────────────────────────────
# Each entry: (rainfall_min, rainfall_max, temp_min, temp_max, ph_min, ph_max)
CROP_PROFILE = {
    "rice":        (150, 300,  20, 35, 5.5, 7.0),
    "maize":       (50,  150,  18, 35, 5.5, 7.5),
    "chickpea":    (65,  200,  15, 30, 5.5, 7.0),
    "kidneybeans": (60,  180,  15, 30, 6.0, 7.5),
    "pigeonpeas":  (60,  200,  18, 35, 5.0, 7.0),
    "mothbeans":   (40,  120,  25, 42, 5.5, 7.5),
    "mungbean":    (50,  180,  25, 40, 6.0, 7.5),
    "blackgram":   (60,  200,  25, 40, 6.0, 7.5),
    "lentil":      (60,  200,  15, 25, 6.0, 8.0),
    "pomegranate": (50,  200,  20, 38, 5.5, 7.2),
    "banana":      (80,  220,  25, 40, 5.5, 7.0),
    "mango":       (60,  200,  24, 42, 5.5, 7.5),
    "grapes":      (50,  150,  15, 35, 5.5, 7.0),
    "watermelon":  (40,  100,  24, 40, 6.0, 7.0),
    "muskmelon":   (40,  100,  24, 38, 6.0, 7.5),
    "apple":       (100, 250,  10, 25, 5.5, 6.5),
    "orange":      (100, 250,  15, 35, 6.0, 7.5),
    "papaya":      (80,  250,  22, 38, 6.0, 7.0),
    "coconut":     (100, 300,  25, 38, 5.0, 8.0),
    "cotton":      (50,  150,  21, 35, 5.8, 8.0),
    "jute":        (150, 300,  24, 38, 6.0, 7.0),
    "coffee":      (100, 250,  15, 30, 6.0, 6.5),
}

# ── Rainfall band labels ────────────────────────────────────────────────────
def _rainfall_label(mm):
    if mm < 60:   return "very low",   "drought-tolerant"
    if mm < 120:  return "low",        "moderate water requirement"
    if mm < 200:  return "moderate",   "average water requirement"
    if mm < 300:  return "high",       "high water requirement"
    return             "very high",   "heavy rainfall tolerance"

def _temp_label(t):
    if t < 15:  return "cool",    "cool-season"
    if t < 22:  return "mild",    "mild-temperature"
    if t < 30:  return "warm",    "warm-season"
    if t < 38:  return "hot",     "heat-tolerant"
    return          "very hot", "extreme-heat-tolerant"

def _ph_label(ph):
    if ph < 5.5:  return "strongly acidic"
    if ph < 6.5:  return "mildly acidic"
    if ph < 7.5:  return "neutral"
    if ph < 8.5:  return "mildly alkaline"
    return              "strongly alkaline"

def _match(val, lo, hi):
    """Return 'ideal', 'acceptable', or 'marginal' fit."""
    margin = (hi - lo) * 0.15
    if lo <= val <= hi:
        return "ideal"
    if (lo - margin) <= val <= (hi + margin):
        return "acceptable"
    return "marginal"


def generate_explanation(inputs: dict, crop: str) -> dict:
    """
    Parameters
    ----------
    inputs : dict with keys N, P, K, temperature, humidity, ph, rainfall
    crop   : predicted crop name (lowercase string)

    Returns
    -------
    dict with keys: summary, details (list of str), tip
    """
    rf   = float(inputs.get("rainfall",    0))
    temp = float(inputs.get("temperature", 0))
    ph   = float(inputs.get("ph",          7))
    n    = float(inputs.get("N",           0))
    p    = float(inputs.get("P",           0))
    k    = float(inputs.get("K",           0))
    hum  = float(inputs.get("humidity",    0))

    crop_key  = crop.lower()
    profile   = CROP_PROFILE.get(crop_key)

    rf_band,   rf_desc   = _rainfall_label(rf)
    temp_band, temp_desc = _temp_label(temp)
    ph_desc              = _ph_label(ph)

    details = []
    tip     = None

    if profile:
        rf_lo, rf_hi, t_lo, t_hi, ph_lo, ph_hi = profile

        rf_fit   = _match(rf,   rf_lo,  rf_hi)
        temp_fit = _match(temp, t_lo,   t_hi)
        ph_fit   = _match(ph,   ph_lo,  ph_hi)

        # Rainfall detail
        if rf_fit == "ideal":
            details.append(
                f"Rainfall of {rf:.0f} mm is within the ideal range "
                f"({rf_lo}–{rf_hi} mm) for {crop}."
            )
        elif rf_fit == "acceptable":
            details.append(
                f"Rainfall of {rf:.0f} mm is slightly outside the preferred "
                f"range ({rf_lo}–{rf_hi} mm) but still manageable for {crop}."
            )
        else:
            details.append(
                f"Rainfall of {rf:.0f} mm is outside the optimal range "
                f"({rf_lo}–{rf_hi} mm); irrigation or drainage may be needed."
            )
            tip = "Consider supplemental irrigation or water management practices."

        # Temperature detail
        if temp_fit == "ideal":
            details.append(
                f"Temperature of {temp:.1f} °C is ideal for {crop} "
                f"(optimal: {t_lo}–{t_hi} °C)."
            )
        elif temp_fit == "acceptable":
            details.append(
                f"Temperature of {temp:.1f} °C is near the boundary of the "
                f"preferred range ({t_lo}–{t_hi} °C) for {crop}."
            )
        else:
            details.append(
                f"Temperature of {temp:.1f} °C may stress {crop} "
                f"(preferred: {t_lo}–{t_hi} °C). Monitor crop health closely."
            )
            if not tip:
                tip = "Use shade nets or mulching to moderate soil temperature."

        # pH detail
        if ph_fit == "ideal":
            details.append(
                f"Soil pH of {ph:.1f} ({ph_desc}) is well-suited for {crop} "
                f"(optimal: {ph_lo}–{ph_hi})."
            )
        else:
            details.append(
                f"Soil pH of {ph:.1f} ({ph_desc}) is slightly outside the "
                f"optimal range ({ph_lo}–{ph_hi}) for {crop}. "
                f"{'Add lime to raise pH.' if ph < ph_lo else 'Add sulfur or organic matter to lower pH.'}"
            )
            if not tip:
                tip = ("Apply agricultural lime to raise pH." if ph < ph_lo
                       else "Apply sulfur or compost to lower soil pH.")

    else:
        # Generic fallback if crop not in profile table
        details.append(
            f"The field conditions (rainfall {rf:.0f} mm, "
            f"temperature {temp:.1f} °C, pH {ph:.1f}) are suitable for {crop}."
        )

    # Nutrient commentary
    if n > 80:
        details.append(f"Nitrogen level ({n:.0f} mg/kg) is high — good for leafy growth.")
    elif n < 30:
        details.append(f"Nitrogen level ({n:.0f} mg/kg) is low; consider urea or compost top-dressing.")

    if k > 80:
        details.append(f"Potassium ({k:.0f} mg/kg) is adequate for strong root and fruit development.")

    if hum > 85:
        details.append("High humidity may increase fungal disease risk — ensure good canopy airflow.")
    elif hum < 40:
        details.append("Low humidity may increase water stress; monitor soil moisture regularly.")

    # Build one-sentence summary
    fit_words = {
        "ideal":      "excellent",
        "acceptable": "good",
        "marginal":   "challenging",
    }
    if profile:
        fits      = [_match(rf, profile[0], profile[1]),
                     _match(temp, profile[2], profile[3]),
                     _match(ph, profile[4], profile[5])]
        best_fit  = "excellent" if fits.count("ideal") >= 2 else \
                    "good"      if "marginal" not in fits else "challenging"
        summary = (
            f"{crop.capitalize()} is a {best_fit} match for your field. "
            f"The {rf_band} rainfall, {temp_band} temperature, and "
            f"{ph_desc} soil provide {'optimal' if best_fit == 'excellent' else 'workable'} "
            f"growing conditions."
        )
    else:
        summary = (
            f"{crop.capitalize()} suits the given field conditions — "
            f"{rf_band} rainfall, {temp_band} temperature, and {ph_desc} soil."
        )

    return {
        "summary": summary,
        "details": details,
        "tip":     tip or "Maintain consistent irrigation and monitor for pests during the growing season.",
    }
