-- Table for storing user-submitted texts
CREATE TABLE IF NOT EXISTS texts (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    username TEXT NOT NULL,
    text TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing key-value settings (e.g., current book, snack, roles)
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);


-- Table for storing user book progress
CREATE TABLE IF NOT EXISTS user_progress (
    user_id BIGINT PRIMARY KEY,
    username TEXT NOT NULL,
    progress TEXT
);
