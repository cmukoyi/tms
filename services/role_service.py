# services/role_service.py

from models import Role, User
from flask import session
import json

class RoleService:
    
    # Define all available permissions
    AVAILABLE_PERMISSIONS = {
        'user_management': {
            'display_name': 'User Management',
            'description': 'Create, edit, and manage users',
            'category': 'User Administration'
        },
        'role_management': {
            'display_name': 'Role Management',
            'description': 'Create and manage user roles',
            'category': 'User Administration'
        },
        'company_management': {
            'display_name': 'Company Management',
            'description': 'Manage company settings and information',
            'category': 'Company Administration'
        },
        'tender_create': {
            'display_name': 'Create Tenders',
            'description': 'Create new tender opportunities',
            'category': 'Tender Management'
        },
        'tender_edit': {
            'display_name': 'Edit Tenders',
            'description': 'Edit existing tenders',
            'category': 'Tender Management'
        },
        'tender_delete': {
            'display_name': 'Delete Tenders',
            'description': 'Delete tenders',
            'category': 'Tender Management'
        },
        'tender_view_all': {
            'display_name': 'View All Tenders',
            'description': 'View all tenders in the system',
            'category': 'Tender Management'
        },
        'tender_view_company': {
            'display_name': 'View Company Tenders',
            'description': 'View tenders for own company only',
            'category': 'Tender Management'
        },
        'document_upload': {
            'display_name': 'Upload Documents',
            'description': 'Upload documents to tenders',
            'category': 'Document Management'
        },
        'document_delete': {
            'display_name': 'Delete Documents',
            'description': 'Delete documents from tenders',
            'category': 'Document Management'
        },
        'notes_add': {
            'display_name': 'Add Notes',
            'description': 'Add notes and comments',
            'category': 'Collaboration'
        },
        'notes_edit_own': {
            'display_name': 'Edit Own Notes',
            'description': 'Edit your own notes',
            'category': 'Collaboration'
        },
        'notes_edit_all': {
            'display_name': 'Edit All Notes',
            'description': 'Edit any notes',
            'category': 'Collaboration'
        },
        'notes_delete_own': {
            'display_name': 'Delete Own Notes',
            'description': 'Delete your own notes',
            'category': 'Collaboration'
        },
        'notes_delete_all': {
            'display_name': 'Delete All Notes',
            'description': 'Delete any notes',
            'category': 'Collaboration'
        },
        'reporting_view': {
            'display_name': 'View Reports',
            'description': 'Access reporting dashboard',
            'category': 'Analytics & Reporting'
        },
        'reporting_export': {
            'display_name': 'Export Reports',
            'description': 'Export reports to PDF/Excel',
            'category': 'Analytics & Reporting'
        },
        'reporting_advanced': {
            'display_name': 'Advanced Analytics',
            'description': 'Access advanced analytics features',
            'category': 'Analytics & Reporting'
        },
        'billing_view': {
            'display_name': 'View Billing',
            'description': 'View billing information',
            'category': 'Billing & Finance'
        },
        'billing_manage': {
            'display_name': 'Manage Billing',
            'description': 'Manage billing and pricing',
            'category': 'Billing & Finance'
        },
        'custom_fields_create': {
            'display_name': 'Create Custom Fields',
            'description': 'Create custom fields',
            'category': 'System Configuration'
        },
        'custom_fields_manage': {
            'display_name': 'Manage Custom Fields',
            'description': 'Edit and delete custom fields',
            'category': 'System Configuration'
        },
        'audit_log_view': {
            'display_name': 'View Audit Logs',
            'description': 'View system audit logs',
            'category': 'Security & Audit'
        },
        'system_admin': {
            'display_name': 'System Administration',
            'description': 'Full system administration access',
            'category': 'System Administration'
        }
    }
    
    # Pre-defined role templates
    ROLE_TEMPLATES = {
        'super_admin': {
            'name': 'Super Admin',
            'description': 'Full system access',
            'level': 'super_admin',
            'permissions': list(AVAILABLE_PERMISSIONS.keys())  # All permissions
        },
        'company_admin': {
            'name': 'Company Admin',
            'description': 'Full company administration',
            'level': 'company_admin',
            'permissions': [
                'user_management', 'role_management', 'company_management',
                'tender_create', 'tender_edit', 'tender_delete', 'tender_view_company',
                'document_upload', 'document_delete',
                'notes_add', 'notes_edit_all', 'notes_delete_all',
                'reporting_view', 'reporting_export', 'reporting_advanced',
                'billing_view', 'custom_fields_create', 'custom_fields_manage',
                'audit_log_view'
            ]
        },
        'procurement_manager': {
            'name': 'Procurement Manager',
            'description': 'Manage procurement and tenders',
            'level': 'procurement_manager',
            'permissions': [
                'tender_create', 'tender_edit', 'tender_view_company',
                'document_upload', 'notes_add', 'notes_edit_own', 'notes_delete_own',
                'reporting_view', 'reporting_export'
            ]
        },
        'vendor': {
            'name': 'Vendor',
            'description': 'Limited vendor access',
            'level': 'vendor',
            'permissions': [
                'tender_view_company', 'document_upload',
                'notes_add', 'notes_edit_own'
            ]
        },
        'viewer': {
            'name': 'Viewer',
            'description': 'Read-only access',
            'level': 'viewer',
            'permissions': [
                'tender_view_company', 'reporting_view'
            ]
        }
    }
    
    @classmethod
    def initialize_default_roles(cls):
        """Initialize default system roles"""
        try:
            created_count = 0
            for role_key, role_data in cls.ROLE_TEMPLATES.items():
                # Check if role already exists
                existing_role = Role.query.filter_by(name=role_data['name']).first()
                
                if not existing_role:
                    new_role = Role(
                        name=role_data['name'],
                        description=role_data['description'],
                        level=role_data['level'],
                        permissions=json.dumps(role_data['permissions'])
                    )
                    db.session.add(new_role)
                    created_count += 1
                else:
                    # Update existing role permissions if they've changed
                    existing_permissions = json.loads(existing_role.permissions or '[]')
                    if set(existing_permissions) != set(role_data['permissions']):
                        existing_role.permissions = json.dumps(role_data['permissions'])
                        existing_role.description = role_data['description']
            
            db.session.commit()
            return True, f"Initialized {created_count} default roles"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error initializing roles: {str(e)}"
    
    @classmethod
    def create_custom_role(cls, name, description, level, permissions, created_by=None):
        """Create a custom role with specified permissions"""
        try:
            # Validate permissions
            invalid_permissions = [p for p in permissions if p not in cls.AVAILABLE_PERMISSIONS]
            if invalid_permissions:
                return None, f"Invalid permissions: {', '.join(invalid_permissions)}"
            
            # Check if role name already exists
            existing_role = Role.query.filter_by(name=name).first()
            if existing_role:
                return None, f"Role '{name}' already exists"
            
            # Create new role
            new_role = Role(
                name=name,
                description=description,
                level=level,
                permissions=json.dumps(permissions)
            )
            
            db.session.add(new_role)
            db.session.commit()
            
            return new_role, f"Role '{name}' created successfully"
            
        except Exception as e:
            db.session.rollback()
            return None, f"Error creating role: {str(e)}"
    
    @classmethod
    def update_role(cls, role_id, name=None, description=None, level=None, permissions=None):
        """Update an existing role"""
        try:
            role = Role.query.get(role_id)
            if not role:
                return False, "Role not found"
            
            # Update fields if provided
            if name:
                # Check if new name conflicts with existing role
                existing = Role.query.filter(Role.name == name, Role.id != role_id).first()
                if existing:
                    return False, f"Role name '{name}' already exists"
                role.name = name
            
            if description:
                role.description = description
            
            if level:
                role.level = level
            
            if permissions is not None:
                # Validate permissions
                invalid_permissions = [p for p in permissions if p not in cls.AVAILABLE_PERMISSIONS]
                if invalid_permissions:
                    return False, f"Invalid permissions: {', '.join(invalid_permissions)}"
                role.permissions = json.dumps(permissions)
            
            db.session.commit()
            return True, f"Role '{role.name}' updated successfully"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating role: {str(e)}"
    
    @classmethod
    def delete_role(cls, role_id):
        """Delete a role (only if not in use)"""
        try:
            role = Role.query.get(role_id)
            if not role:
                return False, "Role not found"
            
            # Check if role is in use
            users_with_role = User.query.filter_by(role_id=role_id).count()
            if users_with_role > 0:
                return False, f"Cannot delete role. It is assigned to {users_with_role} users."
            
            # Don't allow deletion of system roles
            if role.name in [template['name'] for template in cls.ROLE_TEMPLATES.values()]:
                return False, "Cannot delete system roles"
            
            db.session.delete(role)
            db.session.commit()
            
            return True, f"Role '{role.name}' deleted successfully"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting role: {str(e)}"
    
    @classmethod
    def get_all_roles(cls):
        """Get all roles"""
        return Role.query.order_by(Role.name).all()

    
    @classmethod
    def get_role_by_id(cls, role_id):
        """Get role by ID"""
        return Role.query.get(role_id)
    
    @classmethod
    def get_role_by_name(cls, name):
        """Get role by name"""
        return Role.query.filter_by(name=name).first()
    
    @classmethod
    def get_role_permissions(cls, role_id):
        """Get permissions for a role"""
        role = Role.query.get(role_id)
        if not role or not role.permissions:
            return []
        
        try:
            return json.loads(role.permissions)
        except:
            return []
    
    @classmethod
    def check_user_permission(cls, user_id, permission):
        """Check if user has a specific permission"""
        try:
            user = User.query.get(user_id)
            if not user or not user.role:
                return False
            
            # Super admin has all permissions
            if user.is_super_admin:
                return True
            
            user_permissions = cls.get_role_permissions(user.role_id)
            return permission in user_permissions
            
        except Exception as e:
            print(f"Error checking user permission: {e}")
            return False
    
    @classmethod
    def get_user_permissions(cls, user_id):
        """Get all permissions for a user"""
        try:
            user = User.query.get(user_id)
            if not user:
                return []
            
            # Super admin has all permissions
            if user.is_super_admin:
                return list(cls.AVAILABLE_PERMISSIONS.keys())
            
            if not user.role:
                return []
            
            return cls.get_role_permissions(user.role_id)
            
        except Exception as e:
            print(f"Error getting user permissions: {e}")
            return []
    
    @classmethod
    def get_available_permissions(cls):
        """Get all available permissions"""
        return cls.AVAILABLE_PERMISSIONS
    
    @classmethod
    def get_permissions_by_category(cls):
        """Get permissions grouped by category"""
        categories = {}
        for perm_key, perm_data in cls.AVAILABLE_PERMISSIONS.items():
            category = perm_data['category']
            if category not in categories:
                categories[category] = []
            categories[category].append({
                'key': perm_key,
                'display_name': perm_data['display_name'],
                'description': perm_data['description']
            })
        return categories