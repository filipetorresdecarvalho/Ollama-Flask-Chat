DROP TABLE IF EXISTS users;
CREATE TABLE users (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    chat_db_uuid TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL DEFAULT 'user', -- New column for user roles
    phone TEXT,
    birthday TEXT,
    city TEXT,
    country TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);