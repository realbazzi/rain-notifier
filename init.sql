CREATE DATABASE IF NOT EXISTS rainbot;
USE rainbot;

CREATE TABLE users (
    chat_id BIGINT PRIMARY KEY
);

CREATE TABLE rains (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rain_id VARCHAR(255),
    points INT,
    durationSec INT,
    startedAt BIGINT,
    expiresAt BIGINT,
    totalClaims INT DEFAULT 0,
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);