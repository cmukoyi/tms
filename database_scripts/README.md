# TMS Database Scripts

Database setup scripts for Tender Management System (TMS) - Azure VM Deployment

## Overview

These scripts create the complete database structure for TMS including all tables, relationships, initial data, and a default admin user.

## Prerequisites

- MySQL 8.0 or higher (MySQL 5.7+ also supported)
- MySQL client or MySQL Workbench
- Database admin privileges

## Execution Order

**IMPORTANT:** Run these scripts in the exact order listed below!

### 1. Database Creation
```bash
mysql -u root -p < 01_create_database.sql
```
Creates the `tms_db` database with UTF8MB4 character set.

### 2. User Creation
```bash
mysql -u root -p < 02_create_user.sql
```
Creates `tms_user` with necessary privileges.
**⚠️ CHANGE THE PASSWORD before running in production!**

### 3. Core Tables
```bash
mysql -u root -p < 03_create_core_tables.sql
```
Creates:
- companies
- users
- roles
- tender_categories
- tender_statuses
- document_types

### 4. Tender Tables
```bash
mysql -u root -p < 04_create_tender_tables.sql
```
Creates:
- tenders
- tender_documents
- tender_notes
- tender_history
- custom_fields
- documents
- company_documents

### 5. Module & Billing Tables
```bash
mysql -u root -p < 05_create_module_billing_tables.sql
```
Creates:
- module_definitions
- company_modules
- company_module_pricing
- monthly_bills
- bill_line_items
- features (legacy)
- company_features (legacy)

### 6. Workflow & Permissions Tables
```bash
mysql -u root -p < 06_create_workflow_permissions_tables.sql
```
Creates:
- permissions
- company_roles
- role_permissions
- user_company_roles
- tender_assignments
- tender_workflows
- tender_comments
- tender_activities

### 7. Notification & Accounting Tables
```bash
mysql -u root -p < 07_create_notification_accounting_tables.sql
```
Creates:
- company_settings
- tender_notifications
- saved_searches
- account_types
- accounts
- journal_entries
- transactions

### 8. Initial Data
```bash
mysql -u root -p < 08_insert_initial_data.sql
```
Inserts seed data:
- Default roles (Super Admin, Company Admin, Manager, User)
- Tender statuses (Draft, Open, Closed, etc.)
- Tender categories (IT Services, Construction, etc.)
- Document types (RFP, Proposals, etc.)
- Module definitions (12 modules)
- Permissions (23 permissions)
- Account types (15 types)

### 9. Create Admin User
```bash
mysql -u root -p < 09_create_admin_user.sql
```
Creates default super admin:
- **Username:** admin
- **Password:** Admin@2026
- **⚠️ CRITICAL:** Change this password immediately after first login!

## Quick Setup (All Scripts)

Run all scripts in sequence:

```bash
cd database_scripts

mysql -u root -p < 01_create_database.sql
mysql -u root -p < 02_create_user.sql
mysql -u root -p < 03_create_core_tables.sql
mysql -u root -p < 04_create_tender_tables.sql
mysql -u root -p < 05_create_module_billing_tables.sql
mysql -u root -p < 06_create_workflow_permissions_tables.sql
mysql -u root -p < 07_create_notification_accounting_tables.sql
mysql -u root -p < 08_insert_initial_data.sql
mysql -u root -p < 09_create_admin_user.sql
```

Or use a single command:

```bash
for script in *.sql; do 
    echo "Running $script..."
    mysql -u root -p < "$script"
done
```

## Azure VM Deployment

### 1. Upload Scripts to Azure VM
```bash
scp -r database_scripts/ azureuser@your-vm-ip:/home/azureuser/
```

### 2. SSH into Azure VM
```bash
ssh azureuser@your-vm-ip
```

### 3. Run Scripts on VM
```bash
cd /home/azureuser/database_scripts
mysql -u root -p < 01_create_database.sql
# ... continue with other scripts
```

## Database Configuration

After running the scripts, update your `.env` file:

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_NAME=tms_db
DB_USER=tms_user
DB_PASSWORD=TMS_Password_2026!  # CHANGE THIS!

# MySQL Connection String
DATABASE_URL=mysql+pymysql://tms_user:TMS_Password_2026!@localhost:3306/tms_db
```

## Security Notes

1. **Change default passwords immediately:**
   - Database user password (in script 02)
   - Admin user password (after first login)

2. **For Azure VM deployment:**
   - Use strong passwords
   - Enable MySQL firewall rules
   - Use SSL connections if possible
   - Restrict remote access to specific IPs

3. **Database user permissions:**
   - The `tms_user` has limited privileges (no GRANT, SUPER, etc.)
   - Only has access to `tms_db` database
   - Cannot modify other databases or users

## Verification

After running all scripts, verify the setup:

```sql
-- Check database
SHOW DATABASES LIKE 'tms_db';

-- Check tables (should show 40+ tables)
USE tms_db;
SHOW TABLES;

-- Check admin user
SELECT * FROM users WHERE username = 'admin';

-- Check module definitions
SELECT COUNT(*) FROM module_definitions;

-- Check permissions
SELECT COUNT(*) FROM permissions;
```

## Troubleshooting

### Error: Database exists
```sql
DROP DATABASE IF EXISTS tms_db;
-- Then re-run script 01
```

### Error: User exists
```sql
DROP USER IF EXISTS 'tms_user'@'localhost';
-- Then re-run script 02
```

### Foreign key errors
Make sure you run scripts in the correct order. Foreign keys depend on parent tables being created first.

### Character set issues
Ensure MySQL server uses UTF8MB4:
```sql
SHOW VARIABLES LIKE 'character_set%';
```

## Backup & Restore

### Create Backup
```bash
mysqldump -u root -p tms_db > tms_backup_$(date +%Y%m%d).sql
```

### Restore from Backup
```bash
mysql -u root -p tms_db < tms_backup_20260102.sql
```

## Support

For issues or questions:
- Check application logs
- Verify MySQL error logs
- Ensure all prerequisites are met
- Confirm scripts ran in correct order

## Database Schema Summary

- **Total Tables:** 40+
- **Core Entities:** Companies, Users, Tenders
- **Modules:** 12 premium features
- **Permissions:** 23 granular permissions
- **Accounting:** Full double-entry system
- **Workflow:** Complete approval workflow
- **Notifications:** Deadline tracking system

## Next Steps

After database setup:

1. **Configure application:**
   - Update `.env` file
   - Test database connection
   - Run Flask migrations (if any)

2. **First login:**
   - Login as admin
   - Change admin password
   - Create your company
   - Create additional users

3. **Enable modules:**
   - Configure company modules
   - Set up billing (if needed)
   - Configure notifications

4. **Security hardening:**
   - Review user permissions
   - Set up SSL/TLS
   - Configure firewall rules
   - Enable audit logging

---

**Last Updated:** January 2, 2026
**Version:** 1.0
**Database:** MySQL 8.0+
