from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from engine import AnimeEngine

CLIENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "client"))
app = Flask(__name__, static_folder=CLIENT_DIR)
CORS(app)

print("Starting Anime Recommendation Engine...")
engine = AnimeEngine()

@app.route("/")
def serve_index():
    return send_from_directory(CLIENT_DIR, "index.html")

@app.route("/<path:path>")
def serve_static(path):
    target = os.path.join(CLIENT_DIR, path)
    if os.path.exists(target):
        return send_from_directory(CLIENT_DIR, path)
    return send_from_directory(CLIENT_DIR, "index.html")

@app.route("/api/options", methods=["GET"])
def get_options():
    try:
        options = engine.get_options()
        return jsonify({"status": "success", "data": options})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/autocomplete", methods=["GET"])
def autocomplete():
    query = request.args.get("q", "")
    limit = int(request.args.get("limit", 10))
    results = engine.autocomplete_titles(query, limit=limit)
    return jsonify({"status": "success", "results": results})

@app.route("/api/search", methods=["GET"])
def search_by_title():
    title = request.args.get("title", "").strip()
    top_n = int(request.args.get("top_n", 100))
    if not title:
        return jsonify({"status": "error", "message": "Title parameter is required."}), 400
    
    response = engine.recommend_by_title(title, top_n=top_n)
    return jsonify(response)

@app.route("/api/filter", methods=["POST"])
def apply_filters():
    data = request.json or {}
    genres = data.get("genres", [])
    types = data.get("types", [])
    studios = data.get("studios", [])
    ratings = data.get("ratings", [])
    top_n = int(data.get("top_n", 100))

    response = engine.hybrid_metadata_recommend(
        genres=genres,
        type_name=types,
        studios=studios,
        rating=ratings,
        top_n=top_n
    )
    return jsonify(response)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Server running at http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
