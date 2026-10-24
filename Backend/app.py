
import os
from pathlib import Path

from flask import Flask, jsonify
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Load MongoDB credentials
env_path = Path(__file__).resolve().parent / "atlas-credentials.env"
load_dotenv(env_path)

# Read environment variables
MONGO_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "Menu-Randomizer")

if not MONGO_URI:
    raise RuntimeError("MONGO_URI is missing from atlas-credentials.env")

# Connect to MongoDB Atlas
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]

# Create Flask application
app = Flask(__name__)


# Test Flask
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "message": "Flask backend is running!"
    })


# Test MongoDB Atlas connection
@app.route("/api/db-test", methods=["GET"])
def test_database():
    try:
        client.admin.command("ping")

        return jsonify({
            "message": "MongoDB Atlas connected successfully!",
            "database": db.name
        }), 200

    except PyMongoError:
        app.logger.exception("MongoDB connection failed")

        return jsonify({
            "error": "MongoDB connection failed"
        }), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
