import sqlite3
from datetime import datetime

DATABASE_NAME = "uor_job_bot.db"

def get_conn():
    """Get a database connection."""
    return sqlite3.connect(DATABASE_NAME)

def init_db():
    """Initialize the database and create tables if they don't exist."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            subscription_status TEXT DEFAULT 'No',
            keyword TEXT,
            location TEXT,
            premium_status TEXT DEFAULT 'free',
            searches_today INTEGER DEFAULT 0,
            last_search_date TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id: int):
    """Add a new user to the database if they don't already exist."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_user(user_id: int) -> dict:
    """Retrieve user data."""
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

# In database.py, replace the old subscribe_user with this:

def subscribe_user(user_id: int, keyword: str, location: str, min_salary: int = 0):
    """Subscribe a user to daily alerts, including salary preference."""
    conn = get_conn()
    cursor = conn.cursor()
    
    # First, ensure the min_salary column exists. This is robust.
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN min_salary INTEGER DEFAULT 0;")
    except sqlite3.OperationalError:
        # Column already exists, which is fine.
        pass

    cursor.execute("""
        UPDATE users
        SET subscription_status = 'Yes', keyword = ?, location = ?, min_salary = ?
        WHERE user_id = ?
    """, (keyword, location, min_salary, user_id))
    conn.commit()
    conn.close()

def unsubscribe_user(user_id: int):
    """Unsubscribe a user from daily alerts."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users
        SET subscription_status = 'No', keyword = NULL, location = NULL
        WHERE user_id = ?
    """, (user_id,))
    conn.commit()
    conn.close()

def get_subscribed_users() -> list:
    """Get all users who are subscribed to daily alerts."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, keyword, location FROM users WHERE subscription_status = 'Yes'")
    users = cursor.fetchall()
    conn.close()
    return users

def update_search_count(user_id: int):
    """Update the search count for a user."""
    conn = get_conn()
    cursor = conn.cursor()
    today = datetime.now().date().isoformat()
    user = get_user(user_id)
    if not user:
        add_user(user_id)
        user = get_user(user_id)

    if user.get('last_search_date') != today:
        cursor.execute("UPDATE users SET searches_today = 1, last_search_date = ? WHERE user_id = ?", (today, user_id))
    else:
        cursor.execute("UPDATE users SET searches_today = searches_today + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()