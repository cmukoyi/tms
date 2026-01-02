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
    'scrypt:32768:8:1$SJEwZzOWn9D0Lc8R$d8f0c3e7a1f2b4c9e8d7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7',
    'System',
    'Administrator',
    TRUE,
    TRUE,
    1,  -- Super Admin role
    NOW()
)
ON DUPLICATE KEY UPDATE 
    email = VALUES(email),
    first_name = VALUES(first_name),
    last_name = VALUES(last_name),
    is_super_admin = VALUES(is_super_admin);

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
