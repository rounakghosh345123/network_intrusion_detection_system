"""Intrushield V2 - Flask backend. Run with:  python backend/app.py"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

# ---------- Paths (derived from this file, so they work from any folder) ----------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# ---------- Load the three model artifacts once, when the server starts ----------
model = joblib.load(MODELS_DIR / "xgboost_attack_model_13class_balanced.joblib")
feature_names = [str(f) for f in joblib.load(MODELS_DIR / "xgboost_attack_model_13class_features.joblib")]
raw_mapping = joblib.load(MODELS_DIR / "xgboost_attack_model_13class_mapping.joblib")


def build_class_mapping(raw):
    """Turn the mapping artifact into {class_id: label}.
    Handles {0: 'BENIGN'}, {'BENIGN': 0} and ['BENIGN', 'Bot', ...}."""
    if isinstance(raw, dict):
        mapping = {}
        for key, value in raw.items():
            if isinstance(value, (int, np.integer)) and not isinstance(key, (int, np.integer)):
                mapping[int(value)] = str(key)      # label -> id
            else:
                mapping[int(key)] = str(value)      # id -> label
        return mapping
    return {i: str(label) for i, label in enumerate(raw)}


class_mapping = build_class_mapping(raw_mapping)
NUM_CLASSES = len(class_mapping)
NUM_FEATURES = len(feature_names)

MAX_SAMPLE_ROWS = 100      # prediction rows sent back to the browser
CHUNK_SIZE = 100_000       # rows predicted at a time (keeps memory low)

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024   # 500 MB upload limit


# ---------- Serve the frontend from the same Flask process ----------
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def frontend_files(filename):
    if filename in ("style.css", "script.js"):
        return send_from_directory(FRONTEND_DIR, filename)
    return jsonify({"success": False, "error": "Not found."}), 404


# ---------- API routes ----------
@app.route("/health")
def health():
    return jsonify({"status": "online", "model": "XGBoost", "classes": NUM_CLASSES, "features": NUM_FEATURES})


@app.route("/model-info")
def model_info():
    return jsonify({
        "model": "XGBoost Multiclass Classifier",
        "classes": NUM_CLASSES,
        "features": NUM_FEATURES,
        "feature_names": feature_names,
        "class_mapping": {str(k): v for k, v in class_mapping.items()},
    })


@app.route("/predict", methods=["POST"])
def predict():
    # 1. Check that a CSV file was sent
    file = request.files.get("file")
    if file is None or file.filename == "":
        return jsonify({"success": False, "error": "No CSV file was provided."}), 400
    if not file.filename.lower().endswith(".csv"):
        return jsonify({"success": False, "error": "Please upload a CSV file."}), 400

    # 2. Read the CSV (malformed files give a clean error)
    try:
        df = pd.read_csv(file)
    except Exception:
        return jsonify({"success": False, "error": "The file could not be read as a valid CSV."}), 400
    if df.empty:
        return jsonify({"success": False, "error": "The CSV file has no rows."}), 400

    # 3. Check that all required features exist (extra columns are ignored)
    df.columns = [str(c).strip() for c in df.columns]
    missing = [f for f in feature_names if f not in df.columns]
    if missing:
        return jsonify({"success": False,
                        "error": "The uploaded file is missing required model features.",
                        "missing_features": missing}), 400

    # 4. Select the features in the exact order the model expects, clean bad values
    X = df[feature_names].apply(pd.to_numeric, errors="coerce")
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0)

    # 5. Predict in chunks: class ids + probabilities, confidence = highest probability
    try:
        ids_list, conf_list = [], []
        for start in range(0, len(X), CHUNK_SIZE):
            chunk = X.iloc[start:start + CHUNK_SIZE]
            ids_list.append(np.asarray(model.predict(chunk)).astype(int))
            conf_list.append(model.predict_proba(chunk).max(axis=1))
        class_ids = np.concatenate(ids_list)
        confidence = np.concatenate(conf_list)
    except Exception:
        return jsonify({"success": False, "error": "The model could not analyze this data."}), 500

    # 6. Convert ids to labels and decide BENIGN vs ATTACK
    labels = [class_mapping.get(int(i), f"Class {i}") for i in class_ids]
    is_benign = np.array([l.upper() == "BENIGN" for l in labels])
    benign_count = int(is_benign.sum())

    distribution = pd.Series(labels).value_counts().to_dict()
    sample = [{
        "row": i + 1,
        "class_id": int(class_ids[i]),
        "label": labels[i],
        "confidence": round(float(confidence[i]), 4),
        "status": "BENIGN" if is_benign[i] else "ATTACK",
    } for i in range(min(MAX_SAMPLE_ROWS, len(labels)))]

    return jsonify({
        "success": True,
        "rows_analyzed": int(len(labels)),
        "benign_count": benign_count,
        "attack_count": int(len(labels) - benign_count),
        "average_confidence": round(float(confidence.mean()), 4),
        "distribution": {k: int(v) for k, v in distribution.items()},
        "predictions": sample,
        "predictions_shown": len(sample),
    })


@app.errorhandler(413)
def too_large(_):
    return jsonify({"success": False, "error": "File is too large (limit 500 MB)."}), 413


if __name__ == "__main__":
    print("Intrushield V2 running at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
