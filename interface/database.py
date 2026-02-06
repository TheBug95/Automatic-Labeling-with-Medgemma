import os
import datetime
import sqlite3
import math

# Try importing firebase_admin
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

DB_TYPE = "SQLITE"
db_ref = None

def init_db():
    """Initializes the database connection (Firebase or SQLite)."""
    global DB_TYPE, db_ref
    
    # Try Firebase first
    if FIREBASE_AVAILABLE and os.path.exists("serviceAccountKey.json"):
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate("serviceAccountKey.json")
                firebase_admin.initialize_app(cred)
            db_ref = firestore.client()
            DB_TYPE = "FIREBASE"
            return "FIREBASE"
        except Exception as e:
            print(f"Firebase init failed: {e}")

    # Fallback to SQLite
    try:
        conn = sqlite3.connect('local_diagnoses.db', check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS diagnoses
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      image_id TEXT, 
                      diagnosis_text TEXT, 
                      timestamp DATETIME)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_image_id ON diagnoses (image_id)''')
        conn.commit()
        conn.close()
        DB_TYPE = "SQLITE"
        return "SQLITE"
    except Exception as e:
        raise Exception(f"Database initialization failed: {e}")

def save_diagnosis(image_id, text, doctor_name="LocalUser"):
    """Saves the diagnosis to the active database."""
    timestamp = datetime.datetime.now()
    
    if DB_TYPE == "FIREBASE":
        db_ref.collection("ophthalmo_diagnoses").add({
            "imageId": image_id,
            "diagnosisText": text,
            "createdAt": timestamp,
            "doctor": doctor_name
        })
    else:
        conn = sqlite3.connect('local_diagnoses.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT INTO diagnoses (image_id, diagnosis_text, timestamp) VALUES (?, ?, ?)",
                  (image_id, text, timestamp))
        conn.commit()
        conn.close()

def get_latest_diagnosis(image_id):
    """Retrieves the most recent diagnosis for a specific image ID."""
    if DB_TYPE == "FIREBASE":
        docs = db_ref.collection("ophthalmo_diagnoses")\
            .where("imageId", "==", image_id)\
            .order_by("createdAt", direction=firestore.Query.DESCENDING)\
            .limit(1)\
            .stream()
        for doc in docs:
            return doc.to_dict().get("diagnosisText", "")
    else:
        conn = sqlite3.connect('local_diagnoses.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT diagnosis_text FROM diagnoses WHERE image_id = ? ORDER BY id DESC LIMIT 1", (image_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return row[0]
    return ""

def get_history_paginated(search_query="", page=1, per_page=10):
    """
    Retrieves history with search filtering and pagination.
    Returns: (list_of_items, total_count)
    """
    offset = (page - 1) * per_page
    history = []
    total_count = 0
    
    if DB_TYPE == "FIREBASE":
        ref = db_ref.collection("ophthalmo_diagnoses")
        if search_query:
            # Prefix search hack for Firestore
            query = ref.where("imageId", ">=", search_query)\
                       .where("imageId", "<=", search_query + '\uf8ff')
        else:
            query = ref.order_by("createdAt", direction=firestore.Query.DESCENDING)
        
        all_docs = list(query.stream())
        total_count = len(all_docs)
        
        # In-memory pagination for Firebase
        start = offset
        end = offset + per_page
        for doc in all_docs[start:end]:
            history.append(doc.to_dict())

    else:
        # SQLite Implementation
        conn = sqlite3.connect('local_diagnoses.db', check_same_thread=False)
        c = conn.cursor()
        
        # 1. Count
        if search_query:
            c.execute("SELECT COUNT(*) FROM diagnoses WHERE image_id LIKE ?", (f"%{search_query}%",))
        else:
            c.execute("SELECT COUNT(*) FROM diagnoses")
        total_count = c.fetchone()[0]
        
        # 2. Fetch
        query_sql = "SELECT image_id, diagnosis_text, timestamp FROM diagnoses"
        params = []
        
        if search_query:
            query_sql += " WHERE image_id LIKE ?"
            params.append(f"%{search_query}%")
            
        query_sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        
        c.execute(query_sql, params)
        rows = c.fetchall()
        for row in rows:
            history.append({
                "imageId": row[0],
                "diagnosisText": row[1],
                "createdAt": row[2]
            })
        conn.close()
        
    return history, total_count

def get_last_active_image_id():
    """Retrieves the image_id of the most recently saved diagnosis."""
    if DB_TYPE == "FIREBASE":
        docs = db_ref.collection("ophthalmo_diagnoses")\
            .order_by("createdAt", direction=firestore.Query.DESCENDING)\
            .limit(1)\
            .stream()
        for doc in docs:
            return doc.to_dict().get("imageId")
    else:
        conn = sqlite3.connect('local_diagnoses.db', check_same_thread=False)
        c = conn.cursor()
        # Fetch the most recent entry based on timestamp (or ID if timestamp is unreliable)
        c.execute("SELECT image_id FROM diagnoses ORDER BY timestamp DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        if row:
            return row[0]
    return None