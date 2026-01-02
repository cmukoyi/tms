-- =====================================================
-- Script 06: Create Workflow & Permissions Tables
-- Tender Management System (TMS)
-- =====================================================
-- Description: Creates workflow and permissions tables
-- Roles, Permissions, Assignments, Workflow
-- =====================================================

USE tms_db;

-- =====================================================
-- PERMISSIONS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    category VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_permission_name (name),
    INDEX idx_permission_category (category),
    INDEX idx_permission_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- COMPANY ROLES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS company_roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    is_system_role BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    
    INDEX idx_company_role_company (company_id),
    INDEX idx_company_role_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- ROLE PERMISSIONS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS role_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role_id INT NOT NULL,
    permission_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (role_id) REFERENCES company_roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
    
    UNIQUE KEY unique_role_permission (role_id, permission_id),
    INDEX idx_role_perm_role (role_id),
    INDEX idx_role_perm_permission (permission_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- USER COMPANY ROLES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS user_company_roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    role_id INT NOT NULL,
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    assigned_by INT,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES company_roles(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by) REFERENCES users(id) ON DELETE SET NULL,
    
    UNIQUE KEY unique_user_role (user_id, role_id),
    INDEX idx_user_role_user (user_id),
    INDEX idx_user_role_role (role_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TENDER ASSIGNMENTS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS tender_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tender_id INT NOT NULL,
    assigned_to_id INT NOT NULL,
    assigned_by_id INT NOT NULL,
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    due_date DATETIME,
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    
    FOREIGN KEY (tender_id) REFERENCES tenders(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_to_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by_id) REFERENCES users(id) ON DELETE RESTRICT,
    
    INDEX idx_assignment_tender (tender_id),
    INDEX idx_assignment_user (assigned_to_id),
    INDEX idx_assignment_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TENDER WORKFLOWS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS tender_workflows (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tender_id INT NOT NULL UNIQUE,
    status VARCHAR(50) DEFAULT 'draft',
    submitted_for_approval_at DATETIME,
    submitted_for_approval_by INT,
    approved_rejected_at DATETIME,
    approved_rejected_by INT,
    approval_notes TEXT,
    submitted_at DATETIME,
    submitted_by INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tender_id) REFERENCES tenders(id) ON DELETE CASCADE,
    FOREIGN KEY (submitted_for_approval_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (approved_rejected_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (submitted_by) REFERENCES users(id) ON DELETE SET NULL,
    
    INDEX idx_workflow_status (status),
    INDEX idx_workflow_tender (tender_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TENDER COMMENTS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS tender_comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tender_id INT NOT NULL,
    user_id INT NOT NULL,
    comment TEXT NOT NULL,
    parent_comment_id INT,
    is_internal BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    
    FOREIGN KEY (tender_id) REFERENCES tenders(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_comment_id) REFERENCES tender_comments(id) ON DELETE CASCADE,
    
    INDEX idx_comment_tender (tender_id),
    INDEX idx_comment_user (user_id),
    INDEX idx_comment_parent (parent_comment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TENDER ACTIVITIES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS tender_activities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tender_id INT NOT NULL,
    user_id INT,
    activity_type VARCHAR(50) NOT NULL,
    description TEXT,
    activity_metadata TEXT,
    ip_address VARCHAR(45),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tender_id) REFERENCES tenders(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    
    INDEX idx_activity_tender (tender_id),
    INDEX idx_activity_type (activity_type),
    INDEX idx_activity_date (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Display confirmation
SELECT 'Workflow and permissions tables created successfully' AS Status;
