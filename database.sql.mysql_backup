-- MEFAPEX Chatbot Database Schema
-- Simple user authentication table for demo purposes

-- Create database
CREATE DATABASE IF NOT EXISTS mefapex_chatbot;
USE mefapex_chatbot;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    department VARCHAR(50),
    role VARCHAR(30) DEFAULT 'employee',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- Insert demo user
INSERT INTO users (username, password, full_name, department, role) VALUES 
('demo', '1234', 'Demo Kullanıcı', 'Üretim', 'employee');

-- Create chat_logs table to store conversations (optional)
CREATE TABLE IF NOT EXISTS chat_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    user_message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(100),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Create system_settings table for configuration
CREATE TABLE IF NOT EXISTS system_settings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    setting_key VARCHAR(50) NOT NULL UNIQUE,
    setting_value TEXT,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Insert default system settings
INSERT INTO system_settings (setting_key, setting_value, description) VALUES
('chatbot_name', 'MEFAPEX AI Asistan', 'Name of the chatbot'),
('max_message_length', '500', 'Maximum message length allowed'),
('session_timeout', '3600', 'Session timeout in seconds'),
('enable_logging', 'true', 'Enable chat logging'),
('maintenance_mode', 'false', 'System maintenance mode');

-- Show tables
SHOW TABLES;

-- Show demo user
SELECT * FROM users WHERE username = 'demo';

-- Show system settings
SELECT * FROM system_settings;
