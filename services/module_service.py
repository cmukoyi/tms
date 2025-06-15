# services/module_service.py
from datetime import datetime
from models import db, ModuleDefinition, CompanyModule

from functools import wraps

# Module configuration constants
AVAILABLE_MODULES = {
    'company_management': {
        'display_name': 'Company Management',
        'description': 'Multi-company support and company profile management',
        'is_core': False
    },
    'user_management': {
        'display_name': 'User Management',
        'description': 'User registration, roles, and access control',
        'is_core': True
    },
    'tender_management': {
        'display_name': 'Tender Management',
        'description': 'Core tender CRUD operations and workflows',
        'is_core': True
    },
    'document_management': {
        'display_name': 'Document Management',
        'description': 'File upload, download, and document type management',
        'is_core': False
    },
    'custom_fields': {
        'display_name': 'Custom Fields',
        'description': 'Dynamic field creation and management',
        'is_core': False
    },
    'notes_comments': {
        'display_name': 'Notes & Comments',
        'description': 'Collaborative notes and comments on tenders',
        'is_core': False
    },
    'audit_tracking': {
        'display_name': 'Audit & History Tracking',
        'description': 'Action logging and change history',
        'is_core': False
    },
    'notifications': {
        'display_name': 'Notifications',
        'description': 'Email alerts and deadline notifications',
        'is_core': False
    },
    'reporting': {
        'display_name': 'Reporting & Analytics',
        'description': 'Advanced reporting and data analytics',
        'is_core': False
    },
    'advanced_search': {
        'display_name': 'Advanced Search',
        'description': 'Enhanced search and filtering capabilities',
        'is_core': False
    }
}


class ModuleService:
    """Service for managing module settings and permissions"""
    
    @staticmethod
    def initialize_modules():
        """Initialize default modules in the database"""
        try:
            for module_name, config in AVAILABLE_MODULES.items():
                existing = ModuleSettings.query.filter_by(module_name=module_name).first()
                if not existing:
                    module = ModuleSettings(
                        module_name=module_name,
                        display_name=config['display_name'],
                        description=config['description'],
                        is_core=config['is_core'],
                        is_enabled=True,
                        sort_order=list(AVAILABLE_MODULES.keys()).index(module_name)
                    )
                    db.session.add(module)
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error initializing modules: {str(e)}")
            return False
    
    @staticmethod
    def is_module_enabled(module_name):
        """Check if a specific module is enabled"""
        module = ModuleSettings.query.filter_by(
            module_name=module_name,
            is_enabled=True
        ).first()
        return module is not None
    
    @staticmethod
    def get_enabled_modules():
        """Get all enabled modules"""
        return ModuleSettings.query.filter_by(is_enabled=True).order_by(ModuleSettings.sort_order).all()
    
    @staticmethod
    def get_all_modules():
        """Get all modules with their status"""
        return ModuleSettings.query.order_by(ModuleSettings.sort_order).all()
    
    @staticmethod
    def toggle_module(module_name, enabled, user_id):
        """Enable or disable a module"""
        module = ModuleSettings.query.filter_by(module_name=module_name).first()
        if not module:
            return False, "Module not found"
        
        if module.is_core and not enabled:
            return False, "Core modules cannot be disabled"
        
        module.is_enabled = enabled
        module.updated_by = user_id
        module.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            return True, "Module updated successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating module: {str(e)}"
    
    @staticmethod
    def update_module_order(module_orders):
        """Update the sort order of modules"""
        try:
            for module_name, order in module_orders.items():
                module = ModuleSettings.query.filter_by(module_name=module_name).first()
                if module:
                    module.sort_order = order
            
            db.session.commit()
            return True, "Module order updated successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating module order: {str(e)}"


# Decorator for checking module permissions
def require_module(module_name):
    """Decorator to check if a module is enabled before allowing access"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not ModuleService.is_module_enabled(module_name):
                return {'error': f'Module {module_name} is not enabled'}, 403
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
