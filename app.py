"""
app.py  —  Smart Agriculture Flask Application
Run:  python app.py
"""

import os, sys, pickle, json
import numpy as np
from flask import Flask, request, jsonify, render_template

# ── Make sure sibling packages resolve ────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from backend.profit import get_top_crops, get_primary_prediction
from backend.explain import generate_explanation
from backend.explain import generate_explanation

app = Flask(
    __name__,
    template_folder=os.path.join(BASE, "frontend", "templates"),
    static_folder=os.path.join(BASE, "frontend", "static"),
)

# ── Load model artefacts once at startup ──────────────────────────────────
MODEL_PATH = os.path.join(BASE, "models", "model.pkl")

def load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"model.pkl not found at {MODEL_PATH}. "
            "Run:  python backend/train_model.py"
        )
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)

ARTEFACTS = load_model()
MODEL   = ARTEFACTS["model"]
LE      = ARTEFACTS["label_encoder"]
SCALER  = ARTEFACTS["scaler"]
PROFIT  = ARTEFACTS["profit"]
YIELD   = ARTEFACTS["yield_kg_ha"]
PRICE   = ARTEFACTS["price_usd_t"]
ACC     = ARTEFACTS["accuracy"]
CV_MEAN = ARTEFACTS["cv_mean"]

print(f"[app] Model loaded — test accuracy {ACC}%  |  CV mean {CV_MEAN}%")

# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("home.html", model_accuracy=ACC, cv_mean=CV_MEAN)


@app.route("/predict", methods=["GET"])
def predict_page():
    return render_template("index.html", model_accuracy=ACC, cv_mean=CV_MEAN)


@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json(force=True)

        # Validate & parse inputs
        fields = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
        missing = [f for f in fields if f not in data]
        if missing:
            return jsonify({"error": f"Missing fields: {missing}"}), 400

        features = np.array([[
            float(data["N"]),
            float(data["P"]),
            float(data["K"]),
            float(data["temperature"]),
            float(data["humidity"]),
            float(data["ph"]),
            float(data["rainfall"]),
        ]])

        # Scale → predict
        features_scaled = SCALER.transform(features)
        probas = MODEL.predict_proba(features_scaled)[0]

        # Primary prediction
        primary_crop, primary_conf = get_primary_prediction(probas, LE)

        # Top-3 profit-weighted recommendations
        top3 = get_top_crops(probas, LE, PROFIT, YIELD, PRICE, top_n=3)

        explanation = generate_explanation(data, primary_crop)

        response = {
            "primary": {
                "crop":           primary_crop,
                "confidence":     primary_conf,
                "yield_kg_ha":    round(YIELD.get(primary_crop, 0), 2),
                "price_usd_tonne": PRICE.get(primary_crop, 0),
                "profit_usd_ha":  round(PROFIT.get(primary_crop, 0), 2),
            },
            "top3":         top3,
            "explanation":  explanation,
            "model_accuracy": ACC,
        }
        return jsonify(response)

    except ValueError as ve:
        return jsonify({"error": f"Invalid input: {ve}"}), 422
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok", "accuracy": ACC, "cv_mean": CV_MEAN})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
