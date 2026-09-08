import sqlite3
import hashlib
from datetime import datetime

DB_NAME = "lost_found.db"

# =========================================
# 👑 ADMIN SETTINGS
# =========================================


ADMIN_USERNAME = "harshsaini1811"


# =========================================
# DATABASE CONNECTION
# =========================================

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# =========================================
# PASSWORD HASH
# =========================================

def hash_password(password):
    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


# =========================================
# CREATE DATABASE
# =========================================

def create_database():

    conn = get_connection()
    cursor = conn.cursor()

    # USERS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    """)

    # ITEMS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type TEXT NOT NULL,
            item_name TEXT NOT NULL,
            description TEXT,
            color TEXT,
            location TEXT NOT NULL,
            photo TEXT,
            uploaded_at TEXT,
            user_id INTEGER,
            status TEXT DEFAULT 'Active',
            FOREIGN KEY(user_id)
                REFERENCES users(id)
                ON DELETE SET NULL
        )
    """)

    # =====================================
    # DATABASE MIGRATION
    # =====================================

    cursor.execute("PRAGMA table_info(users)")
    user_columns = {
        row[1]
        for row in cursor.fetchall()
    }

    if "is_admin" not in user_columns:

        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN is_admin INTEGER DEFAULT 0
        """)

    cursor.execute("PRAGMA table_info(items)")
    item_columns = {
        row[1]
        for row in cursor.fetchall()
    }

    if "uploaded_at" not in item_columns:

        cursor.execute("""
            ALTER TABLE items
            ADD COLUMN uploaded_at TEXT
        """)

    if "user_id" not in item_columns:

        cursor.execute("""
            ALTER TABLE items
            ADD COLUMN user_id INTEGER
        """)

    if "status" not in item_columns:

        cursor.execute("""
            ALTER TABLE items
            ADD COLUMN status TEXT DEFAULT 'Active'
        """)

    # =====================================
    # 👑 MAKE FIXED USER ADMIN
    # =====================================

    if ADMIN_USERNAME != "YOUR_USERNAME":

        cursor.execute("""
            UPDATE users
            SET is_admin = 1
            WHERE username = ?
        """, (ADMIN_USERNAME,))

    # =====================================
    # NOTIFICATIONS
    # =====================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            lost_id INTEGER,
            found_id INTEGER,
            message TEXT,
            match_score REAL,
            created_at TEXT,
            is_read INTEGER DEFAULT 0,
            UNIQUE(user_id, lost_id, found_id)
        )
    """)

    # =====================================
    # CLAIM REQUESTS
    # =====================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS claim_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            sender_id INTEGER,
            receiver_id INTEGER,
            message TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TEXT
        )
    """)

    # =====================================
    # CHAT
    # =====================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


# =========================================
# CREATE USER
# =========================================

def create_user(name, username, password):

    name = str(name or "").strip()
    username = str(username or "").strip()

    if not name or not username or not password:

        return False, "All fields are required."

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # 👑 Automatically make fixed username admin
        is_admin = (
            1
            if username == ADMIN_USERNAME
            else 0
        )

        cursor.execute("""
            INSERT INTO users
            (
                name,
                username,
                password,
                is_admin
            )
            VALUES (?, ?, ?, ?)
        """, (
            name,
            username,
            hash_password(password),
            is_admin
        ))

        conn.commit()

        if is_admin:

            return True, "Admin account created successfully!"

        return True, "Account created successfully!"

    except sqlite3.IntegrityError:

        return False, "Username already exists."

    finally:

        conn.close()


# =========================================
# LOGIN
# =========================================

def login_user(username, password):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            username,
            is_admin
        FROM users
        WHERE username = ?
        AND password = ?
    """, (
        username.strip(),
        hash_password(password)
    ))

    user = cursor.fetchone()

    conn.close()

    return user


# =========================================
# ADD ITEM
# =========================================

def add_item(
    item_type,
    item_name,
    description,
    color,
    location,
    photo,
    user_id
):

    item_type = str(item_type or "").strip()
    item_name = str(item_name or "").strip()
    description = str(description or "").strip()
    color = str(color or "").strip()
    location = str(location or "").strip()

    if not item_name or not location:

        return False

    conn = get_connection()
    cursor = conn.cursor()

    uploaded_at = datetime.now().strftime(
        "%d-%m-%Y %I:%M:%S %p"
    )

    cursor.execute("""
        INSERT INTO items
        (
            item_type,
            item_name,
            description,
            color,
            location,
            photo,
            uploaded_at,
            user_id,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item_type,
        item_name,
        description,
        color,
        location,
        photo,
        uploaded_at,
        user_id,
        "Active"
    ))

    conn.commit()
    conn.close()

    return True


# =========================================
# NOTIFICATIONS
# =========================================

def add_notification(
    user_id,
    lost_id,
    found_id,
    message,
    match_score
):

    conn = get_connection()
    cursor = conn.cursor()

    created_at = datetime.now().strftime(
        "%d-%m-%Y %I:%M:%S %p"
    )

    try:

        cursor.execute("""
            INSERT INTO notifications
            (
                user_id,
                lost_id,
                found_id,
                message,
                match_score,
                created_at,
                is_read
            )
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (
            user_id,
            lost_id,
            found_id,
            message,
            match_score,
            created_at
        ))

        conn.commit()

    except sqlite3.IntegrityError:

        pass

    finally:

        conn.close()


def get_notifications(user_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            message,
            match_score,
            created_at,
            is_read
        FROM notifications
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))

    notifications = cursor.fetchall()

    conn.close()

    return notifications


def get_unread_count(user_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM notifications
        WHERE user_id = ?
        AND is_read = 0
    """, (user_id,))

    count = cursor.fetchone()[0]

    conn.close()

    return count


def mark_all_read(user_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = ?
    """, (user_id,))

    conn.commit()
    conn.close()


# =========================================
# CLAIM REQUEST
# =========================================

def create_claim_request(
    item_id,
    sender_id,
    receiver_id,
    message
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM claim_requests
        WHERE item_id = ?
        AND sender_id = ?
        AND receiver_id = ?
        AND status = 'Pending'
    """, (
        item_id,
        sender_id,
        receiver_id
    ))

    if cursor.fetchone():

        conn.close()

        return False

    created_at = datetime.now().strftime(
        "%d-%m-%Y %I:%M:%S %p"
    )

    cursor.execute("""
        INSERT INTO claim_requests
        (
            item_id,
            sender_id,
            receiver_id,
            message,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        item_id,
        sender_id,
        receiver_id,
        message.strip(),
        "Pending",
        created_at
    ))

    conn.commit()
    conn.close()

    return True


def get_received_claims(user_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.id,
            c.item_id,
            c.sender_id,
            c.message,
            c.status,
            c.created_at,
            i.item_name,
            i.item_type,
            u.name
        FROM claim_requests c
        JOIN items i
            ON c.item_id = i.id
        JOIN users u
            ON c.sender_id = u.id
        WHERE c.receiver_id = ?
        ORDER BY c.id DESC
    """, (user_id,))

    requests = cursor.fetchall()

    conn.close()

    return requests


def get_sent_claims(user_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.id,
            c.item_id,
            c.message,
            c.status,
            c.created_at,
            i.item_name,
            u.name
        FROM claim_requests c
        JOIN items i
            ON c.item_id = i.id
        JOIN users u
            ON c.receiver_id = u.id
        WHERE c.sender_id = ?
        ORDER BY c.id DESC
    """, (user_id,))

    requests = cursor.fetchall()

    conn.close()

    return requests


def update_claim_status(
    claim_id,
    status
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE claim_requests
        SET status = ?
        WHERE id = ?
    """, (
        status,
        claim_id
    ))

    conn.commit()
    conn.close()


def get_claim_receiver(claim_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            sender_id,
            receiver_id,
            item_id
        FROM claim_requests
        WHERE id = ?
    """, (claim_id,))

    result = cursor.fetchone()

    conn.close()

    return result


# =========================================
# ITEM STATUS
# =========================================

def update_item_status(
    item_id,
    status
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE items
        SET status = ?
        WHERE id = ?
    """, (
        status,
        item_id
    ))

    conn.commit()
    conn.close()


# =========================================
# DELETE ITEM
# =========================================

def delete_item(item_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT photo
        FROM items
        WHERE id = ?
    """, (item_id,))

    result = cursor.fetchone()

    photo = (
        result[0]
        if result
        else ""
    )

    cursor.execute("""
        DELETE FROM notifications
        WHERE lost_id = ?
        OR found_id = ?
    """, (
        item_id,
        item_id
    ))

    cursor.execute("""
        DELETE FROM claim_requests
        WHERE item_id = ?
    """, (item_id,))

    cursor.execute("""
        DELETE FROM items
        WHERE id = ?
    """, (item_id,))

    conn.commit()
    conn.close()

    return photo


# =========================================
# MAKE ADMIN
# =========================================

def make_admin(username):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET is_admin = 1
        WHERE username = ?
    """, (username.strip(),))

    changed = cursor.rowcount

    conn.commit()
    conn.close()

    return changed > 0


# =========================================
# CHAT
# =========================================

def send_chat_message(
    claim_id,
    sender_id,
    receiver_id,
    message
):

    message = str(message or "").strip()

    if not message:

        return False

    conn = get_connection()
    cursor = conn.cursor()

    # Only accepted claims can be used for chat.
    cursor.execute("""
        SELECT id
        FROM claim_requests
        WHERE id = ?
        AND status = 'Accepted'
        AND (
            (sender_id = ?
             AND receiver_id = ?)
            OR
            (sender_id = ?
             AND receiver_id = ?)
        )
    """, (
        claim_id,
        sender_id,
        receiver_id,
        receiver_id,
        sender_id
    ))

    if not cursor.fetchone():

        conn.close()

        return False

    created_at = datetime.now().strftime(
        "%d-%m-%Y %I:%M:%S %p"
    )

    cursor.execute("""
        INSERT INTO chat_messages
        (
            claim_id,
            sender_id,
            receiver_id,
            message,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        claim_id,
        sender_id,
        receiver_id,
        message,
        created_at
    ))

    conn.commit()
    conn.close()

    return True


def get_chat_messages(
    claim_id,
    user_id
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            m.id,
            m.sender_id,
            u.name,
            m.message,
            m.created_at
        FROM chat_messages m
        JOIN users u
            ON m.sender_id = u.id
        WHERE m.claim_id = ?
        AND (
            m.sender_id = ?
            OR m.receiver_id = ?
        )
        ORDER BY m.id ASC
    """, (
        claim_id,
        user_id,
        user_id
    ))

    messages = cursor.fetchall()

    conn.close()

    return messages


def get_accepted_chats(user_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.id,
            c.item_id,
            c.sender_id,
            c.receiver_id,
            c.message,
            c.created_at,
            i.item_name,
            u1.name,
            u2.name
        FROM claim_requests c
        JOIN items i
            ON c.item_id = i.id
        JOIN users u1
            ON c.sender_id = u1.id
        JOIN users u2
            ON c.receiver_id = u2.id
        WHERE c.status = 'Accepted'
        AND (
            c.sender_id = ?
            OR c.receiver_id = ?
        )
        ORDER BY c.id DESC
    """, (
        user_id,
        user_id
    ))

    chats = cursor.fetchall()

    conn.close()

    return chats