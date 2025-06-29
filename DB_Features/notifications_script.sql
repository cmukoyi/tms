-- =====================================================
-- Database Migration for Notification System
-- Run this in PythonAnywhere MySQL console
-- =====================================================

-- =====================================================
-- 1. COMPANY SETTINGS TABLE
-- =====================================================
CREATE TABLE `company_settings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `company_id` int NOT NULL,
  `notification_days` int DEFAULT 7,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_company_settings` (`company_id`),
  KEY `idx_company_settings_company` (`company_id`),
  CONSTRAINT `company_settings_ibfk_1` FOREIGN KEY (`company_id`) REFERENCES `companies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =====================================================
-- 2. TENDER NOTIFICATIONS TABLE
-- =====================================================
CREATE TABLE `tender_notifications` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tender_id` int NOT NULL,
  `company_id` int NOT NULL,
  `notification_type` varchar(50) DEFAULT 'deadline_approaching',
  `message` text,
  `days_remaining` int DEFAULT NULL,
  `is_read` tinyint(1) DEFAULT 0,
  `is_processed` tinyint(1) DEFAULT 0,
  `processed_by` int DEFAULT NULL,
  `processed_at` datetime DEFAULT NULL,
  `processing_note` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_tender_notifications_tender` (`tender_id`),
  KEY `idx_tender_notifications_company` (`company_id`),
  KEY `idx_tender_notifications_processed_by` (`processed_by`),
  KEY `idx_tender_notifications_read` (`is_read`),
  KEY `idx_tender_notifications_processed` (`is_processed`),
  KEY `idx_tender_notifications_created` (`created_at`),
  CONSTRAINT `tender_notifications_ibfk_1` FOREIGN KEY (`tender_id`) REFERENCES `tenders` (`id`) ON DELETE CASCADE,
  CONSTRAINT `tender_notifications_ibfk_2` FOREIGN KEY (`company_id`) REFERENCES `companies` (`id`) ON DELETE CASCADE,
  CONSTRAINT `tender_notifications_ibfk_3` FOREIGN KEY (`processed_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =====================================================
-- 3. INSERT DEFAULT SETTINGS FOR EXISTING COMPANIES
-- =====================================================
INSERT INTO `company_settings` (`company_id`, `notification_days`, `created_at`, `updated_at`)
SELECT 
    c.id,
    7,
    NOW(),
    NOW()
FROM `companies` c
LEFT JOIN company_settings cs ON cs.company_id = c.id
WHERE c.is_active = 1 AND cs.company_id IS NULL;


-- =====================================================
-- 4. SAMPLE DATA - CREATE SAMPLE NOTIFICATIONS
-- =====================================================
-- This will create sample notifications for tenders with upcoming deadlines

INSERT INTO `tender_notifications` (
    `tender_id`,
    `company_id`, 
    `notification_type`,
    `message`,
    `days_remaining`,
    `is_read`,
    `is_processed`,
    `created_at`
)
SELECT 
    t.id,
    t.company_id,
    'deadline_approaching',
    CONCAT('Tender "', t.title, '" (', t.reference_number, ') deadline approaching'),
    DATEDIFF(t.submission_deadline, NOW()) as days_remaining,
    0,
    0,
    NOW()
FROM `tenders` t
WHERE t.submission_deadline > NOW() 
AND t.submission_deadline <= DATE_ADD(NOW(), INTERVAL 7 DAY)
AND t.status_id NOT IN (3, 6)  -- Not closed or cancelled
AND t.company_id IN (SELECT id FROM companies WHERE is_active = 1);

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================

-- Check tables were created
SHOW TABLES LIKE '%notification%';
SHOW TABLES LIKE '%settings%';

-- Check company settings
SELECT 
    c.name as company_name,
    cs.notification_days,
    cs.created_at
FROM company_settings cs
JOIN companies c ON c.id = cs.company_id
ORDER BY c.name;

-- Check notifications created
SELECT 
    COUNT(*) as total_notifications,
    COUNT(CASE WHEN is_read = 0 THEN 1 END) as unread_notifications,
    COUNT(CASE WHEN is_processed = 0 THEN 1 END) as unprocessed_notifications
FROM tender_notifications;

-- Check notifications by company
SELECT 
    c.name as company_name,
    COUNT(tn.id) as notification_count,
    COUNT(CASE WHEN tn.is_read = 0 THEN 1 END) as unread_count
FROM companies c
LEFT JOIN tender_notifications tn ON tn.company_id = c.id
WHERE c.is_active = 1
GROUP BY c.id, c.name
ORDER BY notification_count DESC;

-- Show sample notifications
SELECT 
    tn.id,
    c.name as company,
    t.reference_number,
    t.title,
    tn.message,
    tn.days_remaining,
    tn.is_read,
    tn.is_processed,
    tn.created_at
FROM tender_notifications tn
JOIN companies c ON c.id = tn.company_id
JOIN tenders t ON t.id = tn.tender_id
ORDER BY tn.created_at DESC
LIMIT 10;