"""
Standalone script to initialize the accounting module
This runs independently without starting the Flask app
"""

import sys
from config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Module definition for accounting
ACCOUNTING_MODULE = {
    'name': 'accounting',
    'display_name': 'Accounting',
    'description': 'General ledger, journal entries, and financial statements',
    'is_core': False
}

def initialize_accounting_module():
    """Initialize the accounting module directly in the database"""
    
    # Create database connection
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("Checking accounting module in database...")
        
        # Check if accounting module already exists
        result = session.execute(
            text("SELECT id FROM module_definitions WHERE module_name = 'accounting'")
        )
        existing = result.fetchone()
        
        if existing:
            print(f"✓ Accounting module already exists (ID: {existing[0]})")
        else:
            # Insert accounting module
            session.execute(
                text("""
                    INSERT INTO module_definitions (module_name, display_name, description, is_core, category, monthly_price, sort_order, is_active)
                    VALUES (:module_name, :display_name, :description, :is_core, :category, :monthly_price, :sort_order, :is_active)
                """),
                {
                    'module_name': ACCOUNTING_MODULE['name'],
                    'display_name': ACCOUNTING_MODULE['display_name'],
                    'description': ACCOUNTING_MODULE['description'],
                    'is_core': ACCOUNTING_MODULE['is_core'],
                    'category': 'feature',
                    'monthly_price': 0.00,
                    'sort_order': 100,
                    'is_active': True
                }
            )
            session.commit()
            print("✓ Accounting module created successfully!")
        
        print("\n" + "="*50)
        print("✅ Accounting module is ready!")
        print("="*50)
        print("\nNext steps:")
        print("1. Go to Admin > Billing > Manage Modules")
        print("2. Enable the 'Accounting' module for companies")
        print("3. Companies will see the Accounting menu once enabled")
        print("\nNote: The Flask app will auto-reload and pick up the changes")
        
    except Exception as e:
        session.rollback()
        print(f"✗ Error initializing accounting module: {e}")
        sys.exit(1)
    finally:
        session.close()

if __name__ == '__main__':
    initialize_accounting_module()
