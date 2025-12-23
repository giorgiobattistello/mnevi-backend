import os
import hashlib
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

# Directory upload
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)

# Limite upload: 20 MB
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024


def sha256_of_file(path):
    """Calcola SHA-256 di un file"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


@app.route("/", methods=["GET"])
def health():
    """Health check"""
    return jsonify({
        "status": "ok",
        "service": "mnevi-backend"
    }), 200


@app.route("/upload", methods=["POST"])
def upload():
    """Upload file e genera ricevuta MNEVI"""
    if "file" not in request.files:
        return jsonify({"error": "file missing"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "empty filename"}), 400

    filename = secure_filename(file.filename)
    uid = str(uuid.uuid4())
    filepath = os.path.join(UPLOAD_DIR, f"{uid}_{filename}")
    file.save(filepath)

    file_hash = sha256_of_file(filepath)
    timestamp = datetime.utcnow().isoformat() + "Z"

    receipt = {
        "mnevi_version": "1.0",
        "receipt_id": f"mnevi-{uid}",
        "file_name": filename,
        "file_hash_sha256": file_hash,
        "timestamp_utc": timestamp,
        "algorithm": "SHA-256",
        "proof_type": "existence",
        "network": "offchain-mvp",
        "issuer": "mnevi.app"
    }

    receipt_path = os.path.join(UPLOAD_DIR, f"{uid}_receipt.json")
    with open(receipt_path, "w", encoding="utf-8") as r:
        json.dump(receipt, r, indent=2)

    return jsonify(receipt), 200


@app.route("/verify", methods=["POST"])
def verify():
    """Verifica integrità file rispetto alla ricevuta"""
    if "file" not in request.files or "receipt" not in request.files:
        return jsonify({"error": "file and receipt required"}), 400

    file = request.files["file"]
    receipt_file = request.files["receipt"]

    tmp_path = os.path.join(UPLOAD_DIR, secure_filename(file.filename))
    file.save(tmp_path)

    computed_hash = sha256_of_file(tmp_path)
    receipt = json.load(receipt_file)

    valid = computed_hash == receipt.get("file_hash_sha256")

    return jsonify({
        "valid": valid,
        "computed_hash": computed_hash,
        "receipt_hash": receipt.get("file_hash_sha256")
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
