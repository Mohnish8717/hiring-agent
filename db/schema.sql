-- Database Schema for Device Fingerprinting
-- Designed for PostgreSQL or SQLite

CREATE TABLE IF NOT EXISTS device_fingerprints (
    device_id CHAR(64) PRIMARY KEY,          -- SHA-256 hash
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    application_count INTEGER DEFAULT 1,
    fingerprint_entropy FLOAT,               -- Measure of uniqueness
    is_blacklisted BOOLEAN DEFAULT FALSE,
    blacklist_reason TEXT
);

CREATE TABLE IF NOT EXISTS device_ip_history (
    id SERIAL PRIMARY KEY,
    device_id CHAR(64) REFERENCES device_fingerprints(device_id),
    ip_address TEXT,
    ip_country CHAR(2),
    is_vpn BOOLEAN DEFAULT FALSE,
    seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_device_id ON device_fingerprints(device_id);
CREATE INDEX idx_device_ip_history_device_id ON device_ip_history(device_id);
