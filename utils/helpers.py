# utils/helpers.py
from datetime import datetime
from zoneinfo import ZoneInfo
import tzlocal
from flask import session
from services import AuthService

def get_local_time():
    """Get local timezone time"""
    try:
        import tzlocal
        local_tz_name = tzlocal.get_localzone_name()
    except ImportError:
        local_tz_name = 'UTC'
    
    local_now = datetime.now(ZoneInfo(local_tz_name))
    return local_now

def user_can_access_module(module_name):
    """Check if current user's company has access to a module"""
    from services.company_module_service import CompanyModuleService
    company_id = session.get('company_id')
    if not company_id:
        return False
    
    return CompanyModuleService.is_module_enabled_for_company(company_id, module_name)

def can_access_module(module_name):
    """Check if current user can access a specific module"""
    user_id = session.get('user_id')
    if not user_id:
        return False
    
    user = AuthService.get_user_by_id(user_id)
    if not user or not user.company_id:
        return False
    
    # Core modules are always available
    core_modules = ['tender_management', 'user_management']
    if module_name in core_modules:
        return True
    
    # Basic modules
    basic_modules = ['document_management', 'notes_comments']
    if module_name in basic_modules:
        return True
    
    # Premium modules require specific access
    premium_modules = ['reporting', 'custom_fields', 'company_management']
    if module_name in premium_modules:
        return user.role and user.role.name == 'Super Admin'
    
    return False

def get_company_enabled_modules(company_id):
    """Get list of enabled modules for a company"""
    from models import db
    from sqlalchemy import text
    
    # This is a simple implementation - you can store this in database later
    # For now, let's check if there's a company_modules table
    try:
        # Try to get from database (if table exists)
        query = db.session.execute(
            text("SELECT module_name FROM company_modules WHERE company_id = :company_id AND enabled = 1"),
            {'company_id': company_id}
        )
        return [row[0] for row in query.fetchall()]
    except:
        # If table doesn't exist, return default enabled modules
        return ['analytics', 'notifications']  # Some default enabled modules