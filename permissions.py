# Replace your entire permissions.py file with this fixed version:

from functools import wraps
from flask import session, request, jsonify, flash, redirect, url_for, abort
from models import User, Company, CompanyModule, ModuleDefinition, Role

class ModulePermissions:
    """Centralized module permission checking"""
    
    # Define what each module provides
    MODULE_FEATURES = {
        'user_management': {
            'routes': [
                'users', 'add_user', 'edit_user', 'delete_user',
                'user_roles', 'permissions'
            ],
            'description': 'User and role management',
            'required': True  # Cannot be disabled
        },
        'tender_management': {
            'routes': [
                'tenders', 'add_tender', 'edit_tender', 'delete_tender',
                'tender_details', 'tender_search'
            ],
            'description': 'Core tender management functionality',
            'required': True  # Cannot be disabled
        },
        'company_management': {
            'routes': [
                'company_profile', 'company_settings'
            ],
            'description': 'Company profile and settings management',
            'price': 25.00
        },
        'document_management': {
            'routes': [
                'documents', 'upload_document', 'download_document',
                'document_types'
            ],
            'description': 'File upload and document management',
            'price': 15.00
        },
        'custom_fields': {
            'routes': [
                'custom_fields', 'add_custom_field', 'edit_custom_field'
            ],
            'description': 'Dynamic field creation and management',
            'price': 10.00
        },
        'notes_comments': {
            'routes': [
                'tender_notes', 'add_note', 'edit_note', 'delete_note'
            ],
            'description': 'Collaborative notes and comments',
            'price': 8.00
        },
        'audit_tracking': {
            'routes': [
                'audit_log', 'tender_history', 'user_activity'
            ],
            'description': 'Action logging and change history',
            'price': 20.00
        },
        'notifications': {
            'routes': [
                'notifications', 'notification_settings',
                'email_alerts'
            ],
            'description': 'Email alerts and notifications',
            'price': 12.00
        },
        'reporting': {
            'routes': [
                'reports', 'analytics', 'dashboard_charts',
                'tender_analytics', 'performance_metrics'
            ],
            'description': 'Advanced reporting and analytics',
            'price': 30.00
        },
        'advanced_search': {
            'routes': [
                'advanced_search', 'search_filters'
            ],
            'description': 'Enhanced search capabilities',
            'price': 5.00
        },
        'api_access': {
            'routes': [
                'api_docs', 'api_keys', 'webhook_settings'
            ],
            'description': 'REST API access and integrations',
            'price': 50.00
        },
        'white_labeling': {
            'routes': [
                'branding', 'custom_domain', 'logo_upload'
            ],
            'description': 'White-label branding options',
            'price': 100.00
        }
    }
    
    @staticmethod
    def get_user_permissions(user_id):
        """Get comprehensive permissions for a user"""
        try:
            user = User.query.get(user_id)
            if not user:
                return None
            
            # SUPER ADMIN BYPASS - Super admins get all permissions
            if user.is_super_admin:
                return {
                    'user': user,
                    'company': user.company if user.company_id else None,
                    'user_role': user.role.name if user.role else 'Super Admin',
                    'is_company_admin': True,  # Super admin is also company admin
                    'is_super_admin': True,
                    'enabled_modules': ['all'],  # Super admin has access to all modules
                    'can_delete': True,
                    'can_manage_users': True,
                    'can_view_analytics': True,
                    'can_use_api': True,
                    'has_notifications': True,
                    'has_white_label': True,
                    'can_manage_company': True,
                    'can_upload_documents': True,
                    'can_create_custom_fields': True,
                    'can_add_notes': True,
                    'can_view_audit_log': True,
                    'can_advanced_search': True
                }
            
            # Regular users need company
            if not user.company_id:
                return None
                
            company = Company.query.get(user.company_id)
            if not company:
                return None
            
            # Get enabled modules for the company
            try:
                enabled_modules = company.get_enabled_modules()
            except:
                # Fallback if method doesn't exist
                enabled_modules = CompanyModule.get_enabled_modules(user.company_id)
            
            # Determine user role permissions
            user_role = user.role.name if user.role else 'user'
            
            # Check if user is company admin (handle different role name formats)
            admin_roles = ['company_admin', 'admin', 'Company Admin', 'Admin', 'Super Admin']
            is_company_admin = user_role in admin_roles
            
            # Additional check with case insensitive comparison
            if not is_company_admin:
                is_company_admin = user_role.lower() in [role.lower() for role in admin_roles]
            
            return {
                'user': user,
                'company': company,
                'user_role': user_role,
                'is_company_admin': is_company_admin,
                'is_super_admin': False,
                'enabled_modules': enabled_modules,
                'can_delete': is_company_admin,
                'can_manage_users': 'user_management' in enabled_modules and is_company_admin,
                'can_view_analytics': 'reporting' in enabled_modules,
                'can_use_api': 'api_access' in enabled_modules,
                'has_notifications': 'notifications' in enabled_modules,
                'has_white_label': 'white_labeling' in enabled_modules,
                'can_manage_company': 'company_management' in enabled_modules and is_company_admin,
                'can_upload_documents': 'document_management' in enabled_modules,
                'can_create_custom_fields': 'custom_fields' in enabled_modules and is_company_admin,
                'can_add_notes': 'notes_comments' in enabled_modules,
                'can_view_audit_log': 'audit_tracking' in enabled_modules and is_company_admin,
                'can_advanced_search': 'advanced_search' in enabled_modules
            }
            
        except Exception as e:
            print(f"Error getting user permissions: {str(e)}")
            return None
    
    @staticmethod
    def check_module_access(module_name, user_id=None):
        """Check if user has access to a specific module"""
        if not user_id and 'user_id' in session:
            user_id = session['user_id']
            
        if not user_id:
            return False
        
        try:
            user = User.query.get(user_id)
            if not user:
                return False
            
            # SUPER ADMIN BYPASS - Super admins can access everything
            if user.is_super_admin:
                return True
            
            # Regular users need company and module check
            if not user.company_id:
                return False
            
            permissions = ModulePermissions.get_user_permissions(user_id)
            if not permissions:
                return False
                
            # Check if module is enabled for company
            return module_name in permissions['enabled_modules']
            
        except Exception as e:
            print(f"Error checking module access: {str(e)}")
            return False
    
    @staticmethod
    def get_available_routes(user_id):
        """Get list of routes user can access based on enabled modules"""
        permissions = ModulePermissions.get_user_permissions(user_id)
        if not permissions:
            return []
        
        # Super admin gets all routes
        if permissions['is_super_admin']:
            available_routes = []
            for module_name in ModulePermissions.MODULE_FEATURES:
                routes = ModulePermissions.MODULE_FEATURES[module_name]['routes']
                available_routes.extend(routes)
            return available_routes
        
        # Regular users get routes based on enabled modules
        available_routes = []
        enabled_modules = permissions['enabled_modules']
        
        for module_name in enabled_modules:
            if module_name in ModulePermissions.MODULE_FEATURES:
                routes = ModulePermissions.MODULE_FEATURES[module_name]['routes']
                available_routes.extend(routes)
                
        return available_routes

def require_module(module_name):
    """Decorator to require a specific module to be enabled"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Authentication required'}), 401
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            
            user_id = session['user_id']
            user = User.query.get(user_id)
            
            # SUPER ADMIN BYPASS - Super admins can access everything
            if user and user.is_super_admin:
                return f(*args, **kwargs)
            
            # Check if user has access to this module
            if not ModulePermissions.check_module_access(module_name, user_id):
                # Get module display name for better error message
                try:
                    module_def = ModuleDefinition.query.filter_by(module_name=module_name).first()
                    display_name = module_def.display_name if module_def else module_name.replace('_', ' ').title()
                except:
                    display_name = module_name.replace('_', ' ').title()
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': False, 
                        'message': f'Access denied. {display_name} module required.'
                    }), 403
                
                flash(f'Access denied. {display_name} module is not enabled for your company.', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_company_admin(f):
    """Decorator to require company admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        
        user_id = session['user_id']
        permissions = ModulePermissions.get_user_permissions(user_id)
        
        if not permissions or not (permissions['is_company_admin'] or permissions['is_super_admin']):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False, 
                    'message': 'Access denied. Company admin privileges required.'
                }), 403
            
            flash('Access denied. Company admin privileges required.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def can_delete_entries(user_id=None):
    """Check if user can delete entries"""
    if not user_id and 'user_id' in session:
        user_id = session['user_id']
        
    permissions = ModulePermissions.get_user_permissions(user_id)
    return permissions and permissions['can_delete'] if permissions else False