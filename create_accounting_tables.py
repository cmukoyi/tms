"""
Create accounting tables migration script
Run this to create the accounting-related database tables
"""

from app import app
from models import db

def create_accounting_tables():
    """Create all accounting tables"""
    with app.app_context():
        print("Creating accounting tables...")
        
        # Create all tables defined in models
        db.create_all()
        
        print("✓ Accounting tables created successfully!")
        print("\nTables created:")
        print("  - account_types")
        print("  - accounts")
        print("  - journal_entries")
        print("  - transactions")
        print("\nNext steps:")
        print("1. Run: python init_accounting.py")
        print("2. Log in to your app and go to Accounting menu")

if __name__ == '__main__':
    create_accounting_tables()
