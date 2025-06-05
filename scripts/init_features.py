# init_features.py - Run this script to initialize default features

from app import app  # Import your Flask app
from models import db, Feature, Company

def init_default_features():
    """Initialize default features in the database"""
    
    default_features = [
        {
            'name': 'Dashboard',
            'code': 'dashboard',
            'description': 'Access to main dashboard with overview statistics',
            'category': 'dashboard'
        },
        {
            'name': 'Tender Management',
            'code': 'tenders',
            'description': 'Create, edit, and manage tenders',
            'category': 'tenders'
        },
        {
            'name': 'File Management',
            'code': 'files',
            'description': 'Upload and manage tender documents and files',
            'category': 'files'
        },
        {
            'name': 'Reports',
            'code': 'reports',
            'description': 'Generate and view various reports',
            'category': 'reports'
        },
        {
            'name': 'Analytics',
            'code': 'analytics',
            'description': 'Advanced analytics and insights',
            'category': 'analytics'
        },
        {
            'name': 'User Management',
            'code': 'user_management',
            'description': 'Manage company users and permissions',
            'category': 'users'
        },
        {
            'name': 'API Access',
            'code': 'api_access',
            'description': 'Access to REST API endpoints',
            'category': 'api'
        },
        {
            'name': 'Email Notifications',
            'code': 'email_notifications',
            'description': 'Automated email notifications for tender updates',
            'category': 'integrations'
        },
        {
            'name': 'Tender History',
            'code': 'tender_history',
            'description': 'View detailed history and audit trail',
            'category': 'advanced'
        },
        {
            'name': 'Custom Fields',
            'code': 'custom_fields',
            'description': 'Create custom fields for tenders',
            'category': 'advanced'
        },
        {
            'name': 'Bulk Operations',
            'code': 'bulk_operations',
            'description': 'Perform bulk actions on multiple tenders',
            'category': 'advanced'
        },
        {
            'name': 'Export Data',
            'code': 'export_data',
            'description': 'Export tender data to Excel, CSV, PDF',
            'category': 'reports'
        }
    ]
    
    with app.app_context():
        print("Initializing default features...")
        
        for feature_data in default_features:
            # Check if feature already exists
            existing_feature = Feature.query.filter_by(code=feature_data['code']).first()
            
            if not existing_feature:
                feature = Feature(
                    name=feature_data['name'],
                    code=feature_data['code'],
                    description=feature_data['description'],
                    category=feature_data['category'],
                    is_active=True
                )
                db.session.add(feature)
                print(f"✅ Added feature: {feature_data['name']}")
            else:
                print(f"⚠️  Feature already exists: {feature_data['name']}")
        
        try:
            db.session.commit()
            print("\n🎉 Default features initialized successfully!")
            
            # Show summary
            total_features = Feature.query.count()
            print(f"📊 Total features in database: {total_features}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error initializing features: {str(e)}")

def enable_basic_features_for_all_companies():
    """Enable basic features for all existing companies"""
    
    basic_features = ['dashboard', 'tenders']  # Basic features every company should have
    
    with app.app_context():
        print("\nEnabling basic features for all companies...")
        
        companies = Company.query.filter_by(is_active=True).all()
        
        for company in companies:
            for feature_code in basic_features:
                if company.enable_feature(feature_code):
                    print(f"✅ Enabled {feature_code} for {company.name}")
                else:
                    print(f"⚠️  Failed to enable {feature_code} for {company.name}")
        
        print(f"\n🎉 Basic features enabled for {len(companies)} companies!")

def show_feature_summary():
    """Show summary of all features and which companies have them"""
    
    with app.app_context():
        print("\n" + "="*60)
        print("FEATURE SUMMARY")
        print("="*60)
        
        features = Feature.query.order_by(Feature.category, Feature.name).all()
        companies = Company.query.filter_by(is_active=True).all()
        
        for feature in features:
            companies_with_feature = []
            for company in companies:
                if company.has_feature(feature.code):
                    companies_with_feature.append(company.name)
            
            print(f"\n📋 {feature.name} ({feature.code})")
            print(f"   Category: {feature.category}")
            print(f"   Description: {feature.description}")
            print(f"   Status: {'✅ Active' if feature.is_active else '❌ Inactive'}")
            print(f"   Companies: {len(companies_with_feature)}/{len(companies)}")
            if companies_with_feature:
                print(f"   -> {', '.join(companies_with_feature)}")

if __name__ == "__main__":
    print("🚀 TMS Feature Management Initialization")
    print("="*50)
    
    # Initialize default features
    init_default_features()
    
    # Enable basic features for all companies
    enable_basic_features_for_all_companies()
    
    # Show summary
    show_feature_summary()
    
    print("\n" + "="*50)
    print("✅ Feature management system ready!")
    print("\nNext steps:")
    print("1. Run database migration: flask db upgrade")
    print("2. Access admin panel: /admin/companies")
    print("3. Configure features for each company")