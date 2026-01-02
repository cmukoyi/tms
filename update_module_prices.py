"""
Update module prices for South African Rand (ZAR)
Set reasonable monthly pricing for all modules
"""

import sys
import os
os.environ['WERKZEUG_RUN_MAIN'] = 'true'

from config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Module pricing in ZAR (South African Rand)
MODULE_PRICES = {
    # Core modules - typically free but companies pay for system access
    'dashboard': 0.00,
    'tenders': 0.00,
    'tender_management': 0.00,
    'user_management': 0.00,
    
    # Feature modules - reasonable monthly pricing
    'accounting': 499.00,  # Comprehensive accounting system
    'advanced_search': 149.00,
    'analytics': 299.00,
    'api_access': 799.00,  # Premium feature
    'audit_tracking': 199.00,
    'bulk_operations': 249.00,
    'company_management': 99.00,
    'custom_fields': 149.00,
    'document_management': 199.00,
    'email_notifications': 99.00,
    'export_data': 149.00,
    'files': 99.00,
    'notes_comments': 79.00,
    'notifications': 99.00,
    'reporting': 299.00,
    'reports': 299.00,
    'tender_history': 149.00,
    'white_labeling': 999.00,  # Premium feature
}

def update_module_prices():
    """Update monthly prices for all modules"""
    
    # Create database connection
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("="*70)
        print("MODULE PRICING UPDATE - ZAR (South African Rand)")
        print("="*70)
        
        # Get all modules
        result = session.execute(
            text("SELECT id, module_name, display_name, monthly_price, is_core FROM module_definitions ORDER BY module_name")
        )
        modules = result.fetchall()
        
        print(f"\n📊 Found {len(modules)} modules in database\n")
        
        updated_count = 0
        for module in modules:
            module_id, module_name, display_name, current_price, is_core = module
            
            # Get new price from dictionary or keep current
            new_price = MODULE_PRICES.get(module_name, float(current_price) if current_price else 0.00)
            
            # Update if price has changed
            if float(current_price or 0) != new_price:
                session.execute(
                    text("UPDATE module_definitions SET monthly_price = :price WHERE id = :id"),
                    {'price': new_price, 'id': module_id}
                )
                updated_count += 1
                
                # Show pricing info
                core_badge = "CORE" if is_core else "Optional"
                price_old = f"R{current_price:.2f}" if current_price else "R0.00"
                price_new = f"R{new_price:.2f}"
                
                if new_price == 0:
                    print(f"✓ {module_name:25} | {display_name:30} | {core_badge:8} | {price_old:10} → {price_new} (FREE)")
                else:
                    print(f"✓ {module_name:25} | {display_name:30} | {core_badge:8} | {price_old:10} → {price_new}")
            else:
                # No change needed
                price_str = f"R{new_price:.2f}" if new_price > 0 else "FREE"
                core_badge = "CORE" if is_core else "Optional"
                print(f"  {module_name:25} | {display_name:30} | {core_badge:8} | {price_str:10} (unchanged)")
        
        session.commit()
        
        print("\n" + "="*70)
        print(f"✅ Updated {updated_count} module prices")
        print("="*70)
        
        # Show pricing summary
        print("\n📈 PRICING SUMMARY:")
        print("-" * 70)
        
        result = session.execute(
            text("""
                SELECT 
                    CASE 
                        WHEN is_core = 1 THEN 'Core (Free)'
                        WHEN monthly_price = 0 THEN 'Free Modules'
                        WHEN monthly_price < 200 THEN 'Basic (< R200)'
                        WHEN monthly_price < 500 THEN 'Standard (R200-R500)'
                        ELSE 'Premium (> R500)'
                    END as tier,
                    COUNT(*) as count,
                    SUM(monthly_price) as total_revenue
                FROM module_definitions
                WHERE is_active = 1
                GROUP BY tier
                ORDER BY total_revenue DESC
            """)
        )
        
        for tier, count, revenue in result:
            print(f"{tier:25} | {count:2} modules | R{revenue:8.2f}/month per company")
        
        # Calculate potential revenue
        result = session.execute(
            text("SELECT COUNT(*) FROM companies WHERE is_active = 1")
        )
        company_count = result.scalar()
        
        result = session.execute(
            text("SELECT SUM(monthly_price) FROM module_definitions WHERE is_active = 1 AND is_core = 0")
        )
        total_optional_revenue = result.scalar() or 0
        
        print("\n" + "="*70)
        print(f"🏢 Active Companies: {company_count}")
        print(f"💰 Max Monthly Revenue: R{total_optional_revenue:.2f} per company")
        print(f"💼 Potential Total Revenue: R{total_optional_revenue * company_count:.2f}/month")
        print("="*70)
        
        print("\n✅ Module pricing updated successfully!")
        print("\n💡 Companies will be billed based on their enabled modules")
        print("   → Admin > Billing > Generate Bill")
        
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
    success = update_module_prices()
    sys.exit(0 if success else 1)
