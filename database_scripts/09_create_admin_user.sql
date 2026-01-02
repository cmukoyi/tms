-- =====================================================
-- Script 09: Create Default Admin User
-- Tender Management System (TMS)
-- =====================================================
-- Description: Creates default super admin user
-- IMPORTANT: Change password after first login!
-- Default credentials: admin / Admin@2026
-- =====================================================

USE tms_db;

-- =====================================================
-- CREATE DEFAULT SUPER ADMIN USER
-- =====================================================
-- Password hash for 'Admin@2026' using werkzeug.security
-- In production, you should change this immediately!

-- Delete existing admin user first to recreate with compatible hash
DELETE FROM users WHERE username = 'admin';

INSERT INTO users (
    username,
    email,
    password_hash,
    first_name,
    last_name,
    is_active,
    is_super_admin,
    role_id,
    created_at
) VALUES (
    'admin',
    'admin@tms.local',
    'pbkdf2:sha256:1000000$63BIwoXEPLNT6COw$49947e6c8677cde8f02a8d0c1b3df8d39e2d24c4b5c1d2a5eca62dbaa2eafb39',
    'System',
    'Administrator',
    TRUE,
    TRUE,
    1,  -- Super Admin role
    NOW()
);

-- Display confirmation
SELECT 'Default admin user created successfully' AS Status;
SELECT 
    'Login with: admin / Admin@2026' AS Credentials,
    'IMPORTANT: Change password after first login!' AS Warning;

SELECT 
    id,
    username,
    email,
    first_name,
    last_name,
    is_super_admin,
    is_active
FROM users 
WHERE username = 'admin';
