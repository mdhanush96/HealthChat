-- HealthChat MySQL setup script
-- Run this once to create the database and user before starting the Django server.

CREATE DATABASE IF NOT EXISTS healthchat_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Optional: create a dedicated user (replace 'healthchat_user' and 'StrongPassword!' as needed)
-- CREATE USER IF NOT EXISTS 'healthchat_user'@'localhost' IDENTIFIED BY 'StrongPassword!';
-- GRANT ALL PRIVILEGES ON healthchat_db.* TO 'healthchat_user'@'localhost';
-- FLUSH PRIVILEGES;
