"""
Initialize the accounting module in the system
Run this after adding the accounting module to enable it for companies
"""

from app import app
from models import db
from services.module_service import ModuleService

def initialize_accounting_module():
    """Initialize the accounting module"""
    with app.app_context():
        print("Initializing accounting module...")
        
        # Initialize modules (this will add accounting if not present)
        success = ModuleService.initialize_modules()
        
        if success:
            print("✓ Accounting module initialized successfully!")
            print("\nYou can now:")
            print("1. Go to Admin > Billing > Manage Modules")
            print("2. Enable the 'Accounting' module for companies")
            print("3. Companies will see the Accounting menu once enabled")
        else:
            print("✗ Failed to initialize accounting module")

if __name__ == '__main__':
    initialize_accounting_module()
