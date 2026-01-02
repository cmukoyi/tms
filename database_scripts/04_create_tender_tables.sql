-- =====================================================
-- Script 04: Create Tender Tables
-- Tender Management System (TMS)
-- =====================================================
-- Description: Creates tender-related tables
-- Tenders, Documents, Notes, History, Custom Fields
-- =====================================================

USE tms_db;

-- =====================================================
-- TENDERS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS tenders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    reference_number VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    
    -- Foreign Keys
    company_id INT NOT NULL,
    category_id INT NOT NULL,
    status_id INT NOT NULL,
    created_by INT NOT NULL,
    
    -- Dates
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    submission_deadline DATETIME,
    opening_date DATETIME,
    
    -- Custom fields storage
    custom_fields TEXT,
    
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES tender_categories(id) ON DELETE RESTRICT,
    FOREIGN KEY (status_id) REFERENCES tender_statuses(id) ON DELETE RESTRICT,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT,
    
    INDEX idx_tender_company (company_id),
    INDEX idx_tender_status (status_id),
    INDEX idx_tender_category (category_id),
    INDEX idx_tender_deadline (submission_deadline),
    INDEX idx_tender_reference (reference_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TENDER DOCUMENTS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS tender_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tender_id INT NOT NULL,
    document_type VARCHAR(50),
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INT,
    mime_type VARCHAR(100),
    uploaded_by_id INT NOT NULL,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    version INT DEFAULT 1,
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    
    FOREIGN KEY (tender_id) REFERENCES tenders(id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by_id) REFERENCES users(id) ON DELETE RESTRICT,
    
    INDEX idx_tender_doc_tender (tender_id),
    INDEX idx_tender_doc_type (document_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TENDER NOTES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS tender_notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tender_id INT NOT NULL,
    content TEXT NOT NULL,
    created_by_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tender_id) REFERENCES tenders(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE RESTRICT,
    
    INDEX idx_tender_note_tender (tender_id),
    INDEX idx_tender_note_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TENDER HISTORY TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS tender_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tender_id INT NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    action_description TEXT NOT NULL,
    details JSON,
    performed_by_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    
    FOREIGN KEY (tender_id) REFERENCES tenders(id) ON DELETE CASCADE,
    FOREIGN KEY (performed_by_id) REFERENCES users(id) ON DELETE RESTRICT,
    
    INDEX idx_tender_history_tender (tender_id),
    INDEX idx_tender_history_type (action_type),
    INDEX idx_tender_history_date (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- CUSTOM FIELDS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS custom_fields (
    id INT AUTO_INCREMENT PRIMARY KEY,
    field_name VARCHAR(100) NOT NULL,
    field_label VARCHAR(100) NOT NULL,
    field_type VARCHAR(50) NOT NULL,
    field_options TEXT,
    is_required BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INT NOT NULL,
    
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT,
    
    INDEX idx_custom_field_active (is_active),
    INDEX idx_custom_field_sort (sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- DOCUMENTS TABLE (General company documents)
-- =====================================================
CREATE TABLE IF NOT EXISTS documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tender_id INT,
    company_id INT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_size INT,
    file_type VARCHAR(100),
    uploaded_by_id INT NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tender_id) REFERENCES tenders(id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by_id) REFERENCES users(id) ON DELETE RESTRICT,
    
    INDEX idx_document_tender (tender_id),
    INDEX idx_document_company (company_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- COMPANY DOCUMENTS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS company_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    document_name VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INT,
    mime_type VARCHAR(100),
    document_category VARCHAR(100) NOT NULL,
    description TEXT,
    uploaded_by INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE RESTRICT,
    
    INDEX idx_company_doc_company (company_id),
    INDEX idx_company_doc_category (document_category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Display confirmation
SELECT 'Tender tables created successfully' AS Status;
