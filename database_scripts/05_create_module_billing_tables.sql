-- =====================================================
-- Script 05: Create Module & Billing Tables
-- Tender Management System (TMS)
-- =====================================================
-- Description: Creates module system and billing tables
-- Module Definitions, Company Modules, Pricing, Bills
-- =====================================================

USE tms_db;

-- =====================================================
-- MODULE DEFINITIONS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS module_definitions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    module_name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_core BOOLEAN DEFAULT FALSE,
    category VARCHAR(50) DEFAULT 'feature',
    monthly_price DECIMAL(10, 2) DEFAULT 0.00,
    sort_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_module_name (module_name),
    INDEX idx_module_active (is_active),
    INDEX idx_module_sort (sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- COMPANY MODULES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS company_modules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    module_id INT NOT NULL,
    is_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    enabled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    enabled_by INT,
    disabled_at DATETIME,
    disabled_by INT,
    notes TEXT,
    billing_start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    billing_end_date DATETIME,
    monthly_cost DECIMAL(10, 2) DEFAULT 0.00,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    FOREIGN KEY (module_id) REFERENCES module_definitions(id) ON DELETE CASCADE,
    FOREIGN KEY (enabled_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (disabled_by) REFERENCES users(id) ON DELETE SET NULL,
    
    UNIQUE KEY unique_company_module (company_id, module_id),
    INDEX idx_company_module_enabled (is_enabled),
    INDEX idx_company_module_company (company_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- COMPANY MODULE PRICING TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS company_module_pricing (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    module_id INT NOT NULL,
    custom_price DECIMAL(10, 2) NOT NULL,
    effective_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    FOREIGN KEY (module_id) REFERENCES module_definitions(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT,
    
    INDEX idx_custom_pricing_company (company_id),
    INDEX idx_custom_pricing_module (module_id),
    INDEX idx_custom_pricing_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- MONTHLY BILLS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS monthly_bills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    bill_year INT NOT NULL,
    bill_month INT NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'ZAR' NOT NULL,
    bill_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    due_date DATETIME,
    status VARCHAR(20) DEFAULT 'draft' NOT NULL,
    generated_by INT NOT NULL,
    generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    FOREIGN KEY (generated_by) REFERENCES users(id) ON DELETE RESTRICT,
    
    INDEX idx_bill_company (company_id),
    INDEX idx_bill_period (bill_year, bill_month),
    INDEX idx_bill_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- BILL LINE ITEMS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS bill_line_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bill_id INT NOT NULL,
    module_id INT NOT NULL,
    module_name VARCHAR(100) NOT NULL,
    module_display_name VARCHAR(200) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    quantity INT DEFAULT 1 NOT NULL,
    line_total DECIMAL(10, 2) NOT NULL,
    is_custom_price BOOLEAN DEFAULT FALSE NOT NULL,
    pricing_notes TEXT,
    
    FOREIGN KEY (bill_id) REFERENCES monthly_bills(id) ON DELETE CASCADE,
    FOREIGN KEY (module_id) REFERENCES module_definitions(id) ON DELETE RESTRICT,
    
    INDEX idx_bill_line_bill (bill_id),
    INDEX idx_bill_line_module (module_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- LEGACY FEATURES TABLE (for backward compatibility)
-- =====================================================
CREATE TABLE IF NOT EXISTS features (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    category VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_feature_code (code),
    INDEX idx_feature_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- COMPANY FEATURES TABLE (Legacy)
-- =====================================================
CREATE TABLE IF NOT EXISTS company_features (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    feature_id INT NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    enabled_at DATETIME,
    enabled_by INT,
    code VARCHAR(50),
    is_enabled BOOLEAN DEFAULT TRUE,
    
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    FOREIGN KEY (feature_id) REFERENCES features(id) ON DELETE CASCADE,
    FOREIGN KEY (enabled_by) REFERENCES users(id) ON DELETE SET NULL,
    
    UNIQUE KEY unique_company_feature (company_id, feature_id),
    INDEX idx_company_feature_enabled (enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Display confirmation
SELECT 'Module and billing tables created successfully' AS Status;
