
from functools import wraps
from flask import session, flash, redirect, url_for
from services import AuthService

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    """Decorator to require super admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        user = AuthService.get_user_by_id(session['user_id'])
        if not user or not user.is_super_admin:
            flash('Access denied. Super admin privileges required.', 'error')
            return redirect(url_for('reports.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def company_admin_required(f):
    """Decorator to require company admin or super admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        user = AuthService.get_user_by_id(session['user_id'])
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('auth.login'))
        
        # Allow super admin or company admin
        if user.is_super_admin or (user.role and user.role.name == 'Company Admin'):
            return f(*args, **kwargs)
        else:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('reports.dashboard'))
    return decorated_function