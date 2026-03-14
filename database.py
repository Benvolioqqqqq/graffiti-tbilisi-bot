import sqlite3

def init_db():
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS graffiti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            photo_id TEXT,
            author TEXT DEFAULT 'Неизвестен',
            date TEXT DEFAULT 'Неизвестна',
            description TEXT DEFAULT '',
            added_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    """)
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            user_id INTEGER,
            graffiti_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, graffiti_id)
        )
    """)
    conn.commit()
    conn.close()

def add_graffiti(latitude, longitude, photo_id, author, date, description, added_by):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO graffiti (latitude, longitude, photo_id, author, date, description, added_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (latitude, longitude, photo_id, author, date, description, added_by)
    )
    last_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return last_id

def get_all_graffiti():
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM graffiti WHERE status = 'approved'")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_pending_graffiti():
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM graffiti WHERE status = 'pending'")
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_status(graffiti_id, status):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE graffiti SET status = ? WHERE id = ?", (status, graffiti_id))
    conn.commit()
    conn.close()

def delete_graffiti(graffiti_id):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM graffiti WHERE id = ?", (graffiti_id,))
    conn.commit()
    conn.close()

def search_graffiti(query):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM graffiti WHERE status = 'approved' AND (author LIKE ? OR description LIKE ?)",
        (f"%{query}%", f"%{query}%")
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_stats():
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM graffiti WHERE status = 'approved'")
    approved = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM graffiti WHERE status = 'pending'")
    pending = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM graffiti")
    total = cursor.fetchone()[0]
    cursor.execute("""
        SELECT added_by, COUNT(*) as cnt 
        FROM graffiti WHERE status = 'approved' 
        GROUP BY added_by ORDER BY cnt DESC LIMIT 5
    """)
    top_users = cursor.fetchall()
    conn.close()
    return {"approved": approved, "pending": pending, "total": total, "top_users": top_users}

def update_added_by_username(graffiti_id, username):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE graffiti SET added_by = ? WHERE id = ?", (username, graffiti_id))
    conn.commit()
    conn.close()

def save_user(user_id, username, full_name):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
        (user_id, username, full_name)
    )
    conn.commit()
    conn.close()

def get_users_count():
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count



def toggle_like(user_id, graffiti_id):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM likes WHERE user_id = ? AND graffiti_id = ?", (user_id, graffiti_id))
    if cursor.fetchone():
        cursor.execute("DELETE FROM likes WHERE user_id = ? AND graffiti_id = ?", (user_id, graffiti_id))
        liked = False
    else:
        cursor.execute("INSERT INTO likes (user_id, graffiti_id) VALUES (?, ?)", (user_id, graffiti_id))
        liked = True
    conn.commit()
    conn.close()
    return liked

def get_likes_count(graffiti_id):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM likes WHERE graffiti_id = ?", (graffiti_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def is_liked(user_id, graffiti_id):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM likes WHERE user_id = ? AND graffiti_id = ?", (user_id, graffiti_id))
    result = cursor.fetchone() is not None
    conn.close()
    return result

def get_top_liked(limit=5):
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT g.id, g.author, g.photo_id, COUNT(l.user_id) as likes
        FROM graffiti g
        JOIN likes l ON g.id = l.graffiti_id
        WHERE g.status = 'approved'
        GROUP BY g.id
        ORDER BY likes DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_all_likes():
    conn = sqlite3.connect("graffiti.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT graffiti_id, COUNT(*) as cnt
        FROM likes GROUP BY graffiti_id
    """)
    rows = cursor.fetchall()
    conn.close()
    return dict(rows)
