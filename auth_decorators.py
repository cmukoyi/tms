# Create a new file: auth_decorators.py

from functools import wraps
from flask import abort, session, flash, redirect, url_for, request
from models import User

def login_required(f):
    """Decorator to require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def requires_feature(feature_code):
    """Decorator to check if user's company has access to a feature"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('user_id'):
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('login'))
            
            user = User.query.get(session['user_id'])
            if not user:
                abort(401)
            
            # Check if user can access this feature
            if not user.can_access_feature(feature_code):
                flash(f'You do not have access to the {feature_code.replace("_", " ").title()} feature. Contact your administrator.', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def requires_role(role_level):
    """Decorator to check if user has a specific role level"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('user_id'):
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('login'))
            
            user = User.query.get(session['user_id'])
            if not user or not user.has_role(role_level):
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def requires_permission(action, feature_code=None):
    """Decorator to check if user can perform a specific action"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('user_id'):
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('login'))
            
            user = User.query.get(session['user_id'])
            if not user or not user.can_perform_action(action, feature_code):
                flash(f'You do not have permission to {action} this content.', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def super_admin_required(f):
    """Decorator to require super admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_super_admin():
            flash('Super admin access required.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def company_admin_required(f):
    """Decorator to require company admin or super admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        user = User.query.get(session['user_id'])
        if not user or (not user.is_super_admin() and not user.is_company_admin()):
            flash('Company admin access required.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

# Helper function to get current user
def get_current_user():
    """Get current logged-in user"""
    if session.get('user_id'):
        return User.query.get(session['user_id'])
    return None