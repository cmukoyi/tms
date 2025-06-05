# feature_helpers.py - Helper functions and decorators for feature management

from functools import wraps
from flask import abort, flash, redirect, url_for, session, request
from flask_login import current_user
from models import Company

def get_current_company():
    """Get the current user's company"""
    if hasattr(current_user, 'company_id') and current_user.company_id:
        return Company.query.get(current_user.company_id)
    return None

def has_feature(feature_code):
    """Check if current user's company has a specific feature"""
    company = get_current_company()
    if company:
        return company.has_feature(feature_code)
    return False

def feature_required(feature_code, redirect_url=None):
    """Decorator to require a specific feature for access"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not has_feature(feature_code):
                flash(f'This feature is not available for your account. Please contact support to upgrade.', 'warning')
                if redirect_url:
                    return redirect(redirect_url)
                else:
                    return redirect(url_for('main.dashboard'))  # Adjust to your dashboard route
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_menu_items():
    """Get menu items based on company features"""
    base_menu = [
        {
            'name': 'Dashboard',
            'url': 'main.dashboard',
            'icon': 'fas fa-tachometer-alt',
            'feature': 'dashboard'
        },
        {
            'name': 'Tenders',
            'url': 'main.tenders',
            'icon': 'fas fa-file-contract',
            'feature': 'tenders'
        },
        {
            'name': 'Files',
            'url': 'main.files',
            'icon': 'fas fa-folder',
            'feature': 'files'
        },
        {
            'name': 'Reports',
            'url': 'main.reports',
            'icon': 'fas fa-chart-bar',
            'feature': 'reports'
        },
        {
            'name': 'Analytics',
            'url': 'main.analytics',
            'icon': 'fas fa-analytics',
            'feature': 'analytics'
        },
        {
            'name': 'Users',
            'url': 'main.users',
            'icon': 'fas fa-users',
            'feature': 'user_management'
        }
    ]
    
    # Filter menu items based on features
    available_menu = []
    for item in base_menu:
        if has_feature(item['feature']):
            available_menu.append(item)
    
    return available_menu

def inject_menu_context():
    """Template context processor to inject menu items"""
    return dict(menu_items=get_menu_items())

# Usage in templates: 
# Add this to your app context processor or use directly in templates