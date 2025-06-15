# services/company_module_service.py
from datetime import datetime
from models import db, ModuleDefinition, CompanyModule, Company, User
from functools import wraps
from decimal import Decimal

class CompanyModuleService:
    """Service for managing company-specific module access"""
    
    # Default modules that get created when the system is initialized
    DEFAULT_MODULES = {
        'user_management': {
            'display_name': 'User Management',
            'description': 'User registration, roles, and access control',
            'is_core': True,
            'category': 'core',
            'monthly_price': Decimal('0.00')
        },
        'tender_management': {
            'display_name': 'Tender Management',
            'description': 'Core tender CRUD operations and workflows',
            'is_core': True,
            'category': 'core',
            'monthly_price': Decimal('0.00')
        },
        'company_management': {
            'display_name': 'Company Management',
            'description': 'Multi-company support and company profile management',
            'is_core': False,
            'category': 'feature',
            'monthly_price': Decimal('25.00')
        },
        'document_management': {
            'display_name': 'Document Management',
            'description': 'File upload, download, and document type management',
            'is_core': False,
            'category': 'feature',
            'monthly_price': Decimal('15.00')
        },
        'custom_fields': {
            'display_name': 'Custom Fields',
            'description': 'Dynamic field creation and management',
            'is_core': False,
            'category': 'feature',
            'monthly_price': Decimal('10.00')
        },
        'notes_comments': {
            'display_name': 'Notes & Comments',
            'description': 'Collaborative notes and comments on tenders',
            'is_core': False,
            'category': 'feature',
            'monthly_price': Decimal('8.00')
        },
        'audit_tracking': {
            'display_name': 'Audit & History Tracking',
            'description': 'Action logging and change history',
            'is_core': False,
            'category': 'premium',
            'monthly_price': Decimal('20.00')
        },
        'notifications': {
            'display_name': 'Notifications',
            'description': 'Email alerts and deadline notifications',
            'is_core': False,
            'category': 'feature',
            'monthly_price': Decimal('12.00')
        },
        'reporting': {
            'display_name': 'Reporting & Analytics',
            'description': 'Advanced reporting and data analytics',
            'is_core': False,
            'category': 'premium',
            'monthly_price': Decimal('30.00')
        },
        'advanced_search': {
            'display_name': 'Advanced Search',
            'description': 'Enhanced search and filtering capabilities',
            'is_core': False,
            'category': 'feature',
            'monthly_price': Decimal('5.00')
        },
        'api_access': {
            'display_name': 'API Access',
            'description': 'REST API access for integrations',
            'is_core': False,
            'category': 'premium',
            'monthly_price': Decimal('50.00')
        },
        'white_labeling': {
            'display_name': 'White Labeling',
            'description': 'Custom branding and white label options',
            'is_core': False,
            'category': 'premium',
            'monthly_price': Decimal('100.00')
        }
    }
    
    @staticmethod
    def initialize_module_definitions():
        """Initialize the available modules in the system"""
        try:
            for module_name, config in CompanyModuleService.DEFAULT_MODULES.items():
                existing = ModuleDefinition.query.filter_by(module_name=module_name).first()
                if not existing:
                    module = ModuleDefinition(
                        module_name=module_name,
                        display_name=config['display_name'],
                        description=config['description'],
                        is_core=config['is_core'],
                        category=config['category'],
                        monthly_price=config['monthly_price'],
                        sort_order=list(CompanyModuleService.DEFAULT_MODULES.keys()).index(module_name)
                    )
                    db.session.add(module)
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error initializing module definitions: {str(e)}")
            return False
    
    @staticmethod
    def setup_company_modules(company_id, include_premium=False):
        """Setup default modules for a new company"""
        try:
            # Get all core modules and basic features
            core_modules = ModuleDefinition.query.filter_by(is_core=True).all()
            basic_features = ModuleDefinition.query.filter_by(category='feature').all()
            
            modules_to_enable = core_modules
            if include_premium:
                premium_modules = ModuleDefinition.query.filter_by(category='premium').all()
                modules_to_enable.extend(basic_features + premium_modules)
            else:
                modules_to_enable.extend(basic_features)
            
            for module_def in modules_to_enable:
                # Check if already exists
                existing = CompanyModule.query.filter_by(
                    company_id=company_id, 
                    module_id=module_def.id
                ).first()
                
                if not existing:
                    company_module = CompanyModule(
                        company_id=company_id,
                        module_id=module_def.id,
                        is_enabled=True,
                        billing_start_date=datetime.utcnow()
                    )
                    db.session.add(company_module)
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error setting up company modules: {str(e)}")
            return False
    
    @staticmethod
    def is_module_enabled_for_company(company_id, module_name):
        """Check if a specific module is enabled for a company"""
        company_module = db.session.query(CompanyModule).join(ModuleDefinition).filter(
            CompanyModule.company_id == company_id,
            ModuleDefinition.module_name == module_name,
            CompanyModule.is_enabled == True
        ).first()
        
        return company_module is not None
    
    @staticmethod
    def get_company_modules(company_id):
        """Get all modules available to a company"""
        return db.session.query(CompanyModule).join(ModuleDefinition).filter(
            CompanyModule.company_id == company_id
        ).order_by(ModuleDefinition.sort_order).all()
    
    @staticmethod
    def get_enabled_modules_for_company(company_id):
        """Get only enabled modules for a company"""
        return db.session.query(CompanyModule).join(ModuleDefinition).filter(
            CompanyModule.company_id == company_id,
            CompanyModule.is_enabled == True
        ).order_by(ModuleDefinition.sort_order).all()
    
    @staticmethod
    def toggle_company_module(company_id, module_name, enabled, user_id, notes=None):
        """Enable or disable a module for a company"""
        try:
            module_def = ModuleDefinition.query.filter_by(module_name=module_name).first()
            if not module_def:
                return False, "Module not found"
            
            if module_def.is_core and not enabled:
                return False, "Core modules cannot be disabled"
            
            company_module = CompanyModule.query.filter_by(
                company_id=company_id,
                module_id=module_def.id
            ).first()
            
            if not company_module:
                # Create new module assignment
                company_module = CompanyModule(
                    company_id=company_id,
                    module_id=module_def.id,
                    is_enabled=enabled,
                    enabled_by=user_id if enabled else None,
                    disabled_by=user_id if not enabled else None,
                    notes=notes
                )
                if enabled:
                    company_module.billing_start_date = datetime.utcnow()
                else:
                    company_module.disabled_at = datetime.utcnow()
                
                db.session.add(company_module)
            else:
                # Update existing
                company_module.is_enabled = enabled
                if enabled:
                    company_module.enabled_at = datetime.utcnow()
                    company_module.enabled_by = user_id
                    company_module.disabled_at = None
                    if not company_module.billing_start_date:
                        company_module.billing_start_date = datetime.utcnow()
                else:
                    company_module.disabled_at = datetime.utcnow()
                    company_module.disabled_by = user_id
                
                if notes:
                    company_module.notes = notes
            
            db.session.commit()
            return True, "Module updated successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating module: {str(e)}"
    
    @staticmethod
    def get_company_monthly_cost(company_id):
        """Calculate the monthly cost for a company based on enabled modules"""
        enabled_modules = CompanyModuleService.get_enabled_modules_for_company(company_id)
        total_cost = sum(
            float(cm.module_definition.monthly_price) for cm in enabled_modules 
            if cm.module_definition.monthly_price
        )
        return total_cost
    
    @staticmethod
    def get_all_companies_billing_summary():
        """Get billing summary for all companies"""
        companies = Company.query.filter_by(is_active=True).all()
        summary = []
        
        for company in companies:
            enabled_modules = CompanyModuleService.get_enabled_modules_for_company(company.id)
            monthly_cost = CompanyModuleService.get_company_monthly_cost(company.id)
            
            summary.append({
                'company_id': company.id,
                'company_name': company.name,
                'enabled_modules_count': len(enabled_modules),
                'monthly_cost': monthly_cost,
                'enabled_modules': [cm.module_definition.module_name for cm in enabled_modules]
            })
        
        return summary


# Decorator for checking company module permissions
def require_company_module(module_name):
    """Decorator to check if a module is enabled for the current user's company"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import session, jsonify, redirect, url_for, flash
            
            company_id = session.get('company_id')
            if not company_id:
                flash('No company associated with your account', 'error')
                return redirect(url_for('dashboard'))
            
            if not CompanyModuleService.is_module_enabled_for_company(company_id, module_name):
                flash(f'The {module_name.replace("_", " ").title()} feature is not enabled for your company. Please contact your administrator.', 'warning')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
    @staticmethod
    def get_all():
        """Get all records"""
        # Implementation depends on specific service
        pass

    @staticmethod
    def search(query):
        """Search records"""
        # Implementation depends on specific service
        pass
