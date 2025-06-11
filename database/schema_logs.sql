CREATE TABLE IF NOT EXISTS error_logs (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_uuid TEXT,
    request_method TEXT,
    request_url TEXT,
    ip_address TEXT,
    status_code INTEGER,
    error_message TEXT NOT NULL
);