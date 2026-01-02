"""
Add premium modules to the system
Run this to add AI-powered and advanced features
"""

import sys
import os
os.environ['WERKZEUG_RUN_MAIN'] = 'true'

from config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Premium modules with pricing in ZAR
PREMIUM_MODULES = {
    # Game-changing AI modules
    'ai_tender_writer': {
        'display_name': 'AI Tender Writing Assistant',
        'description': 'AI-powered bid response generator with quality scoring and content suggestions',
        'category': 'premium',
        'monthly_price': 1499.00,
        'is_core': False,
        'sort_order': 100
    },
    'smart_document_intelligence': {
        'display_name': 'Smart Document Intelligence',
        'description': 'Auto-extract requirements from PDFs, create compliance checklists, OCR support',
        'category': 'premium',
        'monthly_price': 999.00,
        'is_core': False,
        'sort_order': 101
    },
    'predictive_scoring': {
        'display_name': 'Predictive Bid Success Scoring',
        'description': 'AI predicts win probability and suggests which tenders to pursue',
        'category': 'premium',
        'monthly_price': 1299.00,
        'is_core': False,
        'sort_order': 102
    },
    'competitive_intelligence': {
        'display_name': 'Competitive Intelligence Hub',
        'description': 'Track competitor patterns, analyze win rates, price benchmarking',
        'category': 'premium',
        'monthly_price': 1999.00,
        'is_core': False,
        'sort_order': 103
    },
    
    # High-value modules
    'collaborative_workspace': {
        'display_name': 'Collaborative Bid Workspace',
        'description': 'Real-time multi-user editing, comments, task assignments, approval workflows',
        'category': 'feature',
        'monthly_price': 599.00,
        'is_core': False,
        'sort_order': 110
    },
    'tender_scraper': {
        'display_name': 'Tender Opportunity Scraper',
        'description': 'Auto-scrape government portals, email alerts, auto-import opportunities',
        'category': 'feature',
        'monthly_price': 799.00,
        'is_core': False,
        'sort_order': 111
    },
    'win_loss_analytics': {
        'display_name': 'Win/Loss Analytics Dashboard',
        'description': 'Win rate analysis, revenue forecasting, conversion funnel, profitability tracking',
        'category': 'feature',
        'monthly_price': 699.00,
        'is_core': False,
        'sort_order': 112
    },
    'esignature_workflows': {
        'display_name': 'Electronic Signature & Workflows',
        'description': 'E-signatures, digital approvals, legally binding, audit trail',
        'category': 'feature',
        'monthly_price': 549.00,
        'is_core': False,
        'sort_order': 113
    },
    
    # Productivity boosters
    'template_library': {
        'display_name': 'Template Library & Auto-Fill',
        'description': 'Reusable templates, auto-population, 100+ professional templates',
        'category': 'feature',
        'monthly_price': 299.00,
        'is_core': False,
        'sort_order': 120
    },
    'mobile_app': {
        'display_name': 'Mobile Tender App',
        'description': 'iOS & Android apps, offline mode, push notifications, mobile uploads',
        'category': 'feature',
        'monthly_price': 399.00,
        'is_core': False,
        'sort_order': 121
    },
    'email_calendar_integration': {
        'display_name': 'Email & Calendar Integration',
        'description': 'Sync with Outlook/Gmail, auto-calendar events, email imports',
        'category': 'feature',
        'monthly_price': 249.00,
        'is_core': False,
        'sort_order': 122
    },
    'crm_module': {
        'display_name': 'Client Relationship Manager',
        'description': 'Track interactions, client history, follow-ups, relationship scoring',
        'category': 'feature',
        'monthly_price': 499.00,
        'is_core': False,
        'sort_order': 123
    },
    
    # Specialized modules
    'compliance_qa': {
        'display_name': 'Compliance & Quality Assurance',
        'description': 'Auto-checklists, quality workflows, ISO/B-BBEE tracking, validation',
        'category': 'feature',
        'monthly_price': 549.00,
        'is_core': False,
        'sort_order': 130
    },
    'resource_planner': {
        'display_name': 'Resource & Team Capacity Planner',
        'description': 'Workload calendar, resource allocation, skill matching, conflict detection',
        'category': 'feature',
        'monthly_price': 449.00,
        'is_core': False,
        'sort_order': 131
    },
    'vendor_portal': {
        'display_name': 'Vendor & Subcontractor Portal',
        'description': 'Collaborate with vendors, collect quotes, compare pricing, performance ratings',
        'category': 'feature',
        'monthly_price': 599.00,
        'is_core': False,
        'sort_order': 132
    },
    'bbbee_tracker': {
        'display_name': 'B-BBEE Scorecard Tracker',
        'description': 'B-BBEE calculator, track ownership/skills dev, certificate alerts',
        'category': 'feature',
        'monthly_price': 399.00,
        'is_core': False,
        'sort_order': 133
    },
    'financial_proposal': {
        'display_name': 'Financial Proposal Builder',
        'description': 'Pricing calculator, BOQ builder, markup calculator, multi-currency',
        'category': 'feature',
        'monthly_price': 699.00,
        'is_core': False,
        'sort_order': 134
    },
    'multi_language': {
        'display_name': 'Multi-Language Support',
        'description': 'English, Afrikaans, Zulu, Xhosa, Sotho - interface and documents',
        'category': 'feature',
        'monthly_price': 399.00,
        'is_core': False,
        'sort_order': 140
    },
    'advanced_reporting': {
        'display_name': 'Advanced Reporting Studio',
        'description': 'Custom report builder, scheduled reports, executive dashboards',
        'category': 'feature',
        'monthly_price': 799.00,
        'is_core': False,
        'sort_order': 141
    }
}

def add_premium_modules():
    """Add all premium modules to the database"""
    
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("="*80)
        print("ADDING PREMIUM MODULES TO TMS")
        print("="*80)
        
        added_count = 0
        updated_count = 0
        total_new_revenue = 0
        
        for module_name, config in PREMIUM_MODULES.items():
            # Check if module exists
            result = session.execute(
                text("SELECT id, monthly_price FROM module_definitions WHERE module_name = :name"),
                {'name': module_name}
            )
            existing = result.fetchone()
            
            if existing:
                # Update existing
                session.execute(
                    text("""
                        UPDATE module_definitions 
                        SET display_name = :display_name,
                            description = :description,
                            category = :category,
                            monthly_price = :price,
                            sort_order = :sort_order
                        WHERE module_name = :name
                    """),
                    {
                        'name': module_name,
                        'display_name': config['display_name'],
                        'description': config['description'],
                        'category': config['category'],
                        'price': config['monthly_price'],
                        'sort_order': config['sort_order']
                    }
                )
                updated_count += 1
                print(f"✓ Updated: {config['display_name']:45} | R{config['monthly_price']:8.2f}/month")
            else:
                # Insert new
                session.execute(
                    text("""
                        INSERT INTO module_definitions 
                        (module_name, display_name, description, category, monthly_price, 
                         is_core, sort_order, is_active, created_at)
                        VALUES 
                        (:name, :display_name, :description, :category, :price,
                         :is_core, :sort_order, 1, NOW())
                    """),
                    {
                        'name': module_name,
                        'display_name': config['display_name'],
                        'description': config['description'],
                        'category': config['category'],
                        'price': config['monthly_price'],
                        'is_core': config['is_core'],
                        'sort_order': config['sort_order']
                    }
                )
                added_count += 1
                total_new_revenue += config['monthly_price']
                print(f"+ Added:   {config['display_name']:45} | R{config['monthly_price']:8.2f}/month")
        
        session.commit()
        
        print("\n" + "="*80)
        print(f"✅ Successfully added {added_count} new modules")
        print(f"✅ Updated {updated_count} existing modules")
        print("="*80)
        
        # Show pricing tiers
        print("\n📊 PRICING TIERS:")
        print("-" * 80)
        
        result = session.execute(
            text("""
                SELECT 
                    CASE 
                        WHEN monthly_price >= 1000 THEN 'Premium (R1,000+)'
                        WHEN monthly_price >= 500 THEN 'Standard (R500-R999)'
                        WHEN monthly_price >= 200 THEN 'Basic (R200-R499)'
                        ELSE 'Entry (< R200)'
                    END as tier,
                    COUNT(*) as count,
                    SUM(monthly_price) as total
                FROM module_definitions
                WHERE is_active = 1 AND is_core = 0
                GROUP BY tier
                ORDER BY total DESC
            """)
        )
        
        grand_total = 0
        for tier, count, total in result:
            grand_total += total
            print(f"{tier:25} | {count:2} modules | R{total:10.2f}/month")
        
        print("-" * 80)
        print(f"{'TOTAL OPTIONAL MODULES':25} | {''} | R{grand_total:10.2f}/month per company")
        
        # Calculate potential
        result = session.execute(text("SELECT COUNT(*) FROM companies WHERE is_active = 1"))
        company_count = result.scalar()
        
        print("\n" + "="*80)
        print(f"🏢 Active Companies: {company_count}")
        print(f"💰 Max Revenue Per Company: R{grand_total:.2f}/month")
        print(f"💼 Potential Total Revenue: R{grand_total * company_count:,.2f}/month")
        print(f"📈 Annual Potential: R{grand_total * company_count * 12:,.2f}/year")
        print("="*80)
        
        print("\n🎯 TOP SELLING POINTS:")
        print("-" * 80)
        print("1. AI Tender Writing Assistant - Write bids 70% faster")
        print("2. Predictive Success Scoring - Know your win probability")
        print("3. Competitive Intelligence - Track all competitors")
        print("4. Tender Scraper - Never miss an opportunity")
        print("5. B-BBEE Tracker - Essential for SA government tenders")
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
    success = add_premium_modules()
    sys.exit(0 if success else 1)
