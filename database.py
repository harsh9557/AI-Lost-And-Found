"""Database layer for AI Lost & Found. SQLite, parameterized queries, safe password hashing."""
import hashlib
import hmac
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_NAME = os.environ.get("LOST_FOUND_DB", str(BASE_DIR / "lost_found.db"))
PBKDF2_ROUNDS = 310_000


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_NAME, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def now_text():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    """Accept modern PBKDF2 hashes and legacy SHA-256 hashes; caller upgrades legacy hashes."""
    if not stored:
        return False
    if stored.startswith("pbkdf2_sha256$"):
        try:
            _, rounds, salt_hex, digest_hex = stored.split("$", 3)
            digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds))
            return hmac.compare_digest(digest.hex(), digest_hex)
        except (ValueError, TypeError):
            return False
    # Backward compatibility with the old unsalted SHA-256 format.
    legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy, stored)


def create_database():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type TEXT NOT NULL CHECK(item_type IN ('Lost','Found')),
            item_name TEXT NOT NULL,
            description TEXT DEFAULT '',
            color TEXT DEFAULT '',
            location TEXT DEFAULT '',
            photo TEXT DEFAULT '',
            uploaded_at TEXT,
            user_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Active',
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            lost_id INTEGER NOT NULL,
            found_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            match_score REAL DEFAULT 0,
            created_at TEXT,
            is_read INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, lost_id, found_id)
        );
        CREATE TABLE IF NOT EXISTS claim_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT
        );
        """)
        # Add missing columns to databases created by earlier versions.
        for table, column, definition in [
            ("users", "is_admin", "INTEGER NOT NULL DEFAULT 0"),
            ("users", "created_at", "TEXT"),
            ("items", "uploaded_at", "TEXT"),
            ("items", "user_id", "INTEGER"),
            ("items", "status", "TEXT DEFAULT 'Active'"),
        ]:
            cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            if column not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        # Fill safe defaults for old rows.
        conn.execute("UPDATE items SET status='Active' WHERE status IS NULL OR status='' ")
        conn.execute("UPDATE items SET uploaded_at=? WHERE uploaded_at IS NULL", (now_text(),))
        conn.execute("UPDATE users SET created_at=? WHERE created_at IS NULL", (now_text(),))
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_type_status ON items(item_type, status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_user ON items(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_claim_receiver ON claim_requests(receiver_id, status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_claim ON chat_messages(claim_id, id)")


def create_user(name, username, password):
    name, username = name.strip(), username.strip()
    if len(name) < 2 or len(username) < 3:
        return False, "Name must be at least 2 characters and username at least 3 characters."
    if len(password) < 8:
        return False, "Password must contain at least 8 characters."
    try:
        with get_connection() as conn:
            conn.execute("INSERT INTO users(name, username, password, is_admin, created_at) VALUES(?,?,?,?,?)",
                         (name, username, hash_password(password), 0, now_text()))
        return True, "Account created successfully. Please log in."
    except sqlite3.IntegrityError:
        return False, "Username already exists. Choose another username."


def login_user(username, password):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE", (username.strip(),)).fetchone()
        if not row or not verify_password(password, row["password"]):
            return None
        if not row["password"].startswith("pbkdf2_sha256$"):
            conn.execute("UPDATE users SET password=? WHERE id=?", (hash_password(password), row["id"]))
        return (row["id"], row["name"], row["username"], row["is_admin"])


def add_item(item_type, item_name, description, color, location, photo, user_id):
    with get_connection() as conn:
        cur = conn.execute("""INSERT INTO items(item_type,item_name,description,color,location,photo,uploaded_at,user_id,status)
            VALUES(?,?,?,?,?,?,?,?, 'Active')""",
            (item_type, item_name.strip(), description.strip(), color.strip(), location.strip(), photo or "", now_text(), user_id))
        return cur.lastrowid


def get_item(item_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
        return dict(row) if row else None


def get_items(item_type=None, status=None, user_id=None, limit=500):
    sql, params, clauses = "SELECT i.*, u.name AS reporter_name FROM items i LEFT JOIN users u ON u.id=i.user_id", [], []
    if item_type:
        clauses.append("i.item_type=?"); params.append(item_type)
    if status:
        clauses.append("i.status=?"); params.append(status)
    if user_id is not None:
        clauses.append("i.user_id=?"); params.append(user_id)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY i.id DESC LIMIT ?"; params.append(int(limit))
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def add_notification(user_id, lost_id, found_id, message, match_score):
    with get_connection() as conn:
        conn.execute("""INSERT OR IGNORE INTO notifications(user_id,lost_id,found_id,message,match_score,created_at,is_read)
            VALUES(?,?,?,?,?,?,0)""", (user_id, lost_id, found_id, message, float(match_score), now_text()))


def get_notifications(user_id):
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 100", (user_id,)).fetchall()]


def get_unread_count(user_id):
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0", (user_id,)).fetchone()[0]


def mark_all_read(user_id):
    with get_connection() as conn:
        conn.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user_id,))


def create_claim_request(item_id, sender_id, receiver_id, message):
    if sender_id == receiver_id:
        return False, "You cannot send a claim request to yourself."
    with get_connection() as conn:
        item = conn.execute("SELECT user_id,item_type,status FROM items WHERE id=?", (item_id,)).fetchone()
        if not item or item["item_type"] != "Found" or item["status"] != "Active":
            return False, "This found item is no longer available."
        if item["user_id"] != receiver_id:
            return False, "The item owner could not be verified. Refresh and try again."
        exists = conn.execute("SELECT 1 FROM claim_requests WHERE item_id=? AND sender_id=? AND status='Pending'", (item_id, sender_id)).fetchone()
        if exists:
            return False, "You already have a pending request for this item."
        conn.execute("INSERT INTO claim_requests(item_id,sender_id,receiver_id,message,status,created_at) VALUES(?,?,?,?,?,?)",
                     (item_id, sender_id, receiver_id, message.strip(), "Pending", now_text()))
    return True, "Claim request sent."


def get_received_claims(user_id):
    with get_connection() as conn:
        return [tuple(r) for r in conn.execute("""SELECT c.id,c.item_id,c.sender_id,c.message,c.status,c.created_at,
            i.item_name,i.item_type,u.name FROM claim_requests c JOIN items i ON i.id=c.item_id JOIN users u ON u.id=c.sender_id
            WHERE c.receiver_id=? ORDER BY c.id DESC""", (user_id,)).fetchall()]


def get_sent_claims(user_id):
    with get_connection() as conn:
        return [tuple(r) for r in conn.execute("""SELECT c.id,c.item_id,c.message,c.status,c.created_at,i.item_name,u.name
            FROM claim_requests c JOIN items i ON i.id=c.item_id JOIN users u ON u.id=c.receiver_id
            WHERE c.sender_id=? ORDER BY c.id DESC""", (user_id,)).fetchall()]


def get_claim_receiver(claim_id):
    with get_connection() as conn:
        r = conn.execute("SELECT sender_id,receiver_id,item_id,status FROM claim_requests WHERE id=?", (claim_id,)).fetchone()
        return tuple(r) if r else None


def update_claim_status(claim_id, status, acting_user_id=None):
    if status not in {"Pending", "Accepted", "Rejected"}:
        return False
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM claim_requests WHERE id=?", (claim_id,)).fetchone()
        if not row or (acting_user_id is not None and row["receiver_id"] != acting_user_id):
            return False
        conn.execute("UPDATE claim_requests SET status=? WHERE id=?", (status, claim_id))
        if status == "Accepted":
            conn.execute("UPDATE items SET status='Claimed' WHERE id=? AND user_id=?", (row["item_id"], row["receiver_id"]))
    return True


def update_item_status(item_id, status, user_id=None):
    allowed = {"Active", "Claimed", "Closed"}
    if status not in allowed:
        return False
    with get_connection() as conn:
        if user_id is None:
            cur = conn.execute("UPDATE items SET status=? WHERE id=?", (status, item_id))
        else:
            cur = conn.execute("UPDATE items SET status=? WHERE id=? AND user_id=?", (status, item_id, user_id))
        return cur.rowcount > 0


def delete_item(item_id, user_id=None):
    with get_connection() as conn:
        row = conn.execute("SELECT photo FROM items WHERE id=?", (item_id,)).fetchone()
        if not row:
            return None
        if user_id is None:
            conn.execute("DELETE FROM items WHERE id=?", (item_id,))
        else:
            cur = conn.execute("DELETE FROM items WHERE id=? AND user_id=?", (item_id, user_id))
            if cur.rowcount == 0:
                return None
        conn.execute("DELETE FROM notifications WHERE lost_id=? OR found_id=?", (item_id, item_id))
        conn.execute("DELETE FROM claim_requests WHERE item_id=?", (item_id,))
        return row["photo"] or ""


def send_chat_message(claim_id, sender_id, receiver_id, message):
    message = message.strip()
    if not message or len(message) > 2000:
        return False
    with get_connection() as conn:
        claim = conn.execute("SELECT sender_id,receiver_id,status FROM claim_requests WHERE id=?", (claim_id,)).fetchone()
        if not claim or claim["status"] != "Accepted" or sender_id not in (claim["sender_id"], claim["receiver_id"]):
            return False
        expected_receiver = claim["receiver_id"] if sender_id == claim["sender_id"] else claim["sender_id"]
        if receiver_id != expected_receiver:
            return False
        conn.execute("INSERT INTO chat_messages(claim_id,sender_id,receiver_id,message,created_at) VALUES(?,?,?,?,?)",
                     (claim_id, sender_id, receiver_id, message, now_text()))
        return True


def get_chat_messages(claim_id, user_id):
    with get_connection() as conn:
        claim = conn.execute("SELECT sender_id,receiver_id,status FROM claim_requests WHERE id=?", (claim_id,)).fetchone()
        if not claim or user_id not in (claim["sender_id"], claim["receiver_id"]):
            return []
        return [tuple(r) for r in conn.execute("""SELECT m.id,m.sender_id,u.name,m.message,m.created_at FROM chat_messages m
            JOIN users u ON u.id=m.sender_id WHERE m.claim_id=? ORDER BY m.id ASC""", (claim_id,)).fetchall()]


def get_accepted_chats(user_id):
    with get_connection() as conn:
        return [tuple(r) for r in conn.execute("""SELECT c.id,c.item_id,c.sender_id,c.receiver_id,c.message,c.created_at,
            i.item_name,u1.name,u2.name FROM claim_requests c JOIN items i ON i.id=c.item_id
            JOIN users u1 ON u1.id=c.sender_id JOIN users u2 ON u2.id=c.receiver_id
            WHERE c.status='Accepted' AND (c.sender_id=? OR c.receiver_id=?) ORDER BY c.id DESC""", (user_id,user_id)).fetchall()]


def get_dashboard_stats():
    with get_connection() as conn:
        return {
            "lost": conn.execute("SELECT COUNT(*) FROM items WHERE item_type='Lost'").fetchone()[0],
            "found": conn.execute("SELECT COUNT(*) FROM items WHERE item_type='Found'").fetchone()[0],
            "active": conn.execute("SELECT COUNT(*) FROM items WHERE status='Active'").fetchone()[0],
            "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "claimed": conn.execute("SELECT COUNT(*) FROM items WHERE status='Claimed'").fetchone()[0],
        }


def get_all_users():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT id,name,username,is_admin,created_at FROM users ORDER BY id").fetchall()]


def make_admin(username):
    with get_connection() as conn:
        cur = conn.execute("UPDATE users SET is_admin=1 WHERE username=? COLLATE NOCASE", (username.strip(),))
        return cur.rowcount > 0
