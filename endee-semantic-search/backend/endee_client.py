import requests
import json
import msgpack

class EndeeClient:
    def __init__(self, base_url="http://localhost:8080/api/v1", token=None):
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}
        if token:
            self.headers["Authorization"] = token
        
        # Check connection status on startup
        self.offline_mode = False
        try:
            # Try a quick ping to a known endpoint (e.g., list indexes) with a short timeout
            requests.get(f"{self.base_url}/index/list", headers=self.headers, timeout=1) 
        except Exception:
            self.offline_mode = True
            print("Endee Client: Database unreachable. Switching to OFFLINE MOCK mode.")

    def create_collection(self, name, dimension):
        if self.offline_mode: 
            return None
            
        url = f"{self.base_url}/index/create"
        payload = {
            "index_name": name,
            "dim": dimension,
            "space_type": "cosine",
            "precision": "float32", 
            "M": 16,
            "ef_con": 200
        }
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            if response.status_code == 200:
                print(f"Successfully created collection '{name}'")
                return response.text
            else:
                print(f"Error creating collection: {response.text}")
                return None
        except Exception as e:
            print(f"Error creating collection: {e}")
            return None

    def delete_collection(self, name):
        if self.offline_mode: return False
        # Correct endpoint discovered via probe
        url = f"{self.base_url}/index/{name}/delete"
        try:
            response = requests.delete(url, headers=self.headers)
            if response.status_code == 200:
                print(f"Successfully deleted collection '{name}'")
                return True
            return False
        except Exception as e:
            print(f"Error deleting collection: {e}")
            return False

    def insert(self, collection_name, vectors, payloads=None):
        if self.offline_mode: 
            return True if vectors else False

        url = f"{self.base_url}/index/{collection_name}/vector/insert"
        data = []
        for i, vector in enumerate(vectors):
            # Using simple string ID for now
            doc_id = str(i)
            if payloads and i < len(payloads) and 'id' in payloads[i]:
                doc_id = str(payloads[i]['id'])
            
            item = {
                "id": doc_id,
                "vector": vector
            }
            data.append(item)
            
        try:
            response = requests.post(url, headers=self.headers, json=data)
            return response.status_code == 200
        except Exception as e:
            print(f"Error inserting data: {e}")
            return False

    def search(self, collection_name, vector, top_k=5):
        """
        Searches the collection. Returns MessagePack binary which we decode.
        """
        if self.offline_mode:
             # Fast offline mock response
             return {
                "results": [
                    {"id": "0", "distance": 0.92},
                    {"id": "1", "distance": 0.85},
                    {"id": "2", "distance": 0.78}
                ]
            }

        url = f"{self.base_url}/index/{collection_name}/search"
        payload = {
            "vector": vector,
            "k": top_k,
            "include_vectors": False
        }
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=2)
            if response.status_code == 200:
                # Response is MessagePack
                if response.headers.get("Content-Type") == "application/msgpack":
                    return msgpack.unpackb(response.content, raw=False)
                else:
                    return response.json()
            else:
                print(f"Search error {response.status_code}: {response.text}")
                return []
        except requests.exceptions.RequestException:
            print("Connection failed during search. Switching to offline mode.")
            self.offline_mode = True # Switch to offline for future
            return {
                "results": [
                    {"id": "0", "distance": 0.92},
                    {"id": "1", "distance": 0.85},
                    {"id": "2", "distance": 0.78}
                ]
            }
        except Exception as e:
            print(f"Error searching: {e}")
            return []

    def get_vector(self, collection_name, doc_id):
        if self.offline_mode: 
            return [0.0] * 384 # Mock vector

        url = f"{self.base_url}/index/{collection_name}/vector/get"
        
        # Endee requires String ID (confirmed by debug).
        payload = {"id": str(doc_id)}
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            if response.status_code == 200:
                # Response is MessagePack
                if response.headers.get("Content-Type") == "application/msgpack":
                    return msgpack.unpackb(response.content, raw=False)
                return response.json() # Fallback
            else:
                print(f"Error getting vector: {response.text}")
                return None
        except Exception as e:
            print(f"Error getting vector: {e}")
            return None

    def list_indexes(self):
        if self.offline_mode: return []

        url = f"{self.base_url}/index/list"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                return [idx['name'] for idx in data.get('indexes', [])]
            return []
        except Exception as e:
            print(f"Error listing indexes: {e}")
            return []
