-- =====================================================
-- Script 02: Create Database User
-- Tender Management System (TMS)
-- =====================================================
-- Description: Creates the application database user
-- Run this as a MySQL admin user
-- IMPORTANT: Change the password before running in production!
-- =====================================================

USE tms_db;

-- Create application user (change password in production!)
CREATE USER IF NOT EXISTS 'tms_user'@'localhost' IDENTIFIED BY 'TMS_Password_2026!';

-- Grant necessary privileges
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP, REFERENCES 
ON tms_db.* TO 'tms_user'@'localhost';

-- If connecting from a different host (e.g., Azure VM), also create:
-- CREATE USER IF NOT EXISTS 'tms_user'@'%' IDENTIFIED BY 'TMS_Password_2026!';
-- GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP, REFERENCES 
-- ON tms_db.* TO 'tms_user'@'%';

-- Apply changes
FLUSH PRIVILEGES;

-- Display confirmation
SELECT 'Database user tms_user created successfully' AS Status;
SELECT user, host FROM mysql.user WHERE user = 'tms_user';
