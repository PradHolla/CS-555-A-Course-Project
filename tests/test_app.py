import os
import sqlite3

from app import create_app, init_db


def test_create_app_config(tmp_path):
    """create_app sets expected configuration values."""
    app = create_app()
    assert app.config["SECRET_KEY"]
    assert "UPLOAD_FOLDER" in app.config
    assert app.config["MAX_CONTENT_LENGTH"] == 5 * 1024 * 1024
    assert "ALLOWED_EXTENSIONS" in app.config


def test_init_db_adds_profile_picture_columns(tmp_path):
    """If an existing sqlite DB misses profile_picture columns, init_db adds them."""
    db_path = tmp_path / "legacy.db"
    db_file = str(db_path)

    # Create an SQLite DB with minimal legacy tables (no profile_picture columns)
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    # Create a legacy user table (without profile_picture)
    cur.execute(
        """
        CREATE TABLE user (
            id INTEGER PRIMARY KEY,
            display_name VARCHAR(100),
            email VARCHAR(200) NOT NULL UNIQUE,
            otp VARCHAR(6),
            otp_expiry DATETIME,
            created_at DATETIME
        );
        """
    )

    # Create a legacy group table (without profile_picture)
    cur.execute(
        """
        CREATE TABLE "group" (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            created_at DATETIME,
            created_by_id INTEGER
        );
        """
    )

    conn.commit()
    conn.close()

    # Create app pointing to this DB file
    app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file}"})

    # Run init_db which should run our PRAGMA checks and ALTER TABLE additions
    init_db(app)

    # Verify columns exist now
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info('user')")
    user_cols = [row[1] for row in cur.fetchall()]
    assert "profile_picture" in user_cols

    cur.execute("PRAGMA table_info('group')")
    group_cols = [row[1] for row in cur.fetchall()]
    assert "profile_picture" in group_cols

    conn.close()
