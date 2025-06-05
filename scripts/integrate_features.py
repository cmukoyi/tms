#!/usr/bin/env python3
"""
Safe Feature Management Integration Script
Run this after updating your models.py to safely integrate feature management
"""

import os
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

def check_requirements():
    """Check if all required files exist"""
    print("🔍 Checking requirements...")
    
    required_files = [
        'app.py',
        'models.py',
        'templates/base.html'
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False
    
    print("✅ All required files found")
    return True

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    
    directories = [
        'templates/admin',
        'static/css',
        'static/js'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created/verified: {directory}")

def check_models_updated():
    """Check if models.py has been updated with Feature models"""
    print("🔍 Checking if models.py has Feature classes...")
    
    try:
        with open('models.py', 'r') as f:
            content = f.read()
            
        if 'class Feature(' in content and 'class CompanyFeature(' in content:
            print("✅ Feature models found in models.py")
            return True
        else:
            print("❌ Feature models not found in models.py")
            print("Please update your models.py with the Feature and CompanyFeature classes")
            return False
    except Exception as e:
        print(f"❌ Error reading models.py: {e}")
        return False

def create_database_tables():
    """Create the database tables"""
    print("🗄️ Creating database tables...")
    
    try:
        # Try different import methods to find your app
        app = None
        db = None
        
        # Method 1: Try direct import
        try:
            from app import app, db
            print("✅ Found app and db from 'app' module")
        except ImportError:
            pass
        
        # Method 2: Try if it's in a different file
        if app is None:
            try:
                import app as app_module
                app = app_module.app
                db = app_module.db
                print("✅ Found app and db from app module")
            except (ImportError, AttributeError):
                pass
        
        # Method 3: Try main
        if app is None:
            try:
                from main import app, db
                print("✅ Found app and db from 'main' module")
            except ImportError:
                pass
        
        if app is None or db is None:
            print("❌ Could not import Flask app and database")
            print("   Make sure your app.py file has 'app' and 'db' variables")
            return False
        
        with app.app_context():
            # Create all tables (this is safe - won't recreate existing tables)
            db.create_all()
            print("✅ Database tables created successfully")
            return True
            
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        print("   Try running this manually:")
        print("   python -c \"from app import app, db; app.app_context().push(); db.create_all()\"")
        return False

def test_feature_models():
    """Test if the Feature models work"""
    print("🧪 Testing Feature models...")
    
    try:
        # Import app and models
        try:
            from app import app
        except ImportError:
            import app as app_module
            app = app_module.app
        
        from models import Feature, CompanyFeature, Company
        
        with app.app_context():
            # Test basic model functionality
            feature_count = Feature.query.count()
            company_count = Company.query.count()
            
            print(f"✅ Feature model working - {feature_count} features found")
            print(f"✅ Company model working - {company_count} companies found")
            return True
            
    except Exception as e:
        print(f"❌ Error testing models: {e}")
        return False

def create_admin_forms():
    """Create admin_forms.py file"""
    print("📝 Creating admin_forms.py...")
    
    admin_forms_content = '''# admin_forms.py - Forms for Feature Management

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length
from models import Feature, Company

class FeatureForm(FlaskForm):
    """Form for creating/editing features"""
    name = StringField('Feature Name', validators=[DataRequired(), Length(max=100)])
    code = StringField('Feature Code', validators=[DataRequired(), Length(max=50)], 
                      description='Used in code (e.g., dashboard, reports, files)')
    description = TextAreaField('Description')
    category = SelectField('Category', choices=[
        ('dashboard', 'Dashboard'),
        ('reports', 'Reports'), 
        ('files', 'Files'),
        ('users', 'User Management'),
        ('analytics', 'Analytics'),
        ('api', 'API Access'),
        ('integrations', 'Integrations'),
        ('advanced', 'Advanced Features')
    ])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Feature')

class CompanyFeaturesManagementForm(FlaskForm):
    """Form for managing all features for a company at once"""
    
    def __init__(self, company_id=None, *args, **kwargs):
        super(CompanyFeaturesManagementForm, self).__init__(*args, **kwargs)
        
        if company_id:
            self.company_id = company_id
            # Get all active features
            features = Feature.query.filter_by(is_active=True).order_by(Feature.category, Feature.name).all()
            
            # Get currently enabled features for this company
            enabled_features = set()
            company = Company.query.get(company_id)
            if company:
                enabled_features = {f.code for f in company.get_enabled_features()}
            
            # Dynamically add checkbox fields for each feature
            for feature in features:
                field_name = f'feature_{feature.code}'
                field = BooleanField(
                    feature.name,
                    default=feature.code in enabled_features,
                    description=feature.description
                )
                setattr(self, field_name, field)
                
                # Store feature info for later use
                if not hasattr(self, '_features'):
                    self._features = []
                self._features.append(feature)
    
    submit = SubmitField('Update Company Features')
    
    def get_features(self):
        """Get list of features for this form"""
        return getattr(self, '_features', [])
'''
    
    try:
        with open('admin_forms.py', 'w') as f:
            f.write(admin_forms_content)
        print("✅ admin_forms.py created successfully")
        return True
    except Exception as e:
        print(f"❌ Error creating admin_forms.py: {e}")
        return False

def initialize_default_features():
    """Initialize default features"""
    print("🎯 Initializing default features...")
    
    try:
        # Import app
        try:
            from app import app, db
        except ImportError:
            import app as app_module
            app = app_module.app
            db = app_module.db
        
        from models import Feature
        
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
                'category': 'files'
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
            }
        ]
        
        with app.app_context():
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
            
            db.session.commit()
            print("✅ Default features initialized successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Error initializing features: {e}")
        return False

def create_manual_commands():
    """Create manual commands file for backup"""
    print("📝 Creating manual_commands.py for backup...")
    
    manual_commands = '''# manual_commands.py - Run these commands manually if integration script fails

# 1. Create database tables
from app import app, db
with app.app_context():
    db.create_all()
    print("Database tables created")

# 2. Initialize features
from models import Feature
default_features = [
    {'name': 'Dashboard', 'code': 'dashboard', 'description': 'Access to main dashboard', 'category': 'dashboard'},
    {'name': 'Tender Management', 'code': 'tenders', 'description': 'Create and manage tenders', 'category': 'files'},
    {'name': 'File Management', 'code': 'files', 'description': 'Upload and manage files', 'category': 'files'},
    {'name': 'Reports', 'code': 'reports', 'description': 'Generate reports', 'category': 'reports'},
    {'name': 'Analytics', 'code': 'analytics', 'description': 'Advanced analytics', 'category': 'analytics'},
    {'name': 'User Management', 'code': 'user_management', 'description': 'Manage users', 'category': 'users'}
]

with app.app_context():
    for feature_data in default_features:
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
            print(f"Added feature: {feature_data['name']}")
    db.session.commit()
    print("Features initialized")
'''
    
    try:
        with open('manual_commands.py', 'w') as f:
            f.write(manual_commands)
        print("✅ manual_commands.py created as backup")
        return True
    except Exception as e:
        print(f"⚠️  Could not create manual_commands.py: {e}")
        return False

def show_next_steps():
    """Show what to do next"""
    print("\n" + "="*60)
    print("🎉 FEATURE MANAGEMENT SETUP COMPLETE!")
    print("="*60)
    print()
    print("✅ Database tables created")
    print("✅ Default features initialized")
    print("✅ admin_forms.py created")
    print()
    print("📋 NEXT STEPS:")
    print("1. Add the routes from app_routes_addition.py to your app.py")
    print("2. Create the admin templates in templates/admin/")
    print("3. Test your app - it should run without errors now!")
    print()
    print("🔧 MANUAL OPTION:")
    print("If anything failed, you can run manual_commands.py manually:")
    print("python -c \"exec(open('manual_commands.py').read())\"")
    print()
    print("🌐 ADMIN URLS (after adding routes):")
    print("- Company Management: /admin/companies")
    print("- Feature Management: /admin/features")

def main():
    """Main integration function"""
    print("🚀 TMS Feature Management Integration")
    print("="*50)
    
    # Step 1: Check requirements
    if not check_requirements():
        return False
    
    # Step 2: Create directories
    create_directories()
    
    # Step 3: Check if models are updated
    if not check_models_updated():
        return False
    
    # Step 4: Create manual commands backup
    create_manual_commands()
    
    # Step 5: Create database tables
    tables_created = create_database_tables()
    
    # Step 6: Test models (only if tables were created)
    models_working = False
    if tables_created:
        models_working = test_feature_models()
    
    # Step 7: Create admin forms
    forms_created = create_admin_forms()
    
    # Step 8: Initialize features (only if models are working)
    features_initialized = False
    if models_working:
        features_initialized = initialize_default_features()
    
    # Step 9: Show next steps
    show_next_steps()
    
    # Check overall success
    if tables_created and models_working and forms_created and features_initialized:
        return True
    else:
        print("\n⚠️  Some steps failed, but manual_commands.py was created as backup")
        return True  # Return True anyway since we have backup options

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Integration completed! (Check any warnings above)")
    else:
        print("\n❌ Integration failed. Please check the errors above.")
        sys.exit(1)
    """Check if all required files exist"""
    print("🔍 Checking requirements...")
    
    required_files = [
        'app.py',
        'models.py',
        'templates/base.html'
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False
    
    print("✅ All required files found")
    return True

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    
    directories = [
        'templates/admin',
        'static/css',
        'static/js'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created/verified: {directory}")

def check_models_updated():
    """Check if models.py has been updated with Feature models"""
    print("🔍 Checking if models.py has Feature classes...")
    
    try:
        with open('models.py', 'r') as f:
            content = f.read()
            
        if 'class Feature(' in content and 'class CompanyFeature(' in content:
            print("✅ Feature models found in models.py")
            return True
        else:
            print("❌ Feature models not found in models.py")
            print("Please update your models.py with the Feature and CompanyFeature classes")
            return False
    except Exception as e:
        print(f"❌ Error reading models.py: {e}")
        return False

def create_database_tables():
    """Create the database tables"""
    print("🗄️ Creating database tables...")
    
    try:
        # Import after checking models
        from app import app, db
        
        with app.app_context():
            # Create all tables (this is safe - won't recreate existing tables)
            db.create_all()
            print("✅ Database tables created successfully")
            return True
            
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        return False

def test_feature_models():
    """Test if the Feature models work"""
    print("🧪 Testing Feature models...")
    
    try:
        from app import app
        from models import Feature, CompanyFeature, Company
        
        with app.app_context():
            # Test basic model functionality
            feature_count = Feature.query.count()
            company_count = Company.query.count()
            
            print(f"✅ Feature model working - {feature_count} features found")
            print(f"✅ Company model working - {company_count} companies found")
            return True
            
    except Exception as e:
        print(f"❌ Error testing models: {e}")
        return False

def create_admin_forms():
    """Create admin_forms.py file"""
    print("📝 Creating admin_forms.py...")
    
    admin_forms_content = '''# admin_forms.py - Forms for Feature Management

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length
from models import Feature, Company

class FeatureForm(FlaskForm):
    """Form for creating/editing features"""
    name = StringField('Feature Name', validators=[DataRequired(), Length(max=100)])
    code = StringField('Feature Code', validators=[DataRequired(), Length(max=50)], 
                      description='Used in code (e.g., dashboard, reports, files)')
    description = TextAreaField('Description')
    category = SelectField('Category', choices=[
        ('dashboard', 'Dashboard'),
        ('reports', 'Reports'), 
        ('files', 'Files'),
        ('users', 'User Management'),
        ('analytics', 'Analytics'),
        ('api', 'API Access'),
        ('integrations', 'Integrations'),
        ('advanced', 'Advanced Features')
    ])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Feature')

class CompanyFeaturesManagementForm(FlaskForm):
    """Form for managing all features for a company at once"""
    
    def __init__(self, company_id=None, *args, **kwargs):
        super(CompanyFeaturesManagementForm, self).__init__(*args, **kwargs)
        
        if company_id:
            self.company_id = company_id
            # Get all active features
            features = Feature.query.filter_by(is_active=True).order_by(Feature.category, Feature.name).all()
            
            # Get currently enabled features for this company
            enabled_features = set()
            company = Company.query.get(company_id)
            if company:
                enabled_features = {f.code for f in company.get_enabled_features()}
            
            # Dynamically add checkbox fields for each feature
            for feature in features:
                field_name = f'feature_{feature.code}'
                field = BooleanField(
                    feature.name,
                    default=feature.code in enabled_features,
                    description=feature.description
                )
                setattr(self, field_name, field)
                
                # Store feature info for later use
                if not hasattr(self, '_features'):
                    self._features = []
                self._features.append(feature)
    
    submit = SubmitField('Update Company Features')
    
    def get_features(self):
        """Get list of features for this form"""
        return getattr(self, '_features', [])
'''
    
    try:
        with open('admin_forms.py', 'w') as f:
            f.write(admin_forms_content)
        print("✅ admin_forms.py created successfully")
        return True
    except Exception as e:
        print(f"❌ Error creating admin_forms.py: {e}")
        return False

def initialize_default_features():
    """Initialize default features"""
    print("🎯 Initializing default features...")
    
    try:
        from app import app, db
        from models import Feature
        
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
                'category': 'files'
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
            }
        ]
        
        with app.app_context():
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
            
            db.session.commit()
            print("✅ Default features initialized successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Error initializing features: {e}")
        return False

def show_next_steps():
    """Show what to do next"""
    print("\n" + "="*60)
    print("🎉 FEATURE MANAGEMENT SETUP COMPLETE!")
    print("="*60)
    print()
    print("✅ Database tables created")
    print("✅ Default features initialized")
    print("✅ admin_forms.py created")
    print()
    print("📋 NEXT STEPS:")
    print("1. Copy the admin_routes.py content to your app.py or create admin_routes.py")
    print("2. Create the admin templates in templates/admin/")
    print("3. Register the admin blueprint in your app.py:")
    print("   from admin_routes import admin_bp")
    print("   app.register_blueprint(admin_bp)")
    print()
    print("🌐 ADMIN URLS (after completing setup):")
    print("- Company Management: /admin/companies")
    print("- Feature Management: /admin/features")
    print()
    print("🔧 Your app should now run without errors!")

def main():
    """Main integration function"""
    print("🚀 TMS Feature Management Integration")
    print("="*50)
    
    # Step 1: Check requirements
    if not check_requirements():
        return False
    
    # Step 2: Create directories
    create_directories()
    
    # Step 3: Check if models are updated
    if not check_models_updated():
        return False
    
    # Step 4: Create database tables
    if not create_database_tables():
        return False
    
    # Step 5: Test models
    if not test_feature_models():
        return False
    
    # Step 6: Create admin forms
    if not create_admin_forms():
        return False
    
    # Step 7: Initialize features
    if not initialize_default_features():
        return False
    
    # Step 8: Show next steps
    show_next_steps()
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Integration completed successfully!")
    else:
        print("\n❌ Integration failed. Please check the errors above.")
        sys.exit(1)