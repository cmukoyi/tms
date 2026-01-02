"""
Initialize accounting module with default account types
Run this script once to set up the accounting system
"""

from app import app
from models import db, AccountType

def initialize_account_types():
    """Initialize default account types"""
    with app.app_context():
        # Check if account types already exist
        existing_count = AccountType.query.count()
        if existing_count > 0:
            print(f"Account types already initialized ({existing_count} types found)")
            return
        
        account_types = [
            # Assets
            {'name': 'Cash', 'category': 'asset', 'normal_balance': 'debit', 
             'description': 'Cash on hand and in bank accounts'},
            {'name': 'Accounts Receivable', 'category': 'asset', 'normal_balance': 'debit',
             'description': 'Money owed to the company by customers'},
            {'name': 'Inventory', 'category': 'asset', 'normal_balance': 'debit',
             'description': 'Goods available for sale'},
            {'name': 'Prepaid Expenses', 'category': 'asset', 'normal_balance': 'debit',
             'description': 'Expenses paid in advance'},
            {'name': 'Fixed Assets', 'category': 'asset', 'normal_balance': 'debit',
             'description': 'Property, equipment, and long-term assets'},
            
            # Liabilities
            {'name': 'Accounts Payable', 'category': 'liability', 'normal_balance': 'credit',
             'description': 'Money owed to suppliers'},
            {'name': 'Short-term Loans', 'category': 'liability', 'normal_balance': 'credit',
             'description': 'Loans payable within one year'},
            {'name': 'Long-term Loans', 'category': 'liability', 'normal_balance': 'credit',
             'description': 'Loans payable after one year'},
            {'name': 'Accrued Expenses', 'category': 'liability', 'normal_balance': 'credit',
             'description': 'Expenses incurred but not yet paid'},
            
            # Equity
            {'name': 'Owner Equity', 'category': 'equity', 'normal_balance': 'credit',
             'description': 'Owner\'s investment in the business'},
            {'name': 'Retained Earnings', 'category': 'equity', 'normal_balance': 'credit',
             'description': 'Accumulated profits retained in the business'},
            {'name': 'Drawings', 'category': 'equity', 'normal_balance': 'debit',
             'description': 'Withdrawals by owner'},
            
            # Revenue
            {'name': 'Sales Revenue', 'category': 'revenue', 'normal_balance': 'credit',
             'description': 'Revenue from sales of goods/services'},
            {'name': 'Service Revenue', 'category': 'revenue', 'normal_balance': 'credit',
             'description': 'Revenue from providing services'},
            {'name': 'Other Income', 'category': 'revenue', 'normal_balance': 'credit',
             'description': 'Miscellaneous income'},
            
            # Expenses
            {'name': 'Cost of Goods Sold', 'category': 'expense', 'normal_balance': 'debit',
             'description': 'Direct costs of producing goods sold'},
            {'name': 'Salaries Expense', 'category': 'expense', 'normal_balance': 'debit',
             'description': 'Employee wages and salaries'},
            {'name': 'Rent Expense', 'category': 'expense', 'normal_balance': 'debit',
             'description': 'Rent payments for facilities'},
            {'name': 'Utilities Expense', 'category': 'expense', 'normal_balance': 'debit',
             'description': 'Electricity, water, internet, etc.'},
            {'name': 'Office Supplies', 'category': 'expense', 'normal_balance': 'debit',
             'description': 'Supplies used in office operations'},
            {'name': 'Marketing Expense', 'category': 'expense', 'normal_balance': 'debit',
             'description': 'Advertising and marketing costs'},
            {'name': 'Insurance Expense', 'category': 'expense', 'normal_balance': 'debit',
             'description': 'Insurance premiums'},
            {'name': 'Depreciation Expense', 'category': 'expense', 'normal_balance': 'debit',
             'description': 'Depreciation of fixed assets'},
            {'name': 'Professional Fees', 'category': 'expense', 'normal_balance': 'debit',
             'description': 'Legal, accounting, consulting fees'},
            {'name': 'Bank Charges', 'category': 'expense', 'normal_balance': 'debit',
             'description': 'Bank service fees and charges'},
            {'name': 'Miscellaneous Expense', 'category': 'expense', 'normal_balance': 'debit',
             'description': 'Other business expenses'},
        ]
        
        for acc_type_data in account_types:
            acc_type = AccountType(**acc_type_data)
            db.session.add(acc_type)
        
        db.session.commit()
        print(f"Successfully initialized {len(account_types)} account types")
        
        # Print summary
        print("\nAccount Types Summary:")
        for category in ['asset', 'liability', 'equity', 'revenue', 'expense']:
            count = AccountType.query.filter_by(category=category).count()
            print(f"  {category.title()}: {count} types")

if __name__ == '__main__':
    initialize_account_types()
