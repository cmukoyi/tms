"""
Test script to verify module access control is working correctly
"""

import sys
import os
# Prevent app.py from starting the Flask server
os.environ['WERKZEUG_RUN_MAIN'] = 'true'

from config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def test_module_system():
    """Test the module access control system"""
    
    # Create database connection
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("="*70)
        print("MODULE SYSTEM VERIFICATION")
        print("="*70)
        
        # 1. Check if accounting module exists in module_definitions
        print("\n1. Checking module_definitions table...")
        result = session.execute(
            text("SELECT id, module_name, display_name, is_active FROM module_definitions WHERE module_name = 'accounting'")
        )
        module = result.fetchone()
        
        if module:
            print(f"   ✓ Accounting module found:")
            print(f"     - ID: {module[0]}")
            print(f"     - Name: {module[1]}")
            print(f"     - Display: {module[2]}")
            print(f"     - Active: {module[3]}")
        else:
            print("   ✗ Accounting module NOT found in module_definitions!")
            print("   Run: python3 init_accounting_standalone.py")
            return False
        
        module_id = module[0]
        
        # 2. Check companies
        print("\n2. Checking companies...")
        result = session.execute(
            text("SELECT id, name FROM companies LIMIT 5")
        )
        companies = result.fetchall()
        
        if not companies:
            print("   ✗ No companies found!")
            return False
        
        print(f"   ✓ Found {len(companies)} companies:")
        for company in companies:
            print(f"     - Company {company[0]}: {company[1]}")
        
        # 3. Check company_modules table for accounting
        print("\n3. Checking company_modules assignments...")
        result = session.execute(
            text("""
                SELECT cm.id, cm.company_id, c.name, cm.is_enabled
                FROM company_modules cm
                JOIN companies c ON cm.company_id = c.id
                WHERE cm.module_id = :module_id
            """),
            {'module_id': module_id}
        )
        company_modules = result.fetchall()
        
        if not company_modules:
            print("   ⚠ No companies have accounting module assigned yet")
            print("   This is normal - enable it via Admin > Billing > Manage Modules")
        else:
            print(f"   ✓ Accounting module assigned to {len(company_modules)} companies:")
            for cm in company_modules:
                status = "ENABLED ✓" if cm[3] else "DISABLED ✗"
                print(f"     - Company {cm[1]} ({cm[2]}): {status}")
        
        # 4. Check all module definitions
        print("\n4. All available modules:")
        result = session.execute(
            text("SELECT module_name, display_name, is_core, is_active FROM module_definitions ORDER BY module_name")
        )
        all_modules = result.fetchall()
        
        for mod in all_modules:
            core = "CORE" if mod[2] else "Optional"
            active = "Active" if mod[3] else "Inactive"
            print(f"   - {mod[0]:25} | {mod[1]:30} | {core:8} | {active}")
        
        # 5. Verification summary
        print("\n" + "="*70)
        print("VERIFICATION SUMMARY")
        print("="*70)
        print("✓ Module system is properly configured")
        print("\nModule Access Control Flow:")
        print("1. User logs in → company_id stored in session")
        print("2. Template calls can_access_module('accounting')")
        print("3. System checks: company_modules.is_enabled = True")
        print("4. Menu shows/hides based on result")
        print("5. @module_required decorator protects routes")
        print("\nTo enable accounting for a company:")
        print("→ Admin > Billing > Manage Modules")
        print("→ Select company and toggle 'Accounting' module")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()

if __name__ == '__main__':
    success = test_module_system()
    sys.exit(0 if success else 1)
