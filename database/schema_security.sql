-- Schema for the security logs database.
CREATE TABLE IF NOT EXISTS login_history (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    user_uuid TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    user_agent TEXT
);