from flask import Flask, request, jsonify, send_from_directory
from sentence_transformers import SentenceTransformer
from endee_client import EndeeClient
import json
import os

app = Flask(__name__, static_folder="../frontend")

# Serve frontend at root
@app.route("/")
def index():
    return send_from_directory("../frontend", "index.html")

# Load model, client, and doc map
# Load model, client, and doc map
print("Loading resources...")
model = SentenceTransformer("all-MiniLM-L6-v2")
endee_host = os.getenv("ENDEE_HOST", "localhost")
client = EndeeClient(base_url=f"http://{endee_host}:8080/api/v1")
COLLECTION_NAME = "semantic_docs"
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # Get directory of app.py
DOC_MAP_FILE = os.path.join(BASE_DIR, "doc_map.json")
doc_map = {}

# Load document mapping if exists
if os.path.exists(DOC_MAP_FILE):
    with open(DOC_MAP_FILE, "r") as f:
        doc_map = json.load(f)
    print(f"Loaded {len(doc_map)} documents from map.")
else:
    print(f"Warning: Doc map not found at {DOC_MAP_FILE}")

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/api/search", methods=["POST"])
def search():
    data = request.json
    query = data.get("query", "")
    if not query:
        return jsonify({"error": "Query required"}), 400

    # Vectorize query
    vector = model.encode(query).tolist()

    # Search Endee
    # Returns list of matches, likely: [[id, distance], ...] or list of structs
    # MsgPack unpack usually returns generic types.
    results = client.search(COLLECTION_NAME, vector, top_k=5)
    
    formatted_results = []
    
    # Endee MessagePack result structure (ResultSet):
    # Typically struct { vector_results: ..., id_results: ... } or just list of items
    # We need to adapt based on what `unpackb` returns.
    # Assuming result is a list of results (or similar).
    # Since we can't test, we'll write robust handling:
    
    # If results is list of items
    try:
        # Check if results is a dict (ResultSet) or list
        items = []
        if isinstance(results, dict):
            # Maybe it has 'results' key?
             items = results.get("results", [])
        elif isinstance(results, list):
            items = results
            
        for item in items:
            # Item might be tuple (id, score) or dict
            doc_id = None
            score = 0.0
            
            # MessagePack might unpack to list/tuple [id, score]
            # Debugging shows Endee likely returns [distance, id] based on the screenshot behavior.
            # item[0] was 0.46.. (distance), item[1] was 1.00 (id)
            
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                # Endee typically returns [similarity, id]
                raw_score = item[0]
                raw_id = item[1]
                
                doc_id = str(int(raw_id)) 
                # Scores are already similarities (0.0 to 1.0)
                score = float(raw_score)
            elif isinstance(item, dict):
                doc_id = str(item.get('id'))
                score = float(item.get('similarity', item.get('distance', 0)))
            else:
                 doc_id = None
                 score = 0.0
            
            text_content = doc_map.get(doc_id, f"Document ID: {doc_id}")
            
            formatted_results.append({
                "score": score,
                "text": text_content,
                "id": doc_id
            })

    except Exception as e:
        print(f"Error parsing results: {e}")
        # Return raw for debugging if parse fails
        formatted_results = [{"text": f"Raw Result Error: {str(e)}", "raw": str(results)}]

    return jsonify({"results": formatted_results})

@app.route("/api/recommend", methods=["POST"])
def recommend():
    data = request.json
    doc_id = data.get("id")
    
    if not doc_id:
        return jsonify({"error": "Document ID required"}), 400

    # 1. Get Vector for the document
    vec_obj = client.get_vector(COLLECTION_NAME, doc_id)
    
    if not vec_obj:
         return jsonify({"error": "Document not found"}), 404

    # Extract vector from Endee response
    query_vector = []
    if isinstance(vec_obj, dict) and 'vector' in vec_obj:
        query_vector = vec_obj['vector']
        
    elif isinstance(vec_obj, (list, tuple)):
        # MessagePack response structure based on debug:
        # ['1', b'', '', 0, [VECTOR]] -> Vector is at index 4
        if len(vec_obj) > 4 and isinstance(vec_obj[4], list):
             query_vector = vec_obj[4]
        # Fallback for search result items (id, distance)
        elif len(vec_obj) >= 2 and isinstance(vec_obj[1], list): 
             query_vector = vec_obj[1]
        
        # Fallback search in list
        if not query_vector:
             for item in vec_obj:
                  if isinstance(item, list) and len(item) > 10: # Vector dim check
                       query_vector = item
                       break
    else:
        # Fallback for single vector object
        if isinstance(vec_obj, list) and len(vec_obj) > 100: 
            query_vector = vec_obj

    if not query_vector:
        return jsonify({"error": "Could not extract vector from document"}), 500

    # 2. Search for similar (get k+1 to exclude self)
    results = client.search(COLLECTION_NAME, query_vector, top_k=6)
    
    formatted_results = []
    try:
        items = []
        if isinstance(results, dict):
             items = results.get("results", [])
        elif isinstance(results, list):
            items = results
            
        for item in items:
            d_id = None
            score = 0.0
            
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                # Endee typically returns [similarity, id]
                d_id = str(int(item[1]))
                score = float(item[0])
            elif isinstance(item, dict):
                d_id = str(item.get('id'))
                score = float(item.get('similarity', item.get('distance', 0)))
            
            # Filter out self
            if d_id == str(doc_id): 
                continue
                
            text_content = doc_map.get(d_id, f"Document ID: {d_id}")
            
            formatted_results.append({
                "score": score,
                "text": text_content,
                "id": d_id
            })

    except Exception as e:
        print(f"Error parsing recommend results: {e}")

    return jsonify({"results": formatted_results})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
