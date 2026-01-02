"""
Permissions Service
Handles permission checks, role management, and access control
"""

from models import (
    db, Permission, CompanyRole, RolePermission, 
    UserCompanyRole, User, Company
)
from flask import session
from sqlalchemy import and_


class PermissionsService:
    """Service for managing permissions and access control"""
    
    @staticmethod
    def user_has_permission(user_id, permission_name, company_id=None):
        """
        Check if a user has a specific permission
        
        Args:
            user_id: User ID to check
            permission_name: Permission name (e.g., 'approve_tenders')
            company_id: Optional company ID to check (defaults to user's company)
        
        Returns:
            Boolean indicating if user has the permission
        """
        try:
            # Super admins have all permissions
            user = User.query.get(user_id)
            if not user:
                return False
            
            if user.is_super_admin:
                return True
            
            # Get company ID
            if not company_id:
                company_id = user.company_id
            
            if not company_id:
                return False
            
            # Check if user has permission through any of their roles
            has_perm = db.session.query(Permission).join(RolePermission).join(CompanyRole).join(
                UserCompanyRole
            ).filter(
                and_(
                    UserCompanyRole.user_id == user_id,
                    CompanyRole.company_id == company_id,
                    CompanyRole.is_active == True,
                    Permission.name == permission_name,
                    Permission.is_active == True
                )
            ).first()
            
            return has_perm is not None
            
        except Exception as e:
            print(f"Error checking permission: {e}")
            return False
    
    @staticmethod
    def get_user_permissions(user_id, company_id=None):
        """
        Get all permissions for a user
        
        Args:
            user_id: User ID
            company_id: Optional company ID
        
        Returns:
            List of permission names
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return []
            
            # Super admins have all permissions
            if user.is_super_admin:
                all_perms = Permission.query.filter_by(is_active=True).all()
                return [p.name for p in all_perms]
            
            # Get company ID
            if not company_id:
                company_id = user.company_id
            
            if not company_id:
                return []
            
            # Get all permissions from user's roles
            permissions = db.session.query(Permission).join(RolePermission).join(CompanyRole).join(
                UserCompanyRole
            ).filter(
                and_(
                    UserCompanyRole.user_id == user_id,
                    CompanyRole.company_id == company_id,
                    CompanyRole.is_active == True,
                    Permission.is_active == True
                )
            ).distinct().all()
            
            return [p.name for p in permissions]
            
        except Exception as e:
            print(f"Error getting user permissions: {e}")
            return []
    
    @staticmethod
    def get_user_roles(user_id, company_id=None):
        """
        Get all roles assigned to a user
        
        Args:
            user_id: User ID
            company_id: Optional company ID
        
        Returns:
            List of CompanyRole objects
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return []
            
            if not company_id:
                company_id = user.company_id
            
            if not company_id:
                return []
            
            roles = db.session.query(CompanyRole).join(UserCompanyRole).filter(
                and_(
                    UserCompanyRole.user_id == user_id,
                    CompanyRole.company_id == company_id,
                    CompanyRole.is_active == True
                )
            ).all()
            
            return roles
            
        except Exception as e:
            print(f"Error getting user roles: {e}")
            return []
    
    @staticmethod
    def assign_role_to_user(user_id, role_id, assigned_by_id=None):
        """
        Assign a role to a user
        
        Args:
            user_id: User to assign role to
            role_id: Role to assign
            assigned_by_id: User who is assigning the role
        
        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            # Check if assignment already exists
            existing = UserCompanyRole.query.filter_by(
                user_id=user_id,
                role_id=role_id
            ).first()
            
            if existing:
                return (False, "User already has this role")
            
            # Create assignment
            assignment = UserCompanyRole(
                user_id=user_id,
                role_id=role_id,
                assigned_by=assigned_by_id
            )
            
            db.session.add(assignment)
            db.session.commit()
            
            return (True, "Role assigned successfully")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error assigning role: {e}")
            return (False, str(e))
    
    @staticmethod
    def remove_role_from_user(user_id, role_id):
        """
        Remove a role from a user
        
        Args:
            user_id: User to remove role from
            role_id: Role to remove
        
        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            assignment = UserCompanyRole.query.filter_by(
                user_id=user_id,
                role_id=role_id
            ).first()
            
            if not assignment:
                return (False, "Role assignment not found")
            
            db.session.delete(assignment)
            db.session.commit()
            
            return (True, "Role removed successfully")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error removing role: {e}")
            return (False, str(e))
    
    @staticmethod
    def get_company_roles(company_id, include_inactive=False):
        """
        Get all roles for a company
        
        Args:
            company_id: Company ID
            include_inactive: Whether to include inactive roles
        
        Returns:
            List of CompanyRole objects
        """
        try:
            query = CompanyRole.query.filter_by(company_id=company_id)
            
            if not include_inactive:
                query = query.filter_by(is_active=True)
            
            return query.order_by(CompanyRole.display_name).all()
            
        except Exception as e:
            print(f"Error getting company roles: {e}")
            return []
    
    @staticmethod
    def create_custom_role(company_id, name, display_name, description, permission_ids, created_by_id=None):
        """
        Create a custom role for a company
        
        Args:
            company_id: Company ID
            name: Role name (slug)
            display_name: Display name
            description: Role description
            permission_ids: List of permission IDs to assign
            created_by_id: User who created the role
        
        Returns:
            Tuple (success: bool, role: CompanyRole or None, message: str)
        """
        try:
            # Check if role name already exists for this company
            existing = CompanyRole.query.filter_by(
                company_id=company_id,
                name=name
            ).first()
            
            if existing:
                return (False, None, "A role with this name already exists")
            
            # Create role
            role = CompanyRole(
                company_id=company_id,
                name=name,
                display_name=display_name,
                description=description,
                is_system_role=False
            )
            
            db.session.add(role)
            db.session.flush()  # Get role ID
            
            # Assign permissions
            for perm_id in permission_ids:
                role_perm = RolePermission(
                    role_id=role.id,
                    permission_id=perm_id
                )
                db.session.add(role_perm)
            
            db.session.commit()
            
            return (True, role, "Role created successfully")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating role: {e}")
            return (False, None, str(e))
    
    @staticmethod
    def update_role_permissions(role_id, permission_ids):
        """
        Update permissions for a role
        
        Args:
            role_id: Role to update
            permission_ids: New list of permission IDs
        
        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            role = CompanyRole.query.get(role_id)
            
            if not role:
                return (False, "Role not found")
            
            # Don't allow editing system roles
            if role.is_system_role:
                return (False, "Cannot edit system roles")
            
            # Delete existing permissions
            RolePermission.query.filter_by(role_id=role_id).delete()
            
            # Add new permissions
            for perm_id in permission_ids:
                role_perm = RolePermission(
                    role_id=role_id,
                    permission_id=perm_id
                )
                db.session.add(role_perm)
            
            db.session.commit()
            
            return (True, "Permissions updated successfully")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating permissions: {e}")
            return (False, str(e))
    
    @staticmethod
    def get_all_permissions(category=None):
        """
        Get all available permissions
        
        Args:
            category: Optional category filter
        
        Returns:
            List of Permission objects
        """
        try:
            query = Permission.query.filter_by(is_active=True)
            
            if category:
                query = query.filter_by(category=category)
            
            return query.order_by(Permission.category, Permission.display_name).all()
            
        except Exception as e:
            print(f"Error getting permissions: {e}")
            return []
    
    @staticmethod
    def get_permission_categories():
        """
        Get all permission categories
        
        Returns:
            List of category names
        """
        try:
            categories = db.session.query(Permission.category).filter(
                Permission.is_active == True
            ).distinct().all()
            
            return [c[0] for c in categories if c[0]]
            
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []
    
    @staticmethod
    def ensure_user_has_company_admin_role(user_id, company_id):
        """
        Ensure a user has the company admin role
        Used for company owners/primary admins
        
        Args:
            user_id: User ID
            company_id: Company ID
        
        Returns:
            Boolean indicating success
        """
        try:
            # Get company admin role
            admin_role = CompanyRole.query.filter_by(
                company_id=company_id,
                name='company_admin'
            ).first()
            
            if not admin_role:
                return False
            
            # Check if user already has the role
            existing = UserCompanyRole.query.filter_by(
                user_id=user_id,
                role_id=admin_role.id
            ).first()
            
            if existing:
                return True
            
            # Assign role
            assignment = UserCompanyRole(
                user_id=user_id,
                role_id=admin_role.id
            )
            
            db.session.add(assignment)
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error ensuring company admin role: {e}")
            return False


# Permission decorator for Flask routes
from functools import wraps
from flask import flash, redirect, url_for

def permission_required(permission_name):
    """
    Decorator to require a specific permission for a route
    
    Usage:
        @app.route('/approve-tender')
        @permission_required('approve_tenders')
        def approve_tender():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is logged in
            if 'user_id' not in session:
                flash('Please log in to access this page', 'error')
                return redirect(url_for('auth.login'))
            
            user_id = session.get('user_id')
            company_id = session.get('company_id')
            
            # Check permission
            if not PermissionsService.user_has_permission(user_id, permission_name, company_id):
                flash('You do not have permission to access this feature', 'error')
                return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
