"""
Initialize Tender Workflow & Permissions System
Creates tables and populates with default permissions and roles
"""

import sys
import os
os.environ['WERKZEUG_RUN_MAIN'] = 'true'

from config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Default permissions for the system
DEFAULT_PERMISSIONS = {
    # Tender permissions
    'view_tenders': {
        'display_name': 'View Tenders',
        'description': 'Can view tender list and details',
        'category': 'tenders'
    },
    'create_tenders': {
        'display_name': 'Create Tenders',
        'description': 'Can create new tender opportunities',
        'category': 'tenders'
    },
    'edit_tenders': {
        'display_name': 'Edit Tenders',
        'description': 'Can edit tender details',
        'category': 'tenders'
    },
    'delete_tenders': {
        'display_name': 'Delete Tenders',
        'description': 'Can delete tenders',
        'category': 'tenders'
    },
    'assign_tenders': {
        'display_name': 'Assign Tenders',
        'description': 'Can assign tenders to team members',
        'category': 'tenders'
    },
    'submit_for_approval': {
        'display_name': 'Submit for Approval',
        'description': 'Can submit tenders for approval',
        'category': 'tenders'
    },
    'approve_tenders': {
        'display_name': 'Approve Tenders',
        'description': 'Can approve or reject tender submissions',
        'category': 'tenders'
    },
    'submit_tenders': {
        'display_name': 'Submit Tenders',
        'description': 'Can submit approved tenders to clients',
        'category': 'tenders'
    },
    'upload_documents': {
        'display_name': 'Upload Documents',
        'description': 'Can upload tender documents',
        'category': 'tenders'
    },
    'delete_documents': {
        'display_name': 'Delete Documents',
        'description': 'Can delete tender documents',
        'category': 'tenders'
    },
    'add_comments': {
        'display_name': 'Add Comments',
        'description': 'Can add comments to tenders',
        'category': 'tenders'
    },
    'view_all_tenders': {
        'display_name': 'View All Company Tenders',
        'description': 'Can view all tenders in company (not just assigned)',
        'category': 'tenders'
    },
    
    # User management permissions
    'view_users': {
        'display_name': 'View Users',
        'description': 'Can view company users',
        'category': 'users'
    },
    'create_users': {
        'display_name': 'Create Users',
        'description': 'Can create new users',
        'category': 'users'
    },
    'edit_users': {
        'display_name': 'Edit Users',
        'description': 'Can edit user details',
        'category': 'users'
    },
    'delete_users': {
        'display_name': 'Delete Users',
        'description': 'Can deactivate users',
        'category': 'users'
    },
    'manage_roles': {
        'display_name': 'Manage Roles',
        'description': 'Can create and edit roles',
        'category': 'users'
    },
    'assign_roles': {
        'display_name': 'Assign Roles',
        'description': 'Can assign roles to users',
        'category': 'users'
    },
    
    # Reporting permissions
    'view_reports': {
        'display_name': 'View Reports',
        'description': 'Can view reports and analytics',
        'category': 'reports'
    },
    'export_reports': {
        'display_name': 'Export Reports',
        'description': 'Can export reports to Excel/PDF',
        'category': 'reports'
    },
    'view_analytics': {
        'display_name': 'View Analytics',
        'description': 'Can view analytics dashboard',
        'category': 'analytics'
    },
    
    # Module permissions
    'manage_modules': {
        'display_name': 'Manage Modules',
        'description': 'Can enable/disable company modules',
        'category': 'settings'
    },
    'view_billing': {
        'display_name': 'View Billing',
        'description': 'Can view billing information',
        'category': 'billing'
    },
    'manage_company_settings': {
        'display_name': 'Manage Company Settings',
        'description': 'Can update company profile and settings',
        'category': 'settings'
    },
    
    # Accounting module permissions
    'view_accounting': {
        'display_name': 'View Accounting',
        'description': 'Can view accounting dashboard',
        'category': 'accounting'
    },
    'create_journal_entries': {
        'display_name': 'Create Journal Entries',
        'description': 'Can create journal entries',
        'category': 'accounting'
    },
    'approve_journal_entries': {
        'display_name': 'Approve Journal Entries',
        'description': 'Can approve journal entries',
        'category': 'accounting'
    },
    'view_financial_reports': {
        'display_name': 'View Financial Reports',
        'description': 'Can view income statement and balance sheet',
        'category': 'accounting'
    },
}

# Default role templates
DEFAULT_ROLES = {
    'viewer': {
        'display_name': 'Viewer',
        'description': 'Can only view tenders and reports (read-only)',
        'permissions': ['view_tenders', 'view_reports', 'view_analytics']
    },
    'contributor': {
        'display_name': 'Contributor',
        'description': 'Can work on assigned tenders and upload documents',
        'permissions': [
            'view_tenders', 'edit_tenders', 'upload_documents', 
            'add_comments', 'submit_for_approval', 'view_reports'
        ]
    },
    'team_lead': {
        'display_name': 'Team Lead',
        'description': 'Can view all tenders, assign work, and collaborate',
        'permissions': [
            'view_tenders', 'view_all_tenders', 'create_tenders', 
            'edit_tenders', 'assign_tenders', 'upload_documents',
            'delete_documents', 'add_comments', 'submit_for_approval',
            'view_reports', 'export_reports', 'view_analytics'
        ]
    },
    'approver': {
        'display_name': 'Approver',
        'description': 'Can approve tender submissions before final submission',
        'permissions': [
            'view_tenders', 'view_all_tenders', 'approve_tenders',
            'add_comments', 'view_reports', 'view_analytics'
        ]
    },
    'manager': {
        'display_name': 'Manager',
        'description': 'Can submit tenders and manage team members',
        'permissions': [
            'view_tenders', 'view_all_tenders', 'create_tenders',
            'edit_tenders', 'assign_tenders', 'approve_tenders',
            'submit_tenders', 'upload_documents', 'delete_documents',
            'add_comments', 'view_users', 'view_reports',
            'export_reports', 'view_analytics', 'view_billing'
        ]
    },
    'company_admin': {
        'display_name': 'Company Admin',
        'description': 'Full access to all company features',
        'permissions': [
            'view_tenders', 'view_all_tenders', 'create_tenders',
            'edit_tenders', 'delete_tenders', 'assign_tenders',
            'approve_tenders', 'submit_tenders', 'upload_documents',
            'delete_documents', 'add_comments', 'view_users',
            'create_users', 'edit_users', 'delete_users',
            'manage_roles', 'assign_roles', 'view_reports',
            'export_reports', 'view_analytics', 'manage_modules',
            'view_billing', 'manage_company_settings',
            'view_accounting', 'create_journal_entries',
            'view_financial_reports'
        ]
    },
}


def create_workflow_tables():
    """Create the new workflow and permissions tables"""
    
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    
    with engine.connect() as conn:
        print("="*80)
        print("CREATING TENDER WORKFLOW & PERMISSIONS TABLES")
        print("="*80)
        
        # 1. Permissions table
        print("\n1. Creating permissions table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS permissions (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) UNIQUE NOT NULL,
                display_name VARCHAR(100) NOT NULL,
                description VARCHAR(255),
                category VARCHAR(50),
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()
        print("   ✓ Permissions table created")
        
        # 2. Company roles table
        print("2. Creating company_roles table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS company_roles (
                id INT PRIMARY KEY AUTO_INCREMENT,
                company_id INT NOT NULL,
                name VARCHAR(100) NOT NULL,
                display_name VARCHAR(100) NOT NULL,
                description VARCHAR(255),
                is_system_role BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                UNIQUE KEY unique_role_per_company (company_id, name)
            )
        """))
        conn.commit()
        print("   ✓ Company roles table created")
        
        # 3. Role permissions junction table
        print("3. Creating role_permissions table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS role_permissions (
                id INT PRIMARY KEY AUTO_INCREMENT,
                role_id INT NOT NULL,
                permission_id INT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (role_id) REFERENCES company_roles(id) ON DELETE CASCADE,
                FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
                UNIQUE KEY unique_role_permission (role_id, permission_id)
            )
        """))
        conn.commit()
        print("   ✓ Role permissions table created")
        
        # 4. User company roles junction table
        print("4. Creating user_company_roles table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_company_roles (
                id INT PRIMARY KEY AUTO_INCREMENT,
                user_id INT NOT NULL,
                role_id INT NOT NULL,
                assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                assigned_by INT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (role_id) REFERENCES company_roles(id) ON DELETE CASCADE,
                FOREIGN KEY (assigned_by) REFERENCES users(id) ON DELETE SET NULL,
                UNIQUE KEY unique_user_role (user_id, role_id)
            )
        """))
        conn.commit()
        print("   ✓ User company roles table created")
        
        # 5. Tender assignments table
        print("5. Creating tender_assignments table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tender_assignments (
                id INT PRIMARY KEY AUTO_INCREMENT,
                tender_id INT NOT NULL,
                assigned_to_id INT NOT NULL,
                assigned_by_id INT NOT NULL,
                assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                due_date DATETIME,
                notes TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (tender_id) REFERENCES tenders(id) ON DELETE CASCADE,
                FOREIGN KEY (assigned_to_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (assigned_by_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))
        conn.commit()
        print("   ✓ Tender assignments table created")
        
        # 6. Tender workflows table
        print("6. Creating tender_workflows table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tender_workflows (
                id INT PRIMARY KEY AUTO_INCREMENT,
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
                FOREIGN KEY (submitted_by) REFERENCES users(id) ON DELETE SET NULL
            )
        """))
        conn.commit()
        print("   ✓ Tender workflows table created")
        
        # 7. Tender documents table
        print("7. Creating tender_documents table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tender_documents (
                id INT PRIMARY KEY AUTO_INCREMENT,
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
                FOREIGN KEY (uploaded_by_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))
        conn.commit()
        print("   ✓ Tender documents table created")
        
        # 8. Tender comments table
        print("8. Creating tender_comments table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tender_comments (
                id INT PRIMARY KEY AUTO_INCREMENT,
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
                FOREIGN KEY (parent_comment_id) REFERENCES tender_comments(id) ON DELETE CASCADE
            )
        """))
        conn.commit()
        print("   ✓ Tender comments table created")
        
        # 9. Tender activities table (audit trail)
        print("9. Creating tender_activities table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tender_activities (
                id INT PRIMARY KEY AUTO_INCREMENT,
                tender_id INT NOT NULL,
                user_id INT,
                activity_type VARCHAR(50) NOT NULL,
                description TEXT,
                metadata TEXT,
                ip_address VARCHAR(45),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tender_id) REFERENCES tenders(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """))
        conn.commit()
        print("   ✓ Tender activities table created")
        
        print("\n" + "="*80)
        print("✅ All tables created successfully!")
        print("="*80)


def populate_permissions():
    """Populate permissions table with default permissions"""
    
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("\n" + "="*80)
        print("POPULATING DEFAULT PERMISSIONS")
        print("="*80)
        
        added_count = 0
        
        for perm_name, perm_data in DEFAULT_PERMISSIONS.items():
            # Check if exists
            result = session.execute(
                text("SELECT id FROM permissions WHERE name = :name"),
                {'name': perm_name}
            )
            
            if not result.fetchone():
                session.execute(
                    text("""
                        INSERT INTO permissions (name, display_name, description, category)
                        VALUES (:name, :display_name, :description, :category)
                    """),
                    {
                        'name': perm_name,
                        'display_name': perm_data['display_name'],
                        'description': perm_data['description'],
                        'category': perm_data['category']
                    }
                )
                added_count += 1
                print(f"  + {perm_data['display_name']:40} ({perm_data['category']})")
        
        session.commit()
        
        print("\n" + "="*80)
        print(f"✅ Added {added_count} permissions")
        print("="*80)
        
        return True
        
    except Exception as e:
        session.rollback()
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


def create_default_roles_for_companies():
    """Create default role templates for all active companies"""
    
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("\n" + "="*80)
        print("CREATING DEFAULT ROLES FOR COMPANIES")
        print("="*80)
        
        # Get all active companies
        result = session.execute(
            text("SELECT id, name FROM companies WHERE is_active = 1")
        )
        companies = result.fetchall()
        
        total_roles_created = 0
        
        for company_id, company_name in companies:
            print(f"\n📁 Company: {company_name} (ID: {company_id})")
            roles_created = 0
            
            for role_name, role_data in DEFAULT_ROLES.items():
                # Check if role exists
                result = session.execute(
                    text("""
                        SELECT id FROM company_roles 
                        WHERE company_id = :company_id AND name = :name
                    """),
                    {'company_id': company_id, 'name': role_name}
                )
                
                if not result.fetchone():
                    # Create role
                    result = session.execute(
                        text("""
                            INSERT INTO company_roles 
                            (company_id, name, display_name, description, is_system_role)
                            VALUES (:company_id, :name, :display_name, :description, TRUE)
                        """),
                        {
                            'company_id': company_id,
                            'name': role_name,
                            'display_name': role_data['display_name'],
                            'description': role_data['description']
                        }
                    )
                    role_id = result.lastrowid
                    
                    # Assign permissions to role
                    for perm_name in role_data['permissions']:
                        perm_result = session.execute(
                            text("SELECT id FROM permissions WHERE name = :name"),
                            {'name': perm_name}
                        )
                        perm_row = perm_result.fetchone()
                        
                        if perm_row:
                            session.execute(
                                text("""
                                    INSERT IGNORE INTO role_permissions (role_id, permission_id)
                                    VALUES (:role_id, :permission_id)
                                """),
                                {'role_id': role_id, 'permission_id': perm_row[0]}
                            )
                    
                    roles_created += 1
                    total_roles_created += 1
                    print(f"  + {role_data['display_name']:20} ({len(role_data['permissions'])} permissions)")
        
        session.commit()
        
        print("\n" + "="*80)
        print(f"✅ Created {total_roles_created} roles across {len(companies)} companies")
        print("="*80)
        
        return True
        
    except Exception as e:
        session.rollback()
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


def create_workflows_for_existing_tenders():
    """Create workflow records for existing tenders"""
    
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("\n" + "="*80)
        print("CREATING WORKFLOWS FOR EXISTING TENDERS")
        print("="*80)
        
        # Get tenders without workflows
        result = session.execute(
            text("""
                SELECT t.id, t.title, t.company_id
                FROM tenders t
                LEFT JOIN tender_workflows tw ON t.id = tw.tender_id
                WHERE tw.id IS NULL
            """)
        )
        
        tenders = result.fetchall()
        
        for tender_id, title, company_id in tenders:
            session.execute(
                text("""
                    INSERT INTO tender_workflows (tender_id, status)
                    VALUES (:tender_id, 'in_progress')
                """),
                {'tender_id': tender_id}
            )
            print(f"  + Workflow created for: {title[:50]}")
        
        session.commit()
        
        print("\n" + "="*80)
        print(f"✅ Created {len(tenders)} workflows")
        print("="*80)
        
        return True
        
    except Exception as e:
        session.rollback()
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


if __name__ == '__main__':
    print("\n🚀 INITIALIZING TENDER WORKFLOW & PERMISSIONS SYSTEM\n")
    
    # Step 1: Create tables
    create_workflow_tables()
    
    # Step 2: Populate permissions
    if not populate_permissions():
        sys.exit(1)
    
    # Step 3: Create default roles
    if not create_default_roles_for_companies():
        sys.exit(1)
    
    # Step 4: Create workflows for existing tenders
    if not create_workflows_for_existing_tenders():
        sys.exit(1)
    
    print("\n" + "="*80)
    print("✅ TENDER WORKFLOW & PERMISSIONS SYSTEM INITIALIZED SUCCESSFULLY!")
    print("="*80)
    print("\n📋 NEXT STEPS:")
    print("  1. Assign roles to company users")
    print("  2. Start using tender workflow features:")
    print("     • Assign tenders to team members")
    print("     • Submit tenders for approval")
    print("     • Approve/reject submissions")
    print("     • Submit approved tenders to clients")
    print("  3. Manage permissions through company roles")
    print("="*80)
    
    sys.exit(0)
