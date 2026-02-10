"""OphthalmoCapture — Database Layer (Metadata Only)

Option B: The database persists annotation metadata (labels, transcriptions,
doctor info, timestamps) for audit and history.  It NEVER stores images or audio.
"""

import os
import datetime
import sqlite3

# Try importing firebase_admin
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

DB_TYPE = "SQLITE"
# Use /tmp for writable storage in Docker (ephemeral but always writable).
# Locally, falls back to the script's own directory.
_DB_DIR = "/tmp" if os.path.isdir("/tmp") else os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(_DB_DIR, "annotations.db")
db_ref = None


def init_db():
    """Initialize the database connection (Firebase or SQLite fallback)."""
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
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_filename TEXT NOT NULL,
            label TEXT,
            transcription TEXT,
            doctor_name TEXT DEFAULT '',
            created_at DATETIME
        )''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_ann_filename
                      ON annotations (image_filename)''')
        # Migration: add session_id column if it doesn't exist yet
        try:
            c.execute("ALTER TABLE annotations ADD COLUMN session_id TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # column already exists
        # Migration: add locs_data column (JSON string)
        try:
            c.execute("ALTER TABLE annotations ADD COLUMN locs_data TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # column already exists
        c.execute('''CREATE INDEX IF NOT EXISTS idx_ann_session
                      ON annotations (image_filename, session_id)''')
        conn.commit()
        conn.close()
        DB_TYPE = "SQLITE"
        return "SQLITE"
    except Exception as e:
        raise Exception(f"Database initialization failed: {e}")


def save_annotation(image_filename, label, transcription, doctor_name=""):
    """Save an annotation record (always INSERT).  Stores metadata only."""
    timestamp = datetime.datetime.now()

    if DB_TYPE == "FIREBASE":
        db_ref.collection("annotations").add({
            "imageFilename": image_filename,
            "label": label,
            "transcription": transcription,
            "doctorName": doctor_name,
            "createdAt": timestamp,
        })
    else:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute(
            "INSERT INTO annotations "
            "(image_filename, label, transcription, doctor_name, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (image_filename, label, transcription, doctor_name, timestamp),
        )
        conn.commit()
        conn.close()


def save_or_update_annotation(
    image_filename, label, transcription, doctor_name="", session_id="",
    locs_data=None,
):
    """Upsert: within the same session, keep only ONE record per image.

    If a record for (image_filename, session_id) already exists → UPDATE it.
    Otherwise → INSERT a new one.
    """
    import json as _json
    timestamp = datetime.datetime.now()
    locs_json = _json.dumps(locs_data or {}, ensure_ascii=False)

    if DB_TYPE == "FIREBASE":
        # Query for existing doc with matching filename + session
        docs = list(
            db_ref.collection("annotations")
            .where("imageFilename", "==", image_filename)
            .where("sessionId", "==", session_id)
            .limit(1)
            .stream()
        )
        if docs:
            docs[0].reference.update({
                "label": label,
                "transcription": transcription,
                "doctorName": doctor_name,
                "locsData": locs_data or {},
                "createdAt": timestamp,
            })
        else:
            db_ref.collection("annotations").add({
                "imageFilename": image_filename,
                "label": label,
                "transcription": transcription,
                "doctorName": doctor_name,
                "sessionId": session_id,
                "locsData": locs_data or {},
                "createdAt": timestamp,
            })
    else:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        # Check if a row for this image+session already exists
        c.execute(
            "SELECT id FROM annotations "
            "WHERE image_filename = ? AND session_id = ? LIMIT 1",
            (image_filename, session_id),
        )
        row = c.fetchone()
        if row:
            c.execute(
                "UPDATE annotations "
                "SET label = ?, transcription = ?, doctor_name = ?, "
                "created_at = ?, locs_data = ? "
                "WHERE id = ?",
                (label, transcription, doctor_name, timestamp, locs_json, row[0]),
            )
        else:
            c.execute(
                "INSERT INTO annotations "
                "(image_filename, label, transcription, doctor_name, "
                "created_at, session_id, locs_data) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (image_filename, label, transcription, doctor_name,
                 timestamp, session_id, locs_json),
            )
        conn.commit()
        conn.close()


def get_latest_annotation(image_filename):
    """Retrieve the most recent annotation for a given image filename."""
    if DB_TYPE == "FIREBASE":
        docs = (
            db_ref.collection("annotations")
            .where("imageFilename", "==", image_filename)
            .order_by("createdAt", direction=firestore.Query.DESCENDING)
            .limit(1)
            .stream()
        )
        for doc in docs:
            return doc.to_dict()
        return None
    else:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute(
            "SELECT image_filename, label, transcription, doctor_name, created_at "
            "FROM annotations WHERE image_filename = ? ORDER BY id DESC LIMIT 1",
            (image_filename,),
        )
        row = c.fetchone()
        conn.close()
        if row:
            return {
                "imageFilename": row[0],
                "label": row[1],
                "transcription": row[2],
                "doctorName": row[3],
                "createdAt": row[4],
            }
        return None


def get_history_paginated(search_query="", page=1, per_page=10):
    """Retrieve annotation history with search and pagination.

    Returns: (list_of_items, total_count)
    """
    offset = (page - 1) * per_page
    history = []
    total_count = 0

    if DB_TYPE == "FIREBASE":
        ref = db_ref.collection("annotations")
        if search_query:
            query = (
                ref.where("imageFilename", ">=", search_query)
                .where("imageFilename", "<=", search_query + "\uf8ff")
            )
        else:
            query = ref.order_by("createdAt", direction=firestore.Query.DESCENDING)

        all_docs = list(query.stream())
        total_count = len(all_docs)
        for doc in all_docs[offset : offset + per_page]:
            history.append(doc.to_dict())

    else:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()

        # Count
        if search_query:
            c.execute(
                "SELECT COUNT(*) FROM annotations WHERE image_filename LIKE ?",
                (f"%{search_query}%",),
            )
        else:
            c.execute("SELECT COUNT(*) FROM annotations")
        total_count = c.fetchone()[0]

        # Fetch page
        sql = (
            "SELECT image_filename, label, transcription, doctor_name, created_at "
            "FROM annotations"
        )
        params = []
        if search_query:
            sql += " WHERE image_filename LIKE ?"
            params.append(f"%{search_query}%")
        sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])

        c.execute(sql, params)
        for row in c.fetchall():
            history.append({
                "imageFilename": row[0],
                "label": row[1],
                "transcription": row[2],
                "doctorName": row[3],
                "createdAt": row[4],
            })
        conn.close()

    return history, total_count


def get_annotation_stats():
    """Get summary statistics of all stored annotations."""
    if DB_TYPE == "FIREBASE":
        docs = list(db_ref.collection("annotations").stream())
        total = len(docs)
        labels = {}
        for doc in docs:
            lbl = doc.to_dict().get("label", "sin_etiqueta")
            labels[lbl] = labels.get(lbl, 0) + 1
        return {"total": total, "by_label": labels}
    else:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM annotations")
        total = c.fetchone()[0]
        c.execute("SELECT label, COUNT(*) FROM annotations GROUP BY label")
        labels = {row[0]: row[1] for row in c.fetchall()}
        conn.close()
        return {"total": total, "by_label": labels}


def get_previously_labeled_filenames(filenames: list[str]) -> dict[str, list[dict]]:
    """Check which filenames have been previously annotated in the DB.

    Returns a dict mapping filename → list of annotation records.
    Only filenames with at least one record are included.
    """
    if not filenames:
        return {}

    result = {}

    if DB_TYPE == "FIREBASE":
        # Firestore doesn't support 'IN' with >30 items, so batch
        for fname in filenames:
            docs = (
                db_ref.collection("annotations")
                .where("imageFilename", "==", fname)
                .order_by("createdAt", direction=firestore.Query.DESCENDING)
                .stream()
            )
            records = [doc.to_dict() for doc in docs]
            if records:
                result[fname] = records
    else:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        placeholders = ",".join("?" for _ in filenames)
        c.execute(
            f"SELECT image_filename, label, transcription, doctor_name, created_at "
            f"FROM annotations WHERE image_filename IN ({placeholders}) "
            f"ORDER BY created_at DESC",
            filenames,
        )
        for row in c.fetchall():
            fname = row[0]
            record = {
                "imageFilename": row[0],
                "label": row[1],
                "transcription": row[2],
                "doctorName": row[3],
                "createdAt": row[4],
            }
            result.setdefault(fname, []).append(record)
        conn.close()

    return result


def get_all_annotations_for_file(image_filename: str) -> list[dict]:
    """Retrieve ALL annotations for a given image filename, ordered by date desc."""
    if DB_TYPE == "FIREBASE":
        docs = (
            db_ref.collection("annotations")
            .where("imageFilename", "==", image_filename)
            .order_by("createdAt", direction=firestore.Query.DESCENDING)
            .stream()
        )
        return [doc.to_dict() for doc in docs]
    else:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute(
            "SELECT image_filename, label, transcription, doctor_name, created_at "
            "FROM annotations WHERE image_filename = ? ORDER BY created_at DESC",
            (image_filename,),
        )
        results = []
        for row in c.fetchall():
            results.append({
                "imageFilename": row[0],
                "label": row[1],
                "transcription": row[2],
                "doctorName": row[3],
                "createdAt": row[4],
            })
        conn.close()
        return results


def get_history_grouped(search_query="", page=1, per_page=10):
    """Retrieve annotation history GROUPED by image filename.

    Returns: (list_of_groups, total_unique_images)
    Each group = {"imageFilename": str, "annotations": [list of records]}
    sorted by most recent annotation date per image.
    """
    offset = (page - 1) * per_page

    if DB_TYPE == "FIREBASE":
        ref = db_ref.collection("annotations")
        if search_query:
            query = (
                ref.where("imageFilename", ">=", search_query)
                .where("imageFilename", "<=", search_query + "\uf8ff")
            )
        else:
            query = ref.order_by("createdAt", direction=firestore.Query.DESCENDING)

        all_docs = [doc.to_dict() for doc in query.stream()]

        # Group by filename
        grouped = {}
        for doc in all_docs:
            fname = doc.get("imageFilename", "")
            grouped.setdefault(fname, []).append(doc)

        # Sort groups by most recent annotation
        sorted_groups = sorted(
            grouped.items(),
            key=lambda x: max(str(a.get("createdAt", "")) for a in x[1]),
            reverse=True,
        )

        total_unique = len(sorted_groups)
        page_groups = sorted_groups[offset:offset + per_page]

        result = []
        for fname, annotations in page_groups:
            result.append({
                "imageFilename": fname,
                "annotations": sorted(
                    annotations,
                    key=lambda a: str(a.get("createdAt", "")),
                    reverse=True,
                ),
            })

        return result, total_unique
    else:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()

        # Count unique filenames
        where = ""
        params = []
        if search_query:
            where = " WHERE image_filename LIKE ?"
            params.append(f"%{search_query}%")

        c.execute(
            f"SELECT COUNT(DISTINCT image_filename) FROM annotations{where}",
            params,
        )
        total_unique = c.fetchone()[0]

        # Get unique filenames for this page, sorted by most recent
        c.execute(
            f"SELECT image_filename, MAX(created_at) as latest "
            f"FROM annotations{where} "
            f"GROUP BY image_filename ORDER BY latest DESC "
            f"LIMIT ? OFFSET ?",
            params + [per_page, offset],
        )
        page_filenames = [row[0] for row in c.fetchall()]

        # Fetch all annotations for those filenames
        result = []
        for fname in page_filenames:
            c.execute(
                "SELECT image_filename, label, transcription, doctor_name, created_at "
                "FROM annotations WHERE image_filename = ? ORDER BY created_at DESC",
                (fname,),
            )
            annotations = []
            for row in c.fetchall():
                annotations.append({
                    "imageFilename": row[0],
                    "label": row[1],
                    "transcription": row[2],
                    "doctorName": row[3],
                    "createdAt": row[4],
                })
            result.append({
                "imageFilename": fname,
                "annotations": annotations,
            })

        conn.close()
        return result, total_unique
