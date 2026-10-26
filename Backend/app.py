
import os
from pathlib import Path

from flask import Flask, jsonify, request
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from bson import ObjectId
from bson.errors import InvalidId
import requests

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

# Get all categories from MongoDB
@app.route("/api/categories", methods=["GET"])
def get_categories():
    try:
        categories_collection = db["Categories"]

        categories = list(categories_collection.find())

        # Convert MongoDB ObjectId to a JSON-compatible string
        for category in categories:
            category["id"] = str(category.pop("_id"))

        return jsonify(categories), 200

    except PyMongoError:
        app.logger.exception("Failed to retrieve categories")

        return jsonify({
            "error": "Failed to retrieve categories"
        }), 500


# Create a new category
@app.route("/api/categories", methods=["POST"])
def create_category():
    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "error": "A JSON object is required"
            }), 400

        title = data.get("title")

        if not isinstance(title, str) or not title.strip():
            return jsonify({
                "error": "Category title is required"
            }), 400

        new_category = {
            "title": title.strip(),
            "dishes": []
        }

        result = db["Categories"].insert_one(new_category)

        return jsonify({
            "id": str(result.inserted_id),
            "title": new_category["title"],
            "dishes": []
        }), 201

    except PyMongoError:
        app.logger.exception("Failed to create category")

        return jsonify({
            "error": "Failed to create category"
        }), 500


# Update an existing category
@app.route("/api/categories/<category_id>", methods=["PUT"])
def update_category(category_id):
    try:
        # Convert string ID into MongoDB ObjectId
        try:
            object_id = ObjectId(category_id)
        except InvalidId:
            return jsonify({
                "error": "Invalid category ID"
            }), 400

        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "error": "A JSON object is required"
            }), 400

        title = data.get("title")

        if not isinstance(title, str) or not title.strip():
            return jsonify({
                "error": "Category title is required"
            }), 400

        # Update category in MongoDB
        result = db["Categories"].update_one(
            {"_id": object_id},
            {"$set": {"title": title.strip()}}
        )

        if result.matched_count == 0:
            return jsonify({
                "error": "Category not found"
            }), 404

        # Retrieve updated category
        category = db["Categories"].find_one(
            {"_id": object_id}
        )

        category["id"] = str(category.pop("_id"))

        return jsonify(category), 200

    except PyMongoError:
        app.logger.exception("Failed to update category")

        return jsonify({
            "error": "Failed to update category"
        }), 500


# Delete an existing category
@app.route("/api/categories/<category_id>", methods=["DELETE"])
def delete_category(category_id):
    try:
        # Convert string ID into MongoDB ObjectId
        try:
            object_id = ObjectId(category_id)
        except InvalidId:
            return jsonify({
                "error": "Invalid category ID"
            }), 400

        # Delete category from MongoDB
        result = db["Categories"].delete_one(
            {"_id": object_id}
        )

        if result.deleted_count == 0:
            return jsonify({
                "error": "Category not found"
            }), 404

        return jsonify({
            "message": "Category deleted successfully"
        }), 200

    except PyMongoError:
        app.logger.exception("Failed to delete category")

        return jsonify({
            "error": "Failed to delete category"
        }), 500


# Add a dish to an existing category
@app.route("/api/categories/<category_id>/dishes", methods=["POST"])
def add_dish(category_id):
    try:
        # Validate category ID
        try:
            object_id = ObjectId(category_id)
        except InvalidId:
            return jsonify({
                "error": "Invalid category ID"
            }), 400

        # Read request body
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "error": "A JSON object is required"
            }), 400

        name = data.get("name")

        if not isinstance(name, str) or not name.strip():
            return jsonify({
                "error": "Dish name is required"
            }), 400


        # Optional TheMealDB information
        meal_db_id = data.get("mealDbId")
        image_url = data.get("imageUrl")

        # Validate optional fields
        if meal_db_id is not None and not isinstance(meal_db_id, str):
            return jsonify({
                "error": "mealDbId must be a string"
            }), 400

        if image_url is not None and not isinstance(image_url, str):
            return jsonify({
                "error": "imageUrl must be a string"
            }), 400
        
        # Generate a unique ID for the dish
        new_dish = {
            "id": str(ObjectId()),
            "name": name.strip(),
            "mealDbId": meal_db_id,
            "imageUrl": image_url
        }

        # Add dish to the category's dishes array
        result = db["Categories"].update_one(
            {"_id": object_id},
            {"$push": {"dishes": new_dish}}
        )

        if result.matched_count == 0:
            return jsonify({
                "error": "Category not found"
            }), 404

        return jsonify(new_dish), 201

    except PyMongoError:
        app.logger.exception("Failed to add dish")

        return jsonify({
            "error": "Failed to add dish"
        }), 500


# Update an existing dish
@app.route(
    "/api/categories/<category_id>/dishes/<dish_id>",
    methods=["PUT"]
)
def update_dish(category_id, dish_id):
    try:
        # Validate category ID
        try:
            object_id = ObjectId(category_id)
        except InvalidId:
            return jsonify({
                "error": "Invalid category ID"
            }), 400

        # Read JSON request body
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "error": "A JSON object is required"
            }), 400

        name = data.get("name")

        if not isinstance(name, str) or not name.strip():
            return jsonify({
                "error": "Dish name is required"
            }), 400

        # Find and update the dish inside its category
        result = db["Categories"].update_one(
            {
                "_id": object_id,
                "dishes.id": dish_id
            },
            {
                "$set": {
                    "dishes.$.name": name.strip()
                }
            }
        )

        if result.matched_count == 0:
            return jsonify({
                "error": "Category or dish not found"
            }), 404

        return jsonify({
            "id": dish_id,
            "name": name.strip()
        }), 200

    except PyMongoError:
        app.logger.exception("Failed to update dish")

        return jsonify({
            "error": "Failed to update dish"
        }), 500


# Delete a dish from an existing category
@app.route(
    "/api/categories/<category_id>/dishes/<dish_id>",
    methods=["DELETE"]
)
def delete_dish(category_id, dish_id):
    try:
        # Validate category ID
        try:
            object_id = ObjectId(category_id)
        except InvalidId:
            return jsonify({
                "error": "Invalid category ID"
            }), 400

        # Remove the dish from the category's dishes array
        result = db["Categories"].update_one(
            {
                "_id": object_id,
                "dishes.id": dish_id
            },
            {
                "$pull": {
                    "dishes": {"id": dish_id}
                }
            }
        )

        if result.matched_count == 0:
            return jsonify({
                "error": "Category or dish not found"
            }), 404

        return jsonify({
            "message": "Dish deleted successfully"
        }), 200

    except PyMongoError:
        app.logger.exception("Failed to delete dish")

        return jsonify({
            "error": "Failed to delete dish"
        }), 500


# Search meals using TheMealDB API
@app.route("/api/meals/search", methods=["GET"])
def search_meals():
    # Get the search query from the URL
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify({
            "error": "Search query is required"
        }), 400

    try:
        # Send request to TheMealDB
        response = requests.get(
            "https://www.themealdb.com/api/json/v1/1/search.php",
            params={"s": query},
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        # Extract only the information we need
        meals = []

        for meal in data.get("meals") or []:
            meals.append({
                "mealDbId": meal["idMeal"],
                "name": meal["strMeal"],
                "imageUrl": meal["strMealThumb"]
            })

        return jsonify(meals), 200

    except (requests.RequestException, ValueError):
        app.logger.exception("TheMealDB search failed")

        return jsonify({
            "error": "Unable to search meals right now"
        }), 502


if __name__ == "__main__":
    app.run(debug=True, port=5000)
