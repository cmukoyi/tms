-- =====================================================
-- Script 08: Insert Initial Data
-- Tender Management System (TMS)
-- =====================================================
-- Description: Inserts initial/seed data
-- Roles, Statuses, Categories, Modules, Permissions
-- =====================================================

USE tms_db;

-- =====================================================
-- INSERT DEFAULT ROLES
-- =====================================================
INSERT INTO roles (name, description) VALUES
    ('Super Admin', 'System administrator with full access'),
    ('Company Admin', 'Company administrator'),
    ('Manager', 'Company manager'),
    ('User', 'Regular user')
ON DUPLICATE KEY UPDATE description = VALUES(description);

-- =====================================================
-- INSERT TENDER STATUSES
-- =====================================================
INSERT INTO tender_statuses (name, description, color, sort_order) VALUES
    ('Draft', 'Tender in draft state', '#6c757d', 1),
    ('Open', 'Tender is open for submissions', '#17a2b8', 2),
    ('Closed', 'Tender has been closed', '#dc3545', 3),
    ('In Progress', 'Tender work in progress', '#ffc107', 4),
    ('Awarded', 'Tender has been awarded', '#28a745', 5),
    ('Cancelled', 'Tender has been cancelled', '#343a40', 6)
ON DUPLICATE KEY UPDATE description = VALUES(description);

-- =====================================================
-- INSERT TENDER CATEGORIES
-- =====================================================
INSERT INTO tender_categories (name, description) VALUES
    ('IT Services', 'Information Technology services and solutions'),
    ('Construction', 'Building and construction projects'),
    ('Consulting', 'Business and technical consulting'),
    ('Supplies', 'Office and general supplies'),
    ('Maintenance', 'Maintenance and repair services'),
    ('Software Development', 'Custom software development'),
    ('Infrastructure', 'IT infrastructure projects'),
    ('Professional Services', 'Various professional services')
ON DUPLICATE KEY UPDATE description = VALUES(description);

-- =====================================================
-- INSERT DOCUMENT TYPES
-- =====================================================
INSERT INTO document_types (name, description, allowed_extensions, max_size_mb) VALUES
    ('RFP Document', 'Request for Proposal document', '.pdf,.doc,.docx', 20),
    ('Technical Proposal', 'Technical proposal document', '.pdf,.doc,.docx', 20),
    ('Financial Proposal', 'Financial/pricing proposal', '.pdf,.xlsx,.xls', 10),
    ('Supporting Document', 'Supporting documentation', '.pdf,.doc,.docx,.xlsx', 15),
    ('Contract', 'Contract documents', '.pdf,.doc,.docx', 10),
    ('Certificate', 'Certificates and compliance docs', '.pdf,.jpg,.png', 5)
ON DUPLICATE KEY UPDATE description = VALUES(description);

-- =====================================================
-- INSERT MODULE DEFINITIONS
-- =====================================================
INSERT INTO module_definitions (module_name, display_name, description, is_core, category, monthly_price, sort_order) VALUES
    ('basic_tender_management', 'Basic Tender Management', 'Core tender management features', TRUE, 'core', 0.00, 1),
    ('advanced_search', 'Advanced Search', 'Advanced search and filtering', FALSE, 'feature', 150.00, 2),
    ('analytics_dashboard', 'Analytics Dashboard', 'Advanced analytics and reporting', FALSE, 'analytics', 300.00, 3),
    ('document_management', 'Document Management', 'Enhanced document management', FALSE, 'feature', 200.00, 4),
    ('workflow_automation', 'Workflow Automation', 'Automated workflow and approvals', FALSE, 'workflow', 400.00, 5),
    ('notifications', 'Notifications', 'Email and system notifications', FALSE, 'feature', 100.00, 6),
    ('custom_fields', 'Custom Fields', 'Custom field definitions', FALSE, 'feature', 150.00, 7),
    ('reporting', 'Advanced Reporting', 'Comprehensive reporting tools', FALSE, 'analytics', 250.00, 8),
    ('api_access', 'API Access', 'REST API access for integrations', FALSE, 'integration', 500.00, 9),
    ('multi_user', 'Multi-User Access', 'Support for multiple users', FALSE, 'feature', 200.00, 10),
    ('accounting', 'Accounting Module', 'Full accounting and financial management', FALSE, 'finance', 600.00, 11),
    ('chatbot', 'AI Chatbot', 'AI-powered tender assistance', FALSE, 'ai', 350.00, 12)
ON DUPLICATE KEY UPDATE 
    display_name = VALUES(display_name),
    description = VALUES(description),
    monthly_price = VALUES(monthly_price);

-- =====================================================
-- INSERT PERMISSIONS
-- =====================================================
INSERT INTO permissions (name, display_name, description, category) VALUES
    -- Tender permissions
    ('view_tenders', 'View Tenders', 'View tender information', 'tenders'),
    ('create_tenders', 'Create Tenders', 'Create new tenders', 'tenders'),
    ('edit_tenders', 'Edit Tenders', 'Edit tender information', 'tenders'),
    ('delete_tenders', 'Delete Tenders', 'Delete tenders', 'tenders'),
    ('assign_tenders', 'Assign Tenders', 'Assign tenders to users', 'tenders'),
    ('submit_tenders', 'Submit Tenders', 'Submit tenders for approval', 'tenders'),
    ('approve_tenders', 'Approve Tenders', 'Approve or reject tenders', 'tenders'),
    
    -- User permissions
    ('view_users', 'View Users', 'View user information', 'users'),
    ('create_users', 'Create Users', 'Create new users', 'users'),
    ('edit_users', 'Edit Users', 'Edit user information', 'users'),
    ('delete_users', 'Delete Users', 'Delete users', 'users'),
    ('manage_roles', 'Manage Roles', 'Manage user roles and permissions', 'users'),
    
    -- Document permissions
    ('view_documents', 'View Documents', 'View documents', 'documents'),
    ('upload_documents', 'Upload Documents', 'Upload new documents', 'documents'),
    ('delete_documents', 'Delete Documents', 'Delete documents', 'documents'),
    
    -- Reporting permissions
    ('view_reports', 'View Reports', 'View reports and analytics', 'reports'),
    ('export_data', 'Export Data', 'Export data to Excel/PDF', 'reports'),
    
    -- Billing permissions
    ('view_billing', 'View Billing', 'View billing information', 'billing'),
    ('manage_billing', 'Manage Billing', 'Manage billing and invoices', 'billing'),
    
    -- System permissions
    ('manage_company', 'Manage Company', 'Manage company settings', 'system'),
    ('manage_modules', 'Manage Modules', 'Enable/disable modules', 'system'),
    ('view_audit_logs', 'View Audit Logs', 'View system audit logs', 'system')
ON DUPLICATE KEY UPDATE 
    display_name = VALUES(display_name),
    description = VALUES(description);

-- =====================================================
-- INSERT ACCOUNT TYPES (for accounting module)
-- =====================================================
INSERT INTO account_types (name, category, normal_balance, description) VALUES
    ('Cash', 'asset', 'debit', 'Cash accounts'),
    ('Bank', 'asset', 'debit', 'Bank accounts'),
    ('Accounts Receivable', 'asset', 'debit', 'Money owed by customers'),
    ('Inventory', 'asset', 'debit', 'Inventory assets'),
    ('Fixed Assets', 'asset', 'debit', 'Property, plant, and equipment'),
    ('Accounts Payable', 'liability', 'credit', 'Money owed to suppliers'),
    ('Loans Payable', 'liability', 'credit', 'Outstanding loans'),
    ('Equity', 'equity', 'credit', 'Owner equity'),
    ('Retained Earnings', 'equity', 'credit', 'Accumulated earnings'),
    ('Revenue', 'revenue', 'credit', 'Income from operations'),
    ('Cost of Sales', 'expense', 'debit', 'Direct costs'),
    ('Operating Expenses', 'expense', 'debit', 'Business operating costs'),
    ('Salaries', 'expense', 'debit', 'Employee salaries and wages'),
    ('Utilities', 'expense', 'debit', 'Utility expenses'),
    ('Depreciation', 'expense', 'debit', 'Asset depreciation')
ON DUPLICATE KEY UPDATE description = VALUES(description);

-- Display confirmation
SELECT 'Initial data inserted successfully' AS Status;

-- Display counts
SELECT 'Roles' AS Table_Name, COUNT(*) AS Record_Count FROM roles
UNION ALL
SELECT 'Tender Statuses', COUNT(*) FROM tender_statuses
UNION ALL
SELECT 'Tender Categories', COUNT(*) FROM tender_categories
UNION ALL
SELECT 'Document Types', COUNT(*) FROM document_types
UNION ALL
SELECT 'Module Definitions', COUNT(*) FROM module_definitions
UNION ALL
SELECT 'Permissions', COUNT(*) FROM permissions
UNION ALL
SELECT 'Account Types', COUNT(*) FROM account_types;
