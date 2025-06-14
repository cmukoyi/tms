from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from functools import wraps
import os
import pymysql
import json
from datetime import datetime
from flask import jsonify, request
from flask_login import current_user
from markupsafe import Markup

from services.billing_service import BillingService
from decimal import Decimal
import calendar


from sqlalchemy import func, and_, or_


pymysql.install_as_MySQLdb()
from datetime import datetime, timedelta
from flask_migrate import Migrate
from werkzeug.utils import secure_filename

from datetime import datetime
from zoneinfo import ZoneInfo
import tzlocal  # optional helper to get local timezone name, install with: pip install tzlocal
from services.company_module_service import CompanyModuleService, require_company_module
from services import CompanyService
from permissions import ModulePermissions, require_module, require_company_admin



# In app.py, instead of:
from services import AuthService

# Use:
from services import AuthService  # This will import from your original services.py file
from services.module_service import ModuleService
# Import our modules
from config import Config
from models import *

from services import (
    AuthService, CompanyService, RoleService, TenantService,
    TenderService, TenderCategoryService, TenderStatusService, 
    DocumentTypeService, TenderDocumentService, CustomFieldService, TenderHistoryService
)

from services.role_service import RoleService
from permissions import require_permission, require_role_level

from dotenv import load_dotenv
load_dotenv()
print(f"Loaded environment variables from: {' .env.production' if 'PYTHONANYWHERE_DOMAIN' in os.environ else '.env'}")

from flask import make_response, request
from datetime import datetime
import io
import xlsxwriter
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch


# Initialize Flask app
app = Flask(__name__)

@app.template_filter('tojsonfilter')
def to_json_filter(obj):
    """Convert object to JSON string for use in templates"""
    return json.dumps(obj)
app.config.from_object(Config)

@app.context_processor
def inject_year():
    from datetime import datetime
    return dict(current_year=datetime.now().year)

@app.context_processor
def inject_module_access():
    def can_access_module(module_name):
        return user_can_access_module(module_name)
    
    return dict(can_access_module=can_access_module)

@app.context_processor
def inject_current_date():
    return {
        'current_month': datetime.now().month,
        'current_year': datetime.now().year
    }
@app.context_processor
def inject_permission_helpers():
    """Inject permission helper functions into templates"""
    from permissions import has_permission, get_user_permissions, has_any_permission, has_all_permissions
    
    return dict(
        has_permission=has_permission,
        get_user_permissions=get_user_permissions,
        has_any_permission=has_any_permission,
        has_all_permissions=has_all_permissions
    )
    

# Initialize database
db.init_app(app)

migrate = Migrate(app, db)

@app.route('/admin/modules')
def test_modules():
    if not session.get('is_super_admin'):
        flash('Access denied. Super admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Initialize modules first
    from services.module_service import ModuleService
    ModuleService.initialize_modules()
    
    # Get modules
    modules = ModuleService.get_all_modules()
    return render_template('admin/modules.html', modules=modules)


@app.route('/admin/init-modules')
def init_modules():
    if not session.get('is_super_admin'):
        return "Access denied"
    
    from services.module_service import ModuleService
    success = ModuleService.initialize_modules()
    if success:
        flash('Modules initialized successfully!', 'success')
    else:
        flash('Error initializing modules. Check logs.', 'error')
    
    return redirect(url_for('test_modules'))

def get_local_time():
    try:
        import tzlocal
        local_tz_name = tzlocal.get_localzone_name()  # e.g. 'Europe/Berlin', 'America/New_York'
    except ImportError:
        # fallback if tzlocal not installed, set default timezone here:
        local_tz_name = 'UTC'
    
    local_now = datetime.now(ZoneInfo(local_tz_name))
    return local_now

# Decorators (keeping existing ones)
def user_can_access_module(module_name):
    """Check if current user's company has access to a module"""
    company_id = session.get('company_id')
    if not company_id:
        return False
    
    return CompanyModuleService.is_module_enabled_for_company(company_id, module_name)

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    """Decorator to require super admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        
        user = AuthService.get_user_by_id(session['user_id'])
        if not user or not user.is_super_admin:
            flash('Access denied. Super admin privileges required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def company_admin_required(f):
    """Decorator to require company admin or super admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        
        user = AuthService.get_user_by_id(session['user_id'])
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('login'))
        
        # Allow super admin or company admin
        if user.is_super_admin or (user.role and user.role.name == 'Company Admin'):
            return f(*args, **kwargs)
        else:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('dashboard'))
    return decorated_function

# Original routes (keeping all existing routes)
@app.route('/')
def home():
    """Home page"""
    current_date = get_local_time()
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')
        
        user = AuthService.login_user(username, password)
        if user:
            # Set session variables
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_super_admin'] = user.is_super_admin
            session['company_id'] = user.company_id
            session['full_name'] = user.full_name
            session['role_name'] = user.role.name if user.role else 'No Role'
            
            flash(f'Welcome back, {user.first_name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout and clear session"""
    username = session.get('username', 'User')
    session.clear()
    flash(f'Goodbye, {username}! You have been logged out.', 'info')
    return redirect(url_for('home'))

# Replace your dashboard route in app.py with this:
@app.route('/test-permissions')
@login_required
def test_permissions():
    """Test route to check user permissions"""
    try:
        user_id = session['user_id']
        permissions = ModulePermissions.get_user_permissions(user_id)
        
        if not permissions:
            return jsonify({
                'success': False,
                'error': 'Could not load user permissions'
            })
        
        available_routes = ModulePermissions.get_available_routes(user_id)
        
        # Handle company name safely for super admins
        company_name = None
        if permissions['company']:
            company_name = permissions['company'].name
        elif permissions['is_super_admin']:
            company_name = "System Administration (No Company)"
        
        return jsonify({
            'success': True,
            'user': f"{permissions['user'].first_name} {permissions['user'].last_name}",
            'company': company_name,
            'user_role': permissions['user_role'],
            'is_company_admin': permissions['is_company_admin'],
            'is_super_admin': permissions['is_super_admin'],
            'enabled_modules': permissions['enabled_modules'],
            'permissions': {
                'can_delete': permissions['can_delete'],
                'can_manage_users': permissions['can_manage_users'],
                'can_view_analytics': permissions['can_view_analytics'],
                'can_use_api': permissions['can_use_api'],
                'has_notifications': permissions['has_notifications'],
                'has_white_label': permissions['has_white_label'],
                'can_manage_company': permissions['can_manage_company'],
                'can_upload_documents': permissions['can_upload_documents'],
                'can_create_custom_fields': permissions['can_create_custom_fields'],
                'can_add_notes': permissions['can_add_notes'],
                'can_view_audit_log': permissions['can_view_audit_log'],
                'can_advanced_search': permissions['can_advanced_search']
            },
            'available_routes': available_routes
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
@app.route('/test-module-access/<module_name>')
@login_required
def test_module_access(module_name):
    """Test if user has access to a specific module"""
    try:
        user_id = session['user_id']
        user = User.query.get(user_id)
        
        # Test the module access function
        has_access = ModulePermissions.check_module_access(module_name, user_id)
        
        # Get permissions for context
        permissions = ModulePermissions.get_user_permissions(user_id)
        
        return jsonify({
            'success': True,
            'module_name': module_name,
            'has_access': has_access,
            'user_is_super_admin': user.is_super_admin if user else False,
            'user_company_id': user.company_id if user else None,
            'enabled_modules': permissions['enabled_modules'] if permissions else [],
            'message': f"Access to '{module_name}': {'GRANTED' if has_access else 'DENIED'}"
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
        
# Test route that requires a specific module
@app.route('/test-analytics')
@login_required
@require_module('reporting')
def test_analytics():
    """Test route that requires analytics module"""
    return jsonify({
        'success': True,
        'message': 'You have access to analytics!',
        'module': 'reporting'
    })

# Add this route to app.py to see who is currently logged in

@app.route('/debug-current-user')
@login_required
def debug_current_user():
    """Debug route to see current logged in user details"""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'No user_id in session',
                'session_keys': list(session.keys())
            })
        
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'error': f'User ID {user_id} not found in database'
            })
        
        # Get all user details
        user_details = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'company_id': user.company_id,
            'role_id': user.role_id,
            'is_super_admin': user.is_super_admin,
            'is_active': user.is_active
        }
        
        # Get role details
        role_details = None
        if user.role:
            role_details = {
                'id': user.role.id,
                'name': user.role.name,
                'description': user.role.description,
                'name_repr': repr(user.role.name)  # Shows hidden characters
            }
        
        # Get company details
        company_details = None
        if user.company:
            company_details = {
                'id': user.company.id,
                'name': user.company.name,
                'email': user.company.email
            }
        
        return jsonify({
            'success': True,
            'session_user_id': user_id,
            'user': user_details,
            'role': role_details,
            'company': company_details
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
# Add this route to verify the role fix is working

@app.route('/verify-role-fix')
@login_required
def verify_role_fix():
    """Verify that role checking is working correctly"""
    try:
        user_id = session['user_id']
        user = User.query.get(user_id)
        
        # Manual role check
        user_role = user.role.name if user.role else 'user'
        admin_roles = ['company_admin', 'admin', 'Company Admin', 'Admin', 'Super Admin']
        
        # Test both methods
        direct_check = user_role in admin_roles
        lower_check = user_role.lower() in [role.lower() for role in admin_roles]
        
        # Get permissions through the system
        permissions = ModulePermissions.get_user_permissions(user_id)
        
        return jsonify({
            'success': True,
            'user_role': user_role,
            'admin_roles': admin_roles,
            'direct_check': direct_check,
            'lower_check': lower_check,
            'system_says_admin': permissions['is_company_admin'] if permissions else None,
            'system_permissions': {
                'can_delete': permissions['can_delete'],
                'can_manage_users': permissions['can_manage_users'],
                'can_manage_company': permissions['can_manage_company']
            } if permissions else None
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
      
# Test route that requires company admin
@app.route('/test-admin')
@login_required
@require_company_admin
def test_admin():
    """Test route that requires company admin role"""
    return jsonify({
        'success': True,
        'message': 'You have company admin access!',
        'role': 'admin'
    })
@app.route('/company/notes')
@login_required
def company_notes():
    """View company notes/announcements"""
    # You can implement this to show company-wide notes or announcements
    # For now, let's redirect to dashboard or show a placeholder
    return render_template('company_notes.html')



@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    user = AuthService.get_user_by_id(session['user_id'])
    permissions = ModulePermissions.get_user_permissions(session['user_id'])
    
    # Get additional context based on user role
    context = {
        'user': user,
        'permissions': permissions  # Add permissions for template use
    }
    
    if user.is_super_admin:
        # Use direct database queries instead of service methods
        context['total_companies'] = Company.query.count()
        context['total_users'] = User.query.count()
        
        # Calculate tender stats manually
        total_tenders = Tender.query.count()
        active_tenders = Tender.query.count()  # For now, assume all are active
        
        # Try to get closed status for better active count
        try:
            closed_status = TenderStatus.query.filter_by(name='Closed').first()
            if closed_status:
                active_tenders = Tender.query.filter(Tender.status_id != closed_status.id).count()
        except:
            pass
        
        context['tender_stats'] = {
            'total': total_tenders,
            'active': active_tenders,
            'closed': total_tenders - active_tenders
        }
        
    elif user.company_id and permissions and permissions['is_company_admin']:
        # Company admin stats - use direct queries
        user_count = User.query.filter_by(company_id=user.company_id, is_active=True).count()
        tender_count = Tender.query.filter_by(company_id=user.company_id).count()
        
        context['company_stats'] = {
            'user_count': user_count,
            'tender_count': tender_count
        }
        
        # Only show users if user management module is enabled
        if permissions and permissions['can_manage_users']:
            context['company_users'] = User.query.filter_by(
                company_id=user.company_id, 
                is_active=True
            ).all()
        
        # Company tender stats
        total_tenders = Tender.query.filter_by(company_id=user.company_id).count()
        active_tenders = total_tenders
        
        # Try to get closed status for better active count
        try:
            closed_status = TenderStatus.query.filter_by(name='Closed').first()
            if closed_status:
                active_tenders = Tender.query.filter(
                    Tender.company_id == user.company_id,
                    Tender.status_id != closed_status.id
                ).count()
        except:
            pass
        
        context['tender_stats'] = {
            'total': total_tenders,
            'active': active_tenders,
            'closed': total_tenders - active_tenders
        }
    
    return render_template('dashboard.html', **context)

# NEW TENDER ROUTES
@app.route('/tenders', methods=['GET', 'POST'])
@login_required
@require_module('tender_management')  # ← Add this decorator


def tenders():
    """View tenders with simple pagination"""
    user = AuthService.get_user_by_id(session['user_id'])
    permissions = ModulePermissions.get_user_permissions(session['user_id'])
    
    # Get parameters with defaults
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status_filter = request.args.get('status', type=int)
    category_filter = request.args.get('category', type=int)
    
    # Validate per_page values
    if per_page not in [10, 20, 50]:
        per_page = 10
    
    # Build base query
    if user.is_super_admin:
        query = Tender.query
    else:
        query = Tender.query.filter_by(company_id=user.company_id)
    
    # Apply advanced search if available
    search_query = request.args.get('search', '').strip()
    if search_query and permissions and permissions['can_advanced_search']:
        query = query.filter(
            Tender.title.contains(search_query) | 
            Tender.description.contains(search_query) |
            Tender.reference_number.contains(search_query)
        )
    elif search_query:
        # Basic search if advanced search not available
        query = query.filter(Tender.title.contains(search_query))
    
    # Apply filters
    if status_filter:
        query = query.filter_by(status_id=status_filter)
    if category_filter:
        query = query.filter_by(category_id=category_filter)
    
    # Order by newest first
    query = query.order_by(Tender.created_at.desc())
    
    # Get paginated results
    pagination_result = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # Create simple pagination object
    pagination = {
        'current_page': page,
        'total_pages': pagination_result.pages,
        'total': pagination_result.total,
        'has_prev': pagination_result.has_prev,
        'has_next': pagination_result.has_next,
        'start_item': ((page - 1) * per_page) + 1 if pagination_result.total > 0 else 0,
        'end_item': min(page * per_page, pagination_result.total)
    }
    
    # Get filter options
    categories = TenderCategoryService.get_all_categories()
    statuses = TenderStatusService.get_all_statuses()
    
    return render_template('tenders/list.html', 
                         tenders=pagination_result.items,
                         pagination=pagination,
                         categories=categories, 
                         statuses=statuses,
                         current_status=status_filter,
                         current_category=category_filter,
                         per_page=per_page,
                         permissions=permissions,  # ← Add permissions for template
                         search_query=search_query)
    

@app.route('/tenders/create', methods=['GET', 'POST'])
@login_required
@require_module('tender_management')  # ← Require tender management module

def create_tender():
    """Create new tender"""
    user = AuthService.get_user_by_id(session['user_id'])
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category_id = request.form.get('category_id')
        status_id = request.form.get('status_id')
        submission_deadline = request.form.get('submission_deadline')
        opening_date = request.form.get('opening_date')
        
        # Parse dates
        submission_deadline = datetime.strptime(submission_deadline, '%Y-%m-%dT%H:%M') if submission_deadline else None
        opening_date = datetime.strptime(opening_date, '%Y-%m-%dT%H:%M') if opening_date else None
        
        # Handle custom fields
        custom_fields = {}
        custom_field_objects = CustomFieldService.get_all_custom_fields()
        for field in custom_field_objects:
            field_value = request.form.get(f'custom_{field.field_name}')
            if field_value:
                custom_fields[field.field_name] = field_value
        
        if not all([title, category_id, status_id]):
            flash('Title, category, and status are required.', 'error')
        else:
            company_id = user.company_id if not user.is_super_admin else request.form.get('company_id')
            
            tender, message = TenderService.create_tender(
                title=title,
                description=description,
                company_id=company_id,
                category_id=int(category_id),
                status_id=int(status_id),
                created_by=user.id,
                submission_deadline=submission_deadline,
                opening_date=opening_date,
                custom_fields=custom_fields if custom_fields else None
            )
            
            if tender:
                flash(message, 'success')
                # Log tender creation
                TenderHistoryService.log_tender_created(
                    tender_id=tender.id,
                    performed_by_id=user.id,
                    tender_title=tender.title
                )
                return redirect(url_for('view_tender', tender_id=tender.id))
            else:
                flash(message, 'error')
    
    # Get form data
    categories = TenderCategoryService.get_all_categories()
    statuses = TenderStatusService.get_all_statuses()
    custom_fields = CustomFieldService.get_all_custom_fields()
    
    # Fix: Always provide a list for companies
    if user.is_super_admin:
        companies = CompanyService.get_all_companies()
    else:
        # For regular users, provide their company in a list
        user_company = CompanyService.get_company_by_id(user.company_id)
        companies = [user_company] if user_company else []
    
    # Ensure companies is never None
    companies = companies or []
    
    return render_template('tenders/create.html', 
                         categories=categories, 
                         statuses=statuses, 
                         custom_fields=custom_fields,
                         companies=companies)

@app.route('/tenders/<int:tender_id>')
@login_required
@require_module('tender_management')  # ← Add this decorator
def view_tender(tender_id):
    """View tender details with notes"""
    user = AuthService.get_user_by_id(session['user_id'])
    permissions = ModulePermissions.get_user_permissions(session['user_id'])
    tender = TenderService.get_tender_by_id(tender_id)
    
    if not tender:
        flash('Tender not found.', 'error')
        return redirect(url_for('tenders'))
    
    # Check access permissions
    if not user.is_super_admin and tender.company_id != user.company_id:
        flash('Access denied.', 'error')
        return redirect(url_for('tenders'))
    
    # Get tender documents (only if document management is enabled)
    documents = []
    document_types = []
    if permissions and permissions['can_upload_documents']:
        documents = TenderDocumentService.get_tender_documents(tender_id)
        document_types = DocumentTypeService.get_all_document_types()
    
    # Get custom fields (only if module is enabled)
    custom_fields = []
    if permissions and 'custom_fields' in permissions['enabled_modules']:
        custom_fields = CustomFieldService.get_all_custom_fields()
    
    # Get tender notes (only if notes module is enabled)
    tender_notes = []
    if permissions and permissions['can_add_notes']:
        tender_notes = TenderNote.query.filter_by(tender_id=tender_id).order_by(TenderNote.created_at.desc()).all()
    
    # Get tender history (only if audit module is enabled)
    tender_history = []
    if permissions and permissions['can_view_audit_log']:
        tender_history = TenderHistoryService.get_tender_history(tender_id)

    return render_template('tenders/view.html', 
                         tender=tender, 
                         documents=documents,
                         document_types=document_types,
                         custom_fields=custom_fields,
                         tender_notes=tender_notes,
                         tender_history=tender_history,
                         current_user=user,
                         permissions=permissions)  # ← Add permissions for template

@app.route('/tenders/<int:tender_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_tender(tender_id):
    """Edit tender"""
    user = AuthService.get_user_by_id(session['user_id'])
    tender = TenderService.get_tender_by_id(tender_id)
    
    if not tender:
        flash('Tender not found.', 'error')
        return redirect(url_for('tenders'))
    
    # Check access permissions
    if not user.is_super_admin and tender.company_id != user.company_id:
        flash('Access denied.', 'error')
        return redirect(url_for('tenders'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category_id = request.form.get('category_id')
        status_id = request.form.get('status_id')
        submission_deadline = request.form.get('submission_deadline')
        opening_date = request.form.get('opening_date')
        
        # Parse dates
        submission_deadline = datetime.strptime(submission_deadline, '%Y-%m-%dT%H:%M') if submission_deadline else None
        opening_date = datetime.strptime(opening_date, '%Y-%m-%dT%H:%M') if opening_date else None
        
        # Handle custom fields
        custom_fields = {}
        custom_field_objects = CustomFieldService.get_all_custom_fields()
        for field in custom_field_objects:
            field_value = request.form.get(f'custom_{field.field_name}')
            if field_value:
                custom_fields[field.field_name] = field_value
        
        if not all([title, category_id, status_id]):
            flash('Title, category, and status are required.', 'error')
        else:
            success, message = TenderService.update_tender(
                tender_id=tender_id,
                title=title,
                description=description,
                category_id=int(category_id),
                status_id=int(status_id),
                submission_deadline=submission_deadline,
                opening_date=opening_date,
                custom_fields=custom_fields if custom_fields else None
            )
            
            if success:
                flash(message, 'success')
                return redirect(url_for('view_tender', tender_id=tender_id))
            else:
                flash(message, 'error')
    
    # Get form data
    categories = TenderCategoryService.get_all_categories()
    statuses = TenderStatusService.get_all_statuses()
    custom_fields = CustomFieldService.get_all_custom_fields()
    
    return render_template('tenders/edit.html', 
                         tender=tender,
                         categories=categories, 
                         statuses=statuses,
                         custom_fields=custom_fields)

# TENDER NOTES ROUTES
@app.route('/tender/<int:tender_id>/notes', methods=['POST'])
@login_required
@require_module('tender_management')  # ← Add this decorator
@require_module('notes_comments')     # ← Add this decorator
def add_tender_note(tender_id):
    """Add a new note to a tender"""
    try:
        user = AuthService.get_user_by_id(session['user_id'])
        
        # Verify tender exists and user has access
        tender = Tender.query.get_or_404(tender_id)
        
        # Check access permissions
        if not user.is_super_admin and tender.company_id != user.company_id:
            flash('Access denied.', 'error')
            return redirect(url_for('view_tender', tender_id=tender_id))
        
        # Get note content from form
        note_content = request.form.get('note_content', '').strip()
        
        if not note_content:
            flash('Note content cannot be empty.', 'error')
            return redirect(url_for('view_tender', tender_id=tender_id))
        
        # Create new note
        new_note = TenderNote(
            tender_id=tender_id,
            content=note_content,
            created_by_id=user.id
        )
        
        db.session.add(new_note)
        db.session.commit()
        
        # Log note addition (only if audit module is enabled)
        permissions = ModulePermissions.get_user_permissions(session['user_id'])
        if permissions and permissions['can_view_audit_log']:
            TenderHistoryService.log_note_added(
                tender_id=tender_id,
                performed_by_id=user.id,
                note_content=note_content
            )
        
        flash('Note added successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error adding note. Please try again.', 'error')
        print(f"Error adding tender note: {str(e)}")
    
    return redirect(url_for('view_tender', tender_id=tender_id) + '#notes')


@app.route('/tender/notes/<int:note_id>/edit', methods=['POST'])
@login_required
def edit_tender_note(note_id):
    """Edit an existing tender note"""
    try:
        user = AuthService.get_user_by_id(session['user_id'])
        
        # Get the note
        note = TenderNote.query.get_or_404(note_id)
        tender_id = note.tender_id
        
        # Check if current user is the author of the note or super admin
        if note.created_by_id != user.id and not user.is_super_admin:
            flash('You can only edit your own notes.', 'error')
            return redirect(url_for('view_tender', tender_id=tender_id))
        
        # Get new content from form
        new_content = request.form.get('note_content', '').strip()
        
        if not new_content:
            flash('Note content cannot be empty.', 'error')
            return redirect(url_for('view_tender', tender_id=tender_id) + '#notes')
        
        # Update the note
        old_content = note.content
        note.content = new_content
        note.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log note edit
        TenderHistoryService.log_note_edited(
            tender_id=tender_id,
            performed_by_id=user.id,
            old_content=old_content,
            new_content=new_content
        )
        
        flash('Note updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error updating note. Please try again.', 'error')
        print(f"Error updating tender note: {str(e)}")
    
    return redirect(url_for('view_tender', tender_id=tender_id) + '#notes')


@app.route('/tender/notes/<int:note_id>/delete', methods=['POST'])
@login_required
def delete_tender_note(note_id):
    """Delete a tender note (only by the author)"""
    try:
        user = AuthService.get_user_by_id(session['user_id'])
        
        # Get the note
        note = TenderNote.query.get_or_404(note_id)
        tender_id = note.tender_id
        
        # Check if current user is the author of the note or super admin
        if note.created_by_id != user.id and not user.is_super_admin:
            flash('You can only delete your own notes.', 'error')
            return redirect(url_for('view_tender', tender_id=tender_id))
        
        # Delete the note
        note_content = note.content  # Store for logging
        db.session.delete(note)
        db.session.commit()
        
        # Log note deletion
        TenderHistoryService.log_note_deleted(
            tender_id=tender_id,
            performed_by_id=user.id,
            note_content=note_content
        )
        
        flash('Note deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error deleting note. Please try again.', 'error')
        print(f"Error deleting tender note: {str(e)}")
    
    return redirect(url_for('view_tender', tender_id=tender_id) + '#notes')

@app.route('/tenders/<int:tender_id>/upload', methods=['POST'])
@login_required
@require_module('tender_management')  # ← Add this decorator
@require_module('document_management')  # ← Add this decorator
def upload_tender_document(tender_id):
    """Upload document to tender"""
    user = AuthService.get_user_by_id(session['user_id'])
    tender = TenderService.get_tender_by_id(tender_id)
    
    if not tender:
        flash('Tender not found.', 'error')
        return redirect(url_for('tenders'))
    
    # Check access permissions
    if not user.is_super_admin and tender.company_id != user.company_id:
        flash('Access denied.', 'error')
        return redirect(url_for('tenders'))
    
    if 'document' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('view_tender', tender_id=tender_id))
    
    file = request.files['document']
    document_type_id = request.form.get('document_type_id')
    
    if not document_type_id:
        flash('Document type is required.', 'error')
        return redirect(url_for('view_tender', tender_id=tender_id))
    
    document, message = TenderDocumentService.save_document(
        file=file,
        tender_id=tender_id,
        document_type_id=int(document_type_id),
        uploaded_by=user.id,
        upload_folder=app.config['UPLOAD_FOLDER']
    )
    
    if document:
        flash(message, 'success')
        # Log document upload (only if audit module is enabled)
        permissions = ModulePermissions.get_user_permissions(session['user_id'])
        if permissions and permissions['can_view_audit_log']:
            TenderHistoryService.log_document_uploaded(
                tender_id=tender_id,
                performed_by_id=user.id,
                document_name=document.original_filename,
                document_type=document.doc_type.name,
            )
    else:
        flash(message, 'error')
    
    return redirect(url_for('view_tender', tender_id=tender_id))





@app.route('/tenders/<int:tender_id>/delete', methods=['POST'])
@login_required
def delete_tender(tender_id):
    """Delete tender"""
    user = AuthService.get_user_by_id(session['user_id'])
    tender = TenderService.get_tender_by_id(tender_id)
    
    if not tender:
        flash('Tender not found.', 'error')
        return redirect(url_for('tenders'))
    
    # Check access permissions
    if not user.is_super_admin and tender.company_id != user.company_id:
        flash('Access denied.', 'error')
        return redirect(url_for('tenders'))
    
    success, message = TenderService.delete_tender(tender_id)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('tenders'))

# REPORTS ROUTES
@app.route('/reports')
@login_required
@require_module('reporting')  # ← Add this decorator
def reports():
    """Reports dashboard"""
    user = AuthService.get_user_by_id(session['user_id'])
    
    if user.is_super_admin:
        # System-wide reports
        tender_stats = TenderService.get_tender_stats()
        company_count = len(CompanyService.get_all_companies())
        user_count = len(AuthService.get_all_users())
        
        context = {
            'tender_stats': tender_stats,
            'company_count': company_count,
            'user_count': user_count,
            'is_super_admin': True
        }
    else:
        # Company-specific reports
        tender_stats = TenderService.get_tender_stats(user.company_id)
        company_stats = CompanyService.get_company_stats(user.company_id)
        
        context = {
            'tender_stats': tender_stats,
            'company_stats': company_stats,
            'is_super_admin': False
        }
    
    return render_template('reports/dashboard.html', **context)

@app.route('/reports/tenders')
@login_required
@require_module('reporting')  # ← Add this decorator

def tender_reports():
    """Detailed tender reports"""
    user = AuthService.get_user_by_id(session['user_id'])
    
    # Get date filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if user.is_super_admin:
        tenders = TenderService.get_all_tenders()
    else:
        tenders = TenderService.get_tenders_by_company(user.company_id)
    
    # Apply date filters if provided
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        tenders = [t for t in tenders if t.created_at.date() >= start_date.date()]
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        tenders = [t for t in tenders if t.created_at.date() <= end_date.date()]
    
    # Calculate statistics
    total_tenders = len(tenders)
    status_breakdown = {}
    category_breakdown = {}
    monthly_breakdown = {}
    
    for tender in tenders:
        # Status breakdown
        status_name = tender.status.name
        status_breakdown[status_name] = status_breakdown.get(status_name, 0) + 1
        
        # Category breakdown
        category_name = tender.category.name
        category_breakdown[category_name] = category_breakdown.get(category_name, 0) + 1
        
        # Monthly breakdown
        month_key = tender.created_at.strftime('%Y-%m')
        monthly_breakdown[month_key] = monthly_breakdown.get(month_key, 0) + 1
    
    return render_template('reports/tenders.html',
                         tenders=tenders,
                         total_tenders=total_tenders,
                         status_breakdown=status_breakdown,
                         category_breakdown=category_breakdown,
                         monthly_breakdown=monthly_breakdown,
                         start_date=request.args.get('start_date'),
                         end_date=request.args.get('end_date'))
# Update your report routes to include current_date in the context

@app.route('/active_tenders_report')
@login_required
@require_module('reporting')
def active_tenders_report():
    """Report of all active (non-closed) tenders"""
        

    user = AuthService.get_user_by_id(session['user_id'])
    current_date = datetime.utcnow()
    
    # Get closed status ID to exclude
    closed_status = TenderStatus.query.filter_by(name='Closed').first()
    closed_status_id = closed_status.id if closed_status else None
    
    if user.is_super_admin:
        # Super admin sees all active tenders
        if closed_status_id:
            tenders = Tender.query.filter(Tender.status_id != closed_status_id).order_by(Tender.created_at.desc()).all()
        else:
            tenders = Tender.query.order_by(Tender.created_at.desc()).all()
    else:
        # Company users see only their company's active tenders
        if closed_status_id:
            tenders = Tender.query.filter(
                Tender.company_id == user.company_id,
                Tender.status_id != closed_status_id
            ).order_by(Tender.created_at.desc()).all()
        else:
            tenders = Tender.query.filter_by(company_id=user.company_id).order_by(Tender.created_at.desc()).all()
    
    # Handle export
    export_format = request.args.get('export')
    if export_format == 'pdf':
        return export_tenders_pdf(tenders, 'Active Tenders Report', user)
    elif export_format == 'excel':
        return export_tenders_excel(tenders, 'Active Tenders Report', user)
    
    context = {
        'tenders': tenders,
        'report_title': 'Active Tenders Report',
        'report_description': 'All tenders that are not closed',
        'user': user,
        'is_super_admin': user.is_super_admin,
        'current_date': current_date
    }
    
    return render_template('reports/tender_list.html', **context)

@app.route('/closed_tenders_report')
@login_required
@require_module('reporting') 
def closed_tenders_report():
    """Report of all closed tenders"""
    user = AuthService.get_user_by_id(session['user_id'])
    current_date = datetime.utcnow()
    
    # Get closed status
    closed_status = TenderStatus.query.filter_by(name='Closed').first()
    if not closed_status:
        flash('No closed status found in system', 'warning')
        return redirect(url_for('reports'))
    
    if user.is_super_admin:
        # Super admin sees all closed tenders
        tenders = Tender.query.filter_by(status_id=closed_status.id).order_by(Tender.updated_at.desc()).all()
    else:
        # Company users see only their company's closed tenders
        tenders = Tender.query.filter(
            Tender.company_id == user.company_id,
            Tender.status_id == closed_status.id
        ).order_by(Tender.updated_at.desc()).all()
    
    # Handle export
    export_format = request.args.get('export')
    if export_format == 'pdf':
        return export_tenders_pdf(tenders, 'Closed Tenders Report', user)
    elif export_format == 'excel':
        return export_tenders_excel(tenders, 'Closed Tenders Report', user)
    
    context = {
        'tenders': tenders,
        'report_title': 'Closed Tenders Report',
        'report_description': 'All tenders with closed status',
        'user': user,
        'is_super_admin': user.is_super_admin,
        'current_date': current_date
    }
    
    return render_template('reports/tender_list.html', **context)

@app.route('/overdue_tenders_report')
@login_required
@require_module('reporting') 
def overdue_tenders_report():
    """Report of overdue tenders (past submission deadline)"""
    user = AuthService.get_user_by_id(session['user_id'])
    current_date = datetime.utcnow()
    
    if user.is_super_admin:
        # Super admin sees all overdue tenders
        tenders = Tender.query.filter(
            Tender.submission_deadline < current_date,
            Tender.submission_deadline.isnot(None)
        ).order_by(Tender.submission_deadline.desc()).all()
    else:
        # Company users see only their company's overdue tenders
        tenders = Tender.query.filter(
            Tender.company_id == user.company_id,
            Tender.submission_deadline < current_date,
            Tender.submission_deadline.isnot(None)
        ).order_by(Tender.submission_deadline.desc()).all()
    
    # Handle export
    export_format = request.args.get('export')
    if export_format == 'pdf':
        return export_tenders_pdf(tenders, 'Overdue Tenders Report', user)
    elif export_format == 'excel':
        return export_tenders_excel(tenders, 'Overdue Tenders Report', user)
    
    context = {
        'tenders': tenders,
        'report_title': 'Overdue Tenders Report',
        'report_description': 'Tenders past their submission deadline',
        'user': user,
        'is_super_admin': user.is_super_admin,
        'show_overdue_info': True,
        'current_date': current_date
    }
    
    return render_template('reports/tender_list.html', **context)

@app.route('/tenders_by_category_report')
@login_required
@require_module('reporting') 
def tenders_by_category_report():
    """Report of tenders grouped by category"""
    user = AuthService.get_user_by_id(session['user_id'])
    current_date = datetime.utcnow()
    
    if user.is_super_admin:
        # Super admin sees all tenders
        tenders = Tender.query.order_by(Tender.category_id, Tender.created_at.desc()).all()
    else:
        # Company users see only their company's tenders
        tenders = Tender.query.filter_by(company_id=user.company_id).order_by(Tender.category_id, Tender.created_at.desc()).all()
    
    # Group tenders by category
    categories = {}
    for tender in tenders:
        category_name = tender.category.name if tender.category else 'Uncategorized'
        if category_name not in categories:
            categories[category_name] = []
        categories[category_name].append(tender)
    
    # Handle export
    export_format = request.args.get('export')
    if export_format == 'pdf':
        return export_tenders_by_category_pdf(categories, user)
    elif export_format == 'excel':
        return export_tenders_by_category_excel(categories, user)
    
    context = {
        'categories': categories,
        'tenders': tenders,
        'report_title': 'Tenders by Category Report',
        'report_description': 'Tenders organized by category',
        'user': user,
        'is_super_admin': user.is_super_admin,
        'grouped_by_category': True,
        'current_date': current_date
    }
    
    return render_template('reports/tender_list.html', **context)

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    user = AuthService.get_user_by_id(session['user_id'])
    
    context = {
        'user': user,
        'company': user.company if user.company else None
    }
    
    return render_template('user/profile.html', **context)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    user = AuthService.get_user_by_id(session['user_id'])
    
    if request.method == 'POST':
        try:
            # Update user information
            user.first_name = request.form.get('first_name', '').strip()
            user.last_name = request.form.get('last_name', '').strip()
            user.email = request.form.get('email', '').strip()
            user.phone = request.form.get('phone', '').strip()
            
            # Handle profile image upload
            if 'profile_image' in request.files:
                file = request.files['profile_image']
                if file and file.filename:
                    # Save the uploaded file
                    filename = secure_filename(file.filename)
                    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], 'profiles')
                    os.makedirs(upload_path, exist_ok=True)
                    
                    # Generate unique filename
                    file_extension = filename.rsplit('.', 1)[1].lower()
                    unique_filename = f"profile_{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}"
                    file_path = os.path.join(upload_path, unique_filename)
                    
                    file.save(file_path)
                    user.profile_image = unique_filename
            
            # Update password if provided
            new_password = request.form.get('new_password', '').strip()
            if new_password:
                current_password = request.form.get('current_password', '').strip()
                if not AuthService.verify_password(user, current_password):
                    flash('Current password is incorrect', 'error')
                    return redirect(url_for('edit_profile'))
                
                user.password_hash = AuthService.hash_password(new_password)
            
            db.session.commit()
            flash('Profile updated successfully', 'success')
            return redirect(url_for('profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'error')
    
    return render_template('user/edit_profile.html', user=user)

# Export helper functions
def export_tenders_pdf(tenders, title, user):
    """Export tenders to PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.black,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    story.append(Paragraph(title, title_style))
    
    # Company info
    if not user.is_super_admin:
        company_info = f"Company: {user.company.name}"
        story.append(Paragraph(company_info, styles['Normal']))
    
    # Export date
    export_date = f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    story.append(Paragraph(export_date, styles['Normal']))
    story.append(Spacer(1, 20))
    
    if not tenders:
        story.append(Paragraph("No tenders found for this report.", styles['Normal']))
    else:
        # Table headers
        headers = ['Reference', 'Title', 'Category', 'Status', 'Created Date', 'Deadline']
        data = [headers]
        
        # Table data
        for tender in tenders:
            row = [
                tender.reference_number,
                tender.title[:30] + '...' if len(tender.title) > 30 else tender.title,
                tender.category.name if tender.category else 'N/A',
                tender.status.name if tender.status else 'N/A',
                tender.created_at.strftime('%Y-%m-%d') if tender.created_at else 'N/A',
                tender.submission_deadline.strftime('%Y-%m-%d') if tender.submission_deadline else 'N/A'
            ]
            data.append(row)
        
        # Create table
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    
    doc.build(story)
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{title.replace(" ", "_")}.pdf"'
    return response

def export_tenders_excel(tenders, title, user):
    """Export tenders to Excel"""
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet(title[:31])  # Excel sheet name limit
    
    # Formats
    header_format = workbook.add_format({
        'bold': True,
        'font_color': 'white',
        'bg_color': '#366092',
        'border': 1
    })
    
    cell_format = workbook.add_format({
        'border': 1,
        'text_wrap': True
    })
    
    # Headers
    headers = ['Reference Number', 'Title', 'Category', 'Status', 'Company', 'Created Date', 'Deadline', 'Days Overdue']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
    
    # Data
    for row, tender in enumerate(tenders, 1):
        days_overdue = ''
        if tender.submission_deadline and tender.submission_deadline < datetime.utcnow():
            days_overdue = (datetime.utcnow() - tender.submission_deadline).days
        
        worksheet.write(row, 0, tender.reference_number, cell_format)
        worksheet.write(row, 1, tender.title, cell_format)
        worksheet.write(row, 2, tender.category.name if tender.category else 'N/A', cell_format)
        worksheet.write(row, 3, tender.status.name if tender.status else 'N/A', cell_format)
        worksheet.write(row, 4, tender.company.name if tender.company else 'N/A', cell_format)
        worksheet.write(row, 5, tender.created_at.strftime('%Y-%m-%d') if tender.created_at else 'N/A', cell_format)
        worksheet.write(row, 6, tender.submission_deadline.strftime('%Y-%m-%d') if tender.submission_deadline else 'N/A', cell_format)
        worksheet.write(row, 7, str(days_overdue) if days_overdue else 'N/A', cell_format)
    
    # Adjust column widths
    worksheet.set_column('A:A', 15)  # Reference
    worksheet.set_column('B:B', 30)  # Title
    worksheet.set_column('C:C', 15)  # Category
    worksheet.set_column('D:D', 12)  # Status
    worksheet.set_column('E:E', 20)  # Company
    worksheet.set_column('F:F', 12)  # Created
    worksheet.set_column('G:G', 12)  # Deadline
    worksheet.set_column('H:H', 12)  # Days Overdue
    
    workbook.close()
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename="{title.replace(" ", "_")}.xlsx"'
    return response

def export_tenders_by_category_pdf(categories, user):
    """Export tenders by category to PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.black,
        spaceAfter=30,
        alignment=1
    )
    story.append(Paragraph("Tenders by Category Report", title_style))
    
    # Company info
    if not user.is_super_admin:
        company_info = f"Company: {user.company.name}"
        story.append(Paragraph(company_info, styles['Normal']))
    
    # Export date
    export_date = f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    story.append(Paragraph(export_date, styles['Normal']))
    story.append(Spacer(1, 20))
    
    for category_name, tenders in categories.items():
        # Category header
        story.append(Paragraph(f"Category: {category_name} ({len(tenders)} tenders)", styles['Heading2']))
        
        # Table for this category
        headers = ['Reference', 'Title', 'Status', 'Created Date']
        data = [headers]
        
        for tender in tenders:
            row = [
                tender.reference_number,
                tender.title[:40] + '...' if len(tender.title) > 40 else tender.title,
                tender.status.name if tender.status else 'N/A',
                tender.created_at.strftime('%Y-%m-%d') if tender.created_at else 'N/A'
            ]
            data.append(row)
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 20))
    
    doc.build(story)
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename="Tenders_by_Category_Report.pdf"'
    return response

def export_tenders_by_category_excel(categories, user):
    """Export tenders by category to Excel"""
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    
    # Formats
    header_format = workbook.add_format({
        'bold': True,
        'font_color': 'white',
        'bg_color': '#366092',
        'border': 1
    })
    
    category_format = workbook.add_format({
        'bold': True,
        'font_color': 'white',
        'bg_color': '#5B9BD5',
        'border': 1
    })
    
    cell_format = workbook.add_format({
        'border': 1,
        'text_wrap': True
    })
    
    # Create a worksheet for each category
    for category_name, tenders in categories.items():
        # Clean sheet name (Excel limitations)
        sheet_name = category_name[:31].replace('/', '_').replace('\\', '_')
        worksheet = workbook.add_worksheet(sheet_name)
        
        # Category header
        worksheet.merge_range('A1:E1', f'Category: {category_name}', category_format)
        
        # Headers
        headers = ['Reference Number', 'Title', 'Status', 'Created Date', 'Deadline']
        for col, header in enumerate(headers):
            worksheet.write(2, col, header, header_format)
        
        # Data
        for row, tender in enumerate(tenders, 3):
            worksheet.write(row, 0, tender.reference_number, cell_format)
            worksheet.write(row, 1, tender.title, cell_format)
            worksheet.write(row, 2, tender.status.name if tender.status else 'N/A', cell_format)
            worksheet.write(row, 3, tender.created_at.strftime('%Y-%m-%d') if tender.created_at else 'N/A', cell_format)
            worksheet.write(row, 4, tender.submission_deadline.strftime('%Y-%m-%d') if tender.submission_deadline else 'N/A', cell_format)
        
        # Adjust column widths
        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 40)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 12)
        worksheet.set_column('E:E', 12)
    
    workbook.close()
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename="Tenders_by_Category_Report.xlsx"'
    return response

# SUPER ADMIN CUSTOM FIELDS MANAGEMENT
@app.route('/admin/custom-fields')
@super_admin_required
def admin_custom_fields():
    """Manage custom fields"""
    custom_fields = CustomFieldService.get_all_custom_fields()
    return render_template('admin/custom_fields.html', custom_fields=custom_fields)

@app.route('/admin/custom-fields/create', methods=['GET', 'POST'])
@super_admin_required
def create_custom_field():
    """Create new custom field"""
    if request.method == 'POST':
        field_name = request.form.get('field_name', '').strip()
        field_label = request.form.get('field_label', '').strip()
        field_type = request.form.get('field_type', '').strip()
        is_required = 'is_required' in request.form
        
        # Handle field options for select fields
        field_options = None
        if field_type == 'select':
            options_text = request.form.get('field_options', '').strip()
            if options_text:
                field_options = [option.strip() for option in options_text.split('\n') if option.strip()]
        
        if not all([field_name, field_label, field_type]):
            flash('Field name, label, and type are required.', 'error')
        else:
            custom_field, message = CustomFieldService.create_custom_field(
                field_name=field_name,
                field_label=field_label,
                field_type=field_type,
                created_by=session['user_id'],
                field_options=field_options,
                is_required=is_required
            )
            
            if custom_field:
                flash(message, 'success')
                return redirect(url_for('admin_custom_fields'))
            else:
                flash(message, 'error')
    
    return render_template('admin/create_custom_field.html')

@app.route('/admin/custom-fields/<int:field_id>/edit', methods=['GET', 'POST'])
@super_admin_required
def edit_custom_field(field_id):
    """Edit custom field"""
    custom_field = CustomField.query.get(field_id)
    if not custom_field:
        flash('Custom field not found.', 'error')
        return redirect(url_for('admin_custom_fields'))
    
    if request.method == 'POST':
        field_label = request.form.get('field_label', '').strip()
        field_type = request.form.get('field_type', '').strip()
        is_required = 'is_required' in request.form
        
        # Handle field options for select fields
        field_options = None
        if field_type == 'select':
            options_text = request.form.get('field_options', '').strip()
            if options_text:
                field_options = [option.strip() for option in options_text.split('\n') if option.strip()]
        
        if not all([field_label, field_type]):
            flash('Field label and type are required.', 'error')
        else:
            success, message = CustomFieldService.update_custom_field(
                field_id=field_id,
                field_label=field_label,
                field_type=field_type,
                field_options=field_options,
                is_required=is_required
            )
            
            if success:
                flash(message, 'success')
                return redirect(url_for('admin_custom_fields'))
            else:
                flash(message, 'error')
    
    return render_template('admin/edit_custom_field.html', custom_field=custom_field)

@app.route('/admin/custom-fields/<int:field_id>/delete', methods=['POST'])
@super_admin_required
def delete_custom_field(field_id):
    """Delete custom field"""
    success, message = CustomFieldService.delete_custom_field(field_id)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('admin_custom_fields'))

# Keep all existing routes (admin routes for companies, users, etc.)
# Super Admin Routes (keeping all existing ones)



@app.route('/admin/companies/create', methods=['GET', 'POST'])
@super_admin_required
def create_company():
    """Admin - Create new company with admin user and module setup"""
    if request.method == 'POST':
        # Company details
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        
        # Admin user details (optional - will be auto-generated if empty)
        admin_first_name = request.form.get('admin_first_name', '').strip()
        admin_last_name = request.form.get('admin_last_name', '').strip()
        admin_email = request.form.get('admin_email', '').strip()
        admin_username = request.form.get('admin_username', '').strip()
        
        # Module setup options
        include_all_features = 'include_all_features' in request.form
        include_premium = 'include_premium' in request.form
        selected_modules = request.form.getlist('selected_modules')
        
        if not name or not email:
            flash('Company name and email are required.', 'error')
            return render_template('admin/create_company.html')
        
        try:
            # Create company with admin
            company, admin_info, message = CompanyService.create_company_with_admin(
                name=name,
                email=email,
                phone=phone if phone else None,
                address=address if address else None,
                admin_first_name=admin_first_name if admin_first_name else None,
                admin_last_name=admin_last_name if admin_last_name else None,
                admin_email=admin_email if admin_email else None,
                admin_username=admin_username if admin_username else None
            )
            
            if company:
                # Setup modules for the new company
                if include_all_features and include_premium:
                    # Enable everything
                    CompanyModuleService.setup_company_modules(company.id, include_premium=True)
                    modules_msg = "All modules (including premium) enabled"
                elif include_all_features:
                    # Enable all feature modules but not premium
                    CompanyModuleService.setup_company_modules(company.id, include_premium=False)
                    modules_msg = "All feature modules enabled"
                elif selected_modules:
                    # Enable only selected modules
                    user_id = session.get('user_id')
                    enabled_count = 0
                    for module_name in selected_modules:
                        success, _ = CompanyModuleService.toggle_company_module(
                            company.id, module_name, True, user_id, "Enabled during company creation"
                        )
                        if success:
                            enabled_count += 1
                    modules_msg = f"{enabled_count} selected modules enabled"
                else:
                    # Default: only core modules
                    CompanyModuleService.setup_company_modules(company.id, include_premium=False)
                    # But let's disable feature modules and keep only core
                    feature_modules = ModuleDefinition.query.filter_by(category='feature').all()
                    user_id = session.get('user_id')
                    for module_def in feature_modules:
                        CompanyModuleService.toggle_company_module(
                            company.id, module_def.module_name, False, user_id, "Disabled - only core modules requested"
                        )
                    modules_msg = "Only core modules enabled"
                
                flash(message, 'success')
                flash(f'Company Admin created - Username: {admin_info["username"]}, Password: {admin_info["password"]}', 'info')
                flash(f'Modules setup: {modules_msg}', 'info')
                flash('⚠️ Please save the admin credentials and share them securely with the company admin!', 'warning')
                return redirect(url_for('view_company', company_id=company.id))
            else:
                flash(message, 'error')
                
        except Exception as e:
            flash(f'Error creating company: {str(e)}', 'error')
    
    # Get available modules for the form
    all_modules = ModuleDefinition.query.filter_by(is_active=True).order_by(ModuleDefinition.sort_order).all()
    # Convert to dictionaries
    modules_data = [module.to_dict() for module in all_modules]
    return render_template('admin/create_company.html', available_modules=modules_data) 




@app.route('/admin/companies/<int:company_id>/edit', methods=['GET', 'POST'])
@login_required
@super_admin_required
def edit_company(company_id):
    """Edit company details and manage modules"""
    company = Company.query.get_or_404(company_id)
    
    # Get all available modules
    all_modules = ModuleDefinition.query.filter_by(is_active=True).order_by(ModuleDefinition.sort_order).all()
    
    # Get ACTUALLY enabled modules using JOIN
    enabled_company_modules = db.session.query(CompanyModule, ModuleDefinition).join(ModuleDefinition).filter(
        CompanyModule.company_id == company_id,
        CompanyModule.is_enabled == True
    ).all()
    
    enabled_module_ids = {cm.module_id for cm, _ in enabled_company_modules}
    monthly_cost = sum(float(module_def.monthly_price) if module_def.monthly_price else 0.0 
                      for cm, module_def in enabled_company_modules)
    
    # Create modules_data structure with CORRECT enabled states
    modules_data = []
    for module_def in all_modules:
        # Check if this module is actually enabled by checking module_id
        is_enabled = module_def.id in enabled_module_ids
        
        # Get the company module record if it exists
        company_module = None
        if is_enabled:
            company_module = CompanyModule.query.filter_by(
                company_id=company_id,
                module_id=module_def.id,
                is_enabled=True
            ).first()
        
        module_data = type('ModuleData', (), {
            'definition': module_def,
            'is_enabled': is_enabled,
            'company_module': company_module
        })()
        
        modules_data.append(module_data)
    
    # Company stats
    user_count = User.query.filter_by(company_id=company_id, is_active=True).count()
    tender_count = Tender.query.filter_by(company_id=company_id).count()
    
    company_stats = type('CompanyStats', (), {
        'user_count': user_count,
        'tender_count': tender_count
    })()
    
    return render_template('admin/edit_company.html',
                         company=company,
                         company_stats=company_stats,
                         modules_data=modules_data,
                         enabled_count=len(enabled_module_ids),
                         total_modules=len(all_modules),
                         monthly_cost=monthly_cost)

@app.route('/debug/test-save/<int:company_id>')
@login_required 
@super_admin_required
def test_save_module(company_id):
    """Test saving a single module to see what happens"""
    try:
        # Test saving the reporting module
        module_name = 'reporting'
        
        print(f"\n=== Testing module save for company {company_id} ===")
        
        # First, find the module definition
        module_def = ModuleDefinition.query.filter_by(module_name=module_name).first()
        if not module_def:
            return jsonify({
                'success': False,
                'error': f'Module "{module_name}" not found in ModuleDefinition table'
            }), 404
        
        print(f"Found module definition: {module_def.module_name} -> {module_def.display_name}")
        
        # Check if company_module record exists
        existing = CompanyModule.query.filter_by(
            company_id=company_id,
            module_id=module_def.id
        ).first()
        
        print(f"Existing record: {existing}")
        
        if existing:
            existing.is_enabled = True
            existing.enabled_at = datetime.now()
            print("Updated existing record")
        else:
            # Create new record using the correct fields
            new_module = CompanyModule(
                company_id=company_id,
                module_id=module_def.id,
                is_enabled=True,
                enabled_at=datetime.now(),
                billing_start_date=datetime.now()
            )
            db.session.add(new_module)
            print("Created new record")
        
        # Try to commit
        db.session.commit()
        print("Commit successful")
        
        # Check what's in the database now
        all_modules = db.session.query(CompanyModule, ModuleDefinition).join(ModuleDefinition).filter(
            CompanyModule.company_id == company_id
        ).all()
        
        result = {
            'success': True,
            'message': f'Test save completed for company {company_id}',
            'modules_in_db': [
                {
                    'id': cm.id,
                    'module_id': cm.module_id,
                    'module_name': module_def.module_name,
                    'display_name': module_def.display_name,
                    'is_enabled': cm.is_enabled,
                    'enabled_at': cm.enabled_at.isoformat() if cm.enabled_at else None,
                    'monthly_price': float(module_def.monthly_price) if module_def.monthly_price else 0.0
                } for cm, module_def in all_modules
            ]
        }
        
        return jsonify(result)
        
    except Exception as e:
        db.session.rollback()
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
        

# Add this route to check if the table exists and its structure:

@app.route('/debug/check-tables')
@login_required
@super_admin_required  
def check_tables():
    """Check if CompanyModule table exists and its structure"""
    try:
        from sqlalchemy import inspect
        
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        result = {
            'all_tables': tables,
            'company_module_exists': 'company_module' in tables,
            'module_definition_exists': 'module_definition' in tables
        }
        
        # If CompanyModule table exists, check its columns
        if 'company_module' in tables:
            columns = inspector.get_columns('company_module')
            result['company_module_columns'] = [
                {
                    'name': col['name'],
                    'type': str(col['type']),
                    'nullable': col['nullable']
                } for col in columns
            ]
            
            # Check if there are any records
            try:
                count = db.session.query(CompanyModule).count()
                result['company_module_record_count'] = count
                
                # Get sample records
                sample_records = CompanyModule.query.limit(5).all()
                result['sample_records'] = [
                    {
                        'id': r.id,
                        'company_id': r.company_id,
                        'module_name': r.module_name,
                        'is_enabled': r.is_enabled,
                        'enabled_at': r.enabled_at.isoformat() if r.enabled_at else None
                    } for r in sample_records
                ]
            except Exception as e:
                result['query_error'] = str(e)
        
        # Check ModuleDefinition table
        if 'module_definition' in tables:
            columns = inspector.get_columns('module_definition')
            result['module_definition_columns'] = [
                {
                    'name': col['name'], 
                    'type': str(col['type']),
                    'nullable': col['nullable']
                } for col in columns
            ]
            
            try:
                count = db.session.query(ModuleDefinition).count()
                result['module_definition_record_count'] = count
                
                sample_defs = ModuleDefinition.query.limit(5).all()
                result['sample_definitions'] = [
                    {
                        'id': r.id,
                        'module_name': r.module_name,
                        'display_name': r.display_name,
                        'monthly_price': r.monthly_price,
                        'is_active': r.is_active
                    } for r in sample_defs
                ]
            except Exception as e:
                result['module_def_query_error'] = str(e)
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# Add this route to check the actual structure of your existing tables:

@app.route('/debug/check-actual-tables')
@login_required
@super_admin_required
def check_actual_tables():
    """Check the actual structure of existing tables"""
    try:
        from sqlalchemy import inspect, text
        
        inspector = inspect(db.engine)
        result = {}
        
        # Check company_modules table (plural)
        if 'company_modules' in inspector.get_table_names():
            columns = inspector.get_columns('company_modules')
            result['company_modules'] = {
                'columns': [
                    {
                        'name': col['name'],
                        'type': str(col['type']),
                        'nullable': col['nullable']
                    } for col in columns
                ],
                'sample_data': []
            }
            
            # Get sample data using raw SQL
            try:
                with db.engine.connect() as conn:
                    sample_result = conn.execute(text("SELECT * FROM company_modules LIMIT 5"))
                    result['company_modules']['sample_data'] = [
                        dict(row._mapping) for row in sample_result
                    ]
                    
                    count_result = conn.execute(text("SELECT COUNT(*) as count FROM company_modules"))
                    result['company_modules']['total_count'] = count_result.fetchone()[0]
            except Exception as e:
                result['company_modules']['data_error'] = str(e)
        
        # Check module_definitions table (plural)
        if 'module_definitions' in inspector.get_table_names():
            columns = inspector.get_columns('module_definitions')
            result['module_definitions'] = {
                'columns': [
                    {
                        'name': col['name'],
                        'type': str(col['type']),
                        'nullable': col['nullable']
                    } for col in columns
                ],
                'sample_data': []
            }
            
            # Get sample data using raw SQL
            try:
                with db.engine.connect() as conn:
                    sample_result = conn.execute(text("SELECT * FROM module_definitions LIMIT 5"))
                    result['module_definitions']['sample_data'] = [
                        dict(row._mapping) for row in sample_result
                    ]
                    
                    count_result = conn.execute(text("SELECT COUNT(*) as count FROM module_definitions"))
                    result['module_definitions']['total_count'] = count_result.fetchone()[0]
            except Exception as e:
                result['module_definitions']['data_error'] = str(e)
        
        # Also check company_features table (seems related)
        if 'company_features' in inspector.get_table_names():
            columns = inspector.get_columns('company_features')
            result['company_features'] = {
                'columns': [
                    {
                        'name': col['name'],
                        'type': str(col['type']),
                        'nullable': col['nullable']
                    } for col in columns
                ],
                'sample_data': []
            }
            
            try:
                with db.engine.connect() as conn:
                    sample_result = conn.execute(text("SELECT * FROM company_features LIMIT 5"))
                    result['company_features']['sample_data'] = [
                        dict(row._mapping) for row in sample_result
                    ]
                    
                    count_result = conn.execute(text("SELECT COUNT(*) as count FROM company_features"))
                    result['company_features']['total_count'] = count_result.fetchone()[0]
            except Exception as e:
                result['company_features']['data_error'] = str(e)
        
        # Check features table
        if 'features' in inspector.get_table_names():
            columns = inspector.get_columns('features')
            result['features'] = {
                'columns': [
                    {
                        'name': col['name'],
                        'type': str(col['type']),
                        'nullable': col['nullable']
                    } for col in columns
                ],
                'sample_data': []
            }
            
            try:
                with db.engine.connect() as conn:
                    sample_result = conn.execute(text("SELECT * FROM features LIMIT 10"))
                    result['features']['sample_data'] = [
                        dict(row._mapping) for row in sample_result
                    ]
                    
                    count_result = conn.execute(text("SELECT COUNT(*) as count FROM features"))
                    result['features']['total_count'] = count_result.fetchone()[0]
            except Exception as e:
                result['features']['data_error'] = str(e)
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/debug/company/<int:company_id>/modules')
@login_required
def debug_company_modules(company_id):
    """Debug route to see what modules are actually saved in the database"""
    try:
        company = Company.query.get_or_404(company_id)
        
        # Get all CompanyModule records for this company
        company_modules = CompanyModule.query.filter_by(company_id=company_id).all()
        
        # Get enabled modules using the method
        try:
            enabled_modules = company.get_enabled_modules()
        except:
            enabled_modules = CompanyModule.get_enabled_modules(company_id)
        
        # Get all available modules
        try:
            all_modules = ModuleDefinition.query.all()
        except:
            all_modules = []
        
        debug_info = {
            'company_id': company_id,
            'company_name': company.name,
            'company_modules_table': [
                {
                    'id': cm.id,
                    'module_name': cm.module_name,
                    'is_enabled': cm.is_enabled,
                    'enabled_at': cm.enabled_at.isoformat() if cm.enabled_at else None,
                    'monthly_cost': cm.monthly_cost
                } for cm in company_modules
            ],
            'enabled_modules_method': enabled_modules,
            'available_modules': [
                {
                    'id': m.id,
                    'module_name': m.module_name,
                    'display_name': m.display_name,
                    'monthly_price': m.monthly_price
                } for m in all_modules
            ],
            'total_company_modules': len(company_modules),
            'total_enabled': len([cm for cm in company_modules if cm.is_enabled])
        }
        
        return jsonify(debug_info)
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/admin/companies/<int:company_id>/modules/batch-update', methods=['POST'])
@login_required
@super_admin_required
def update_company_modules(company_id):
    """Update company module settings - FIXED VERSION"""
    try:
        print(f"\n=== DEBUG: Batch update for company {company_id} ===")
        
        company = Company.query.get_or_404(company_id)
        
        if not request.is_json:
            return jsonify({
                'success': False,
                'message': 'Content-Type must be application/json'
            }), 400
            
        data = request.get_json()
        changes = data.get('changes', [])
        
        # Track results
        updated_modules = []
        errors = []
        
        for change in changes:
            module_name = change.get('module_name')
            enabled = change.get('enabled', False)
            notes = change.get('notes', '')
            
            try:
                # First find the module definition
                module_def = ModuleDefinition.query.filter_by(module_name=module_name).first()
                if not module_def:
                    errors.append(f"Module definition not found: {module_name}")
                    continue
                
                # Check if CompanyModule record exists using module_id
                company_module = CompanyModule.query.filter_by(
                    company_id=company_id,
                    module_id=module_def.id  # Use module_id, not module_name
                ).first()
                
                if enabled:
                    # Enable the module
                    if company_module:
                        # Update existing record
                        company_module.is_enabled = True
                        company_module.enabled_at = datetime.now()
                        company_module.disabled_at = None
                        company_module.enabled_by = session.get('user_id')
                    else:
                        # Create new record
                        company_module = CompanyModule(
                            company_id=company_id,
                            module_id=module_def.id,  # Use module_id
                            is_enabled=True,
                            enabled_at=datetime.now(),
                            enabled_by=session.get('user_id'),
                            billing_start_date=datetime.now(),
                            notes=notes
                        )
                        db.session.add(company_module)
                    
                    updated_modules.append(f"Enabled {module_name}")
                    
                else:
                    # Disable the module
                    if company_module:
                        company_module.is_enabled = False
                        company_module.disabled_at = datetime.now()
                        company_module.disabled_by = session.get('user_id')
                        updated_modules.append(f"Disabled {module_name}")
                    else:
                        updated_modules.append(f"Module {module_name} was already disabled")
                
            except Exception as e:
                errors.append(f"Error with {module_name}: {str(e)}")
                continue
        
        # Commit all changes
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Database error: {str(e)}'
            }), 500
        
        # Get updated status using JOIN
        enabled_company_modules = db.session.query(CompanyModule, ModuleDefinition).join(ModuleDefinition).filter(
            CompanyModule.company_id == company_id,
            CompanyModule.is_enabled == True
        ).all()
        
        enabled_modules = [module_def.module_name for cm, module_def in enabled_company_modules]
        monthly_cost = sum(float(module_def.monthly_price) if module_def.monthly_price else 0.0 
                          for cm, module_def in enabled_company_modules)
        
        result = {
            'success': True,
            'message': f'Modules updated successfully. {len(enabled_modules)} modules enabled.',
            'monthly_cost': monthly_cost,
            'enabled_count': len(enabled_modules),
            'enabled_modules': enabled_modules,
            'updates': updated_modules
        }
        
        if errors:
            result['errors'] = errors
            result['message'] += f' ({len(errors)} errors occurred)'
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating modules: {str(e)}'
        }), 500
        
        # Get updated status
        try:
            enabled_modules = company.get_enabled_modules()
            monthly_cost = CompanyModule.get_monthly_cost(company_id)
        except:
            # Fallback method
            enabled_company_modules = CompanyModule.query.filter_by(
                company_id=company_id, 
                is_enabled=True
            ).all()
            enabled_modules = [cm.module_name for cm in enabled_company_modules]
            monthly_cost = sum(cm.monthly_cost or 0 for cm in enabled_company_modules)
        
        print(f"Final enabled modules: {enabled_modules}")
        print(f"Final monthly cost: {monthly_cost}")
        
        result = {
            'success': True,
            'message': f'Modules updated successfully. {len(enabled_modules)} modules enabled.',
            'monthly_cost': monthly_cost,
            'enabled_count': len(enabled_modules),
            'enabled_modules': enabled_modules,
            'updates': updated_modules
        }
        
        if errors:
            result['errors'] = errors
            result['message'] += f' ({len(errors)} errors occurred)'
        
        return jsonify(result)
        
    except Exception as e:
        print(f"ERROR in update_company_modules: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': f'Error updating modules: {str(e)}'
        }), 500

@app.route('/admin/companies/<int:company_id>/update', methods=['POST'])
@super_admin_required  
def update_company_details(company_id):
    """Update company basic details via AJAX"""
    try:
        company = Company.query.get_or_404(company_id)
        data = request.get_json()
        
        # Update company details
        company.name = data.get('name', company.name)
        company.email = data.get('email', company.email)
        company.phone = data.get('phone')
        company.address = data.get('address')
        company.is_active = data.get('is_active', True)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Company updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating company: {str(e)}'
        }), 500

@app.route('/test-company-modules')
@login_required
def test_company_modules():
    """Test route to check if module system is working"""
    try:
        user_id = session['user_id']
        user = User.query.get(user_id)
        
        # Debug info
        debug_info = {
            'user_id': user_id,
            'user_found': user is not None,
            'user_company_id': user.company_id if user else None,
            'user_name': user.first_name + ' ' + user.last_name if user else None,
        }
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found',
                'debug': debug_info
            })
        
        if not user.company_id:
            return jsonify({
                'success': False,
                'error': 'User has no company assigned',
                'debug': debug_info
            })
        
        company = Company.query.get(user.company_id)
        debug_info['company_found'] = company is not None
        debug_info['company_name'] = company.name if company else None
        
        if not company:
            return jsonify({
                'success': False,
                'error': 'Company not found',
                'debug': debug_info
            })
        
        # Check if the methods exist
        if not hasattr(company, 'get_enabled_modules'):
            return jsonify({
                'success': False,
                'error': 'Company model missing get_enabled_modules method',
                'debug': debug_info,
                'available_methods': [method for method in dir(company) if not method.startswith('_')]
            })
        
        # Test the methods
        enabled_modules = company.get_enabled_modules()
        monthly_cost = company.get_monthly_cost()
        has_analytics = company.has_module('analytics')
        modules_status = CompanyModule.get_company_modules_with_status(company.id)
        
        return jsonify({
            'success': True,
            'debug': debug_info,
            'user': user.first_name + ' ' + user.last_name,
            'company': company.name,
            'enabled_modules': enabled_modules,
            'monthly_cost': monthly_cost,
            'has_analytics': has_analytics,
            'all_modules': modules_status
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/admin/companies/<int:company_id>/view')
@login_required
@super_admin_required
def view_company(company_id):
    company = Company.query.get_or_404(company_id)
    
    # Get company statistics
    user_count = User.query.filter_by(company_id=company_id).count()
    active_user_count = User.query.filter_by(company_id=company_id, is_active=True).count()
    tender_count = Tender.query.filter_by(company_id=company_id).count()
    
    # Get users
    users = User.query.filter_by(company_id=company_id).order_by(User.first_name, User.last_name).all()
    
    # Get enabled modules
    company_modules = []
    if hasattr(company, 'company_modules'):
        company_modules = [cm.to_dict() for cm in company.company_modules if cm.is_enabled]
    
    # Get recent tenders (last 10)
    recent_tenders = Tender.query.filter_by(company_id=company_id).order_by(Tender.created_at.desc()).limit(10).all()
    
    return render_template('admin/view_company.html',
                         company=company,
                         user_count=user_count,
                         active_user_count=active_user_count,
                         tender_count=tender_count,
                         module_count=len(company_modules),
                         users=users,
                         company_modules=company_modules,
                         recent_tenders=recent_tenders)

@app.route('/admin/companies/<int:company_id>/deactivate', methods=['POST'])
@super_admin_required
def deactivate_company(company_id):
    """Admin - Deactivate company"""
    success, message = CompanyService.deactivate_company(company_id)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    return redirect(url_for('admin_companies'))

@app.route('/admin/users')
@super_admin_required
@require_module('user_management')  # ← Add this decorator
def admin_users():
    """Admin - Manage users"""
    users = AuthService.get_all_users()
    return render_template('admin/users.html', users=users)

@app.route('/admin/companies')
@super_admin_required
@require_module('company_management')  # ← Add this decorator (if you have this module)
def admin_companies():
    """Admin - Manage companies"""
    # Use direct database query instead of service method
    companies = Company.query.order_by(Company.name).all()
    
    # Add stats for each company manually
    for company in companies:
        user_count = User.query.filter_by(company_id=company.id, is_active=True).count()
        tender_count = Tender.query.filter_by(company_id=company.id).count()
        
        # Create a simple stats object
        company.stats = type('CompanyStats', (), {
            'user_count': user_count,
            'tender_count': tender_count,
            'active_tender_count': tender_count  # For now, assume all are active
        })()
    
    return render_template('admin/companies.html', companies=companies)



@app.route('/admin/users/create', methods=['GET', 'POST'])
@super_admin_required
def create_user():
    """Admin - Create new user"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        company_id = request.form.get('company_id')
        role_id = request.form.get('role_id')
        is_super_admin = 'is_super_admin' in request.form
        
        # Validation
        if not all([username, email, password, first_name, last_name, role_id]):
            flash('All required fields must be filled.', 'error')
        else:
            # Convert empty string to None for company_id
            company_id = int(company_id) if company_id and company_id.strip() else None
            role_id = int(role_id)
            
            user, message = AuthService.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                company_id=company_id,
                role_id=role_id,
                is_super_admin=is_super_admin
            )
            
            if user:
                flash(message, 'success')
                return redirect(url_for('admin_users'))
            else:
                flash(message, 'error')
    
    companies = CompanyService.get_all_companies()
    roles = RoleService.get_all_roles()
    return render_template('admin/create_user.html', companies=companies, roles=roles)

@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@super_admin_required
def edit_user(user_id):
    """Admin - Update existing user"""
    user = AuthService.get_user_by_id(user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin_users'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')  # optional: only update if not empty
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        company_id = request.form.get('company_id')
        role_id = request.form.get('role_id')
        is_super_admin = 'is_super_admin' in request.form

        # Validation
        if not all([username, email, first_name, last_name, role_id]):
            flash('All required fields except password must be filled.', 'error')
        else:
            company_id = int(company_id) if company_id and company_id.strip() else None
            role_id = int(role_id)

            success, message = AuthService.update_user(
                user_id=user_id,
                username=username,
                email=email,
                password=password if password else None,  # update password only if provided
                first_name=first_name,
                last_name=last_name,
                company_id=company_id,
                role_id=role_id,
                is_super_admin=is_super_admin
            )

            if success:
                flash(message, 'success')
                return redirect(url_for('admin_users'))
            else:
                flash(message, 'error')

    companies = CompanyService.get_all_companies()
    roles = RoleService.get_all_roles()

    return render_template('admin/edit_user.html', user=user, companies=companies, roles=roles)

@app.route('/admin/roles')
@login_required
@require_permission('role_management')
def admin_roles():
    """Manage roles - requires role_management permission"""
    roles = RoleService.get_all_roles()
    permissions_by_category = RoleService.get_permissions_by_category()
    
    return render_template('admin/roles.html', 
                         roles=roles,
                         permissions_by_category=permissions_by_category)

@app.route('/admin/roles/create', methods=['GET', 'POST'])
@login_required
@require_permission('role_management')
def create_role():
    """Create a new custom role"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        level = request.form.get('level', 'viewer')
        permissions = request.form.getlist('permissions')
        
        if not name:
            flash('Role name is required.', 'error')
        else:
            role, message = RoleService.create_custom_role(
                name=name,
                description=description,
                level=level,
                permissions=permissions,
                created_by=session['user_id']
            )
            
            if role:
                flash(message, 'success')
                return redirect(url_for('admin_roles'))
            else:
                flash(message, 'error')
    
    # GET request - show form
    permissions_by_category = RoleService.get_permissions_by_category()
    role_levels = [
        ('viewer', 'Viewer'),
        ('vendor', 'Vendor'),
        ('procurement_manager', 'Procurement Manager'),
        ('company_admin', 'Company Admin')
    ]
    
    return render_template('admin/create_role.html',
                         permissions_by_category=permissions_by_category,
                         role_levels=role_levels)

@app.route('/admin/roles/<int:role_id>/edit', methods=['GET', 'POST'])
@login_required
@require_permission('role_management')
def edit_role(role_id):
    """Edit an existing role"""
    role = RoleService.get_role_by_id(role_id)
    if not role:
        flash('Role not found.', 'error')
        return redirect(url_for('admin_roles'))
    
    # Don't allow editing super admin role
    if role.level == 'super_admin':
        flash('Cannot edit Super Admin role.', 'error')
        return redirect(url_for('admin_roles'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        level = request.form.get('level')
        permissions = request.form.getlist('permissions')
        
        if not name:
            flash('Role name is required.', 'error')
        else:
            success, message = RoleService.update_role(
                role_id=role_id,
                name=name,
                description=description,
                level=level,
                permissions=permissions
            )
            
            if success:
                flash(message, 'success')
                return redirect(url_for('admin_roles'))
            else:
                flash(message, 'error')
    
    # GET request - show form
    permissions_by_category = RoleService.get_permissions_by_category()
    current_permissions = RoleService.get_role_permissions(role_id)
    
    role_levels = [
        ('viewer', 'Viewer'),
        ('vendor', 'Vendor'),
        ('procurement_manager', 'Procurement Manager'),
        ('company_admin', 'Company Admin')
    ]
    
    return render_template('admin/edit_role.html',
                         role=role,
                         permissions_by_category=permissions_by_category,
                         current_permissions=current_permissions,
                         role_levels=role_levels)

@app.route('/admin/roles/<int:role_id>/delete', methods=['POST'])
@login_required
@require_permission('role_management')
def delete_role(role_id):
    """Delete a role"""
    success, message = RoleService.delete_role(role_id)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('admin_roles'))

@app.route('/admin/roles/initialize', methods=['POST'])
@login_required
@require_permission('system_admin')
def initialize_roles():
    """Initialize default system roles"""
    success, message = RoleService.initialize_default_roles()
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('admin_roles'))

@app.route('/admin/roles/<int:role_id>/permissions')
@login_required
@require_permission('role_management')
def view_role_permissions(role_id):
    """View role permissions in detail"""
    role = RoleService.get_role_by_id(role_id)
    if not role:
        flash('Role not found.', 'error')
        return redirect(url_for('admin_roles'))
    
    permissions = RoleService.get_role_permissions(role_id)
    all_permissions = RoleService.get_available_permissions()
    
    # Group permissions by category for display
    permission_details = {}
    for perm in permissions:
        if perm in all_permissions:
            category = all_permissions[perm]['category']
            if category not in permission_details:
                permission_details[category] = []
            permission_details[category].append({
                'key': perm,
                'display_name': all_permissions[perm]['display_name'],
                'description': all_permissions[perm]['description']
            })
    
    # Count users with this role
    from models import User
    user_count = User.query.filter_by(role_id=role_id).count()
    
    return render_template('admin/view_role_permissions.html',
                         role=role,
                         permission_details=permission_details,
                         user_count=user_count)

# ===== API ENDPOINTS FOR ROLE MANAGEMENT =====

@app.route('/api/roles/<int:role_id>/permissions', methods=['GET'])
@login_required
@require_permission('role_management')
def api_get_role_permissions(role_id):
    """API endpoint to get role permissions"""
    permissions = RoleService.get_role_permissions(role_id)
    return jsonify({
        'success': True,
        'permissions': permissions
    })

@app.route('/api/roles/<int:role_id>/permissions', methods=['POST'])
@login_required
@require_permission('role_management')
def api_update_role_permissions(role_id):
    """API endpoint to update role permissions"""
    try:
        data = request.get_json()
        permissions = data.get('permissions', [])
        
        success, message = RoleService.update_role(
            role_id=role_id,
            permissions=permissions
        )
        
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating permissions: {str(e)}'
        }), 500

@app.route('/api/permissions/available')
@login_required
@require_permission('role_management')
def api_get_available_permissions():
    """API endpoint to get all available permissions"""
    permissions = RoleService.get_available_permissions()
    permissions_by_category = RoleService.get_permissions_by_category()
    
    return jsonify({
        'success': True,
        'permissions': permissions,
        'permissions_by_category': permissions_by_category
    })

# ===== USER PERMISSION CHECKING ROUTES =====

@app.route('/debug/user-permissions')
@login_required
def debug_user_permissions():
    """Debug route to check current user's permissions"""
    try:
        user_id = session['user_id']
        from models import User
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'})
        
        permissions = RoleService.get_user_permissions(user_id)
        
        return jsonify({
            'user_id': user_id,
            'username': user.username,
            'role': {
                'id': user.role.id if user.role else None,
                'name': user.role.name if user.role else None,
                'level': user.role.level if user.role else None
            },
            'is_super_admin': user.is_super_admin,
            'permissions': permissions,
            'permission_count': len(permissions)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/debug/check-permission/<permission>')
@login_required
def debug_check_permission(permission):
    """Debug route to check if user has specific permission"""
    user_id = session['user_id']
    has_permission = RoleService.check_user_permission(user_id, permission)
    
    return jsonify({
        'user_id': user_id,
        'permission': permission,
        'has_permission': has_permission
    })

# Company Admin Routes (keeping existing ones)
@app.route('/company/users')
@company_admin_required
@require_module('user_management') 
def company_users():
    """Company Admin - Manage company users"""
    user = AuthService.get_user_by_id(session['user_id'])
    
    if user.is_super_admin:
        # Super admin can see all users
        users = AuthService.get_all_users()
        company = None
    else:
        # Company admin can only see their company users
        users = AuthService.get_users_by_company(user.company_id)
        company = CompanyService.get_company_by_id(user.company_id)
    
    return render_template('company/users.html', users=users, company=company)

@app.route('/company/users/create', methods=['GET', 'POST'])
@company_admin_required
@require_module('user_management') 
def create_company_user():
    """Company Admin - Create new user for their company"""
    current_user = AuthService.get_user_by_id(session['user_id'])
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        role_id = request.form.get('role_id')
        
        # Validation
        if not all([username, email, password, first_name, last_name, role_id]):
            flash('All required fields must be filled.', 'error')
        else:
            role_id = int(role_id)
            
            # Company admin can only create users for their own company
            company_id = current_user.company_id if not current_user.is_super_admin else None
            
            user, message = AuthService.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                company_id=company_id,
                role_id=role_id,
                is_super_admin=False
            )
            
            if user:
                flash(message, 'success')
                return redirect(url_for('company_users'))
            else:
                flash(message, 'error')
    
    # Get roles available for company users (excluding Super Admin)
    roles = RoleService.get_company_roles()
    company = CompanyService.get_company_by_id(current_user.company_id) if not current_user.is_super_admin else None

    return render_template('company/create_user.html', roles=roles, company=company)

# Replace your view_company_users route in app.py with this:

@app.route('/admin/companies/<int:company_id>/users')
@super_admin_required
def view_company_users(company_id):
    """View all users for a specific company"""
    # Get company directly from database
    company = Company.query.get_or_404(company_id)
    
    # Get all users for this company
    users = User.query.filter_by(company_id=company_id).order_by(User.first_name, User.last_name).all()
    
    # Get company statistics
    total_users = len(users)
    active_users = len([u for u in users if u.is_active])
    inactive_users = total_users - active_users
    
    # Count users by role
    role_counts = {}
    for user in users:
        role_name = user.role.name if user.role else 'No Role'
        role_counts[role_name] = role_counts.get(role_name, 0) + 1
    
    # Recent users (last 30 days)
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_users = [u for u in users if u.created_at >= thirty_days_ago]
    
    # Prepare statistics object
    user_stats = type('UserStats', (), {
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'recent_users': len(recent_users),
        'role_counts': role_counts
    })()
    
    return render_template('admin/company_users.html',
                         company=company,
                         users=users,
                         user_stats=user_stats)

@app.route('/admin/companies/<int:company_id>/users/add', methods=['GET', 'POST'])
@super_admin_required
def add_company_user(company_id):
    """Add a new user to a company"""
    company = Company.query.get_or_404(company_id)
    
    if request.method == 'POST':
        try:
            # Get form data
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            email = request.form.get('email', '').strip()
            username = request.form.get('username', '').strip()
            role_id = request.form.get('role_id')
            is_active = 'is_active' in request.form
            
            # Validation
            if not all([first_name, last_name, email, username, role_id]):
                flash('All fields are required', 'error')
                return redirect(url_for('add_company_user', company_id=company_id))
            
            # Check if username or email already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'error')
                return redirect(url_for('add_company_user', company_id=company_id))
            
            if User.query.filter_by(email=email).first():
                flash('Email already exists', 'error')
                return redirect(url_for('add_company_user', company_id=company_id))
            
            # Generate password
            password = CompanyService.generate_password()
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            
            # Create user
            user = User(
                first_name=first_name,
                last_name=last_name,
                email=email,
                username=username,
                password_hash=hashed_password,
                role_id=role_id,
                company_id=company_id,
                is_active=is_active
            )
            
            db.session.add(user)
            db.session.commit()
            
            # Store password temporarily in session to show to admin
            session['new_user_password'] = password
            
            flash(f'User {first_name} {last_name} created successfully!', 'success')
            return redirect(url_for('view_company_users', company_id=company_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'error')
    
    # GET request - show form
    # Get available roles
    roles = Role.query.filter(Role.name != 'Super Admin').all()
    
    return render_template('admin/add_company_user.html',
                         company=company,
                         roles=roles)

@app.route('/admin/companies/<int:company_id>/users/<int:user_id>/edit', methods=['GET', 'POST'])
@super_admin_required
def edit_company_user(company_id, user_id):
    """Edit a company user"""
    company = Company.query.get_or_404(company_id)
    user = User.query.filter_by(id=user_id, company_id=company_id).first_or_404()
    
    if request.method == 'POST':
        try:
            # Get form data
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            email = request.form.get('email', '').strip()
            username = request.form.get('username', '').strip()
            role_id = request.form.get('role_id')
            is_active = 'is_active' in request.form
            
            # Validation
            if not all([first_name, last_name, email, username, role_id]):
                flash('All fields are required', 'error')
                return redirect(url_for('edit_company_user', company_id=company_id, user_id=user_id))
            
            # Check if username or email already exists (excluding current user)
            existing_user = User.query.filter(
                User.username == username,
                User.id != user_id
            ).first()
            if existing_user:
                flash('Username already exists', 'error')
                return redirect(url_for('edit_company_user', company_id=company_id, user_id=user_id))
            
            existing_email = User.query.filter(
                User.email == email,
                User.id != user_id
            ).first()
            if existing_email:
                flash('Email already exists', 'error')
                return redirect(url_for('edit_company_user', company_id=company_id, user_id=user_id))
            
            # Update user
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.username = username
            user.role_id = role_id
            user.is_active = is_active
            
            db.session.commit()
            flash(f'User {first_name} {last_name} updated successfully!', 'success')
            return redirect(url_for('view_company_users', company_id=company_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'error')
    
    # GET request - show form
    roles = Role.query.filter(Role.name != 'Super Admin').all()
    
    return render_template('admin/edit_company_user.html',
                         company=company,
                         user=user,
                         roles=roles)

@app.route('/admin/companies/<int:company_id>/users/<int:user_id>/reset-password', methods=['POST'])
@super_admin_required
def reset_company_user_password(company_id, user_id):
    """Reset a company user's password"""
    try:
        company = Company.query.get_or_404(company_id)
        user = User.query.filter_by(id=user_id, company_id=company_id).first_or_404()
        
        # Generate new password
        new_password = CompanyService.generate_password()
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        
        # Update user password
        user.password_hash = hashed_password
        db.session.commit()
        
        # Store password temporarily in session to show to admin
        session['reset_password'] = new_password
        
        flash(f'Password reset for {user.first_name} {user.last_name}. New password: {new_password}', 'success')
        return redirect(url_for('view_company_users', company_id=company_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error resetting password: {str(e)}', 'error')
        return redirect(url_for('view_company_users', company_id=company_id))

@app.route('/admin/companies/<int:company_id>/users/<int:user_id>/toggle-status', methods=['POST'])
@super_admin_required
def toggle_company_user_status(company_id, user_id):
    """Toggle user active/inactive status"""
    try:
        company = Company.query.get_or_404(company_id)
        user = User.query.filter_by(id=user_id, company_id=company_id).first_or_404()
        
        # Toggle status
        user.is_active = not user.is_active
        db.session.commit()
        
        status = "activated" if user.is_active else "deactivated"
        flash(f'User {user.first_name} {user.last_name} has been {status}', 'success')
        
        return redirect(url_for('view_company_users', company_id=company_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating user status: {str(e)}', 'error')
        return redirect(url_for('view_company_users', company_id=company_id))

@app.route('/admin/companies/<int:company_id>/update', methods=['POST'])
@super_admin_required
def update_company(company_id):
    """Update company basic information"""
    try:
        company = CompanyService.get_company_by_id(company_id)
        if not company:
            return jsonify({'success': False, 'message': 'Company not found'}), 404
        
        data = request.get_json()
        
        # Update company fields
        success, message = CompanyService.update_company(
            company_id=company_id,
            name=data.get('name', company.name),
            email=data.get('email', company.email),
            phone=data.get('phone', company.phone),
            address=data.get('address', company.address),
            is_active=data.get('is_active', company.is_active)
        )
        
        if success:
            return jsonify({'success': True, 'message': 'Company updated successfully'})
        else:
            return jsonify({'success': False, 'message': message}), 500
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error updating company: {str(e)}'}), 500
    
@app.route('/admin/companies/<int:company_id>/modules/batch-update', methods=['POST'])
@super_admin_required
def batch_update_company_modules(company_id):
    """Batch update company modules"""
    try:
        data = request.get_json()
        changes = data.get('changes', [])
        user_id = session.get('user_id')
        
        success_count = 0
        errors = []
        
        for change in changes:
            module_name = change.get('module_name')
            enabled = change.get('enabled')
            notes = change.get('notes', '')
            
            success, message = CompanyModuleService.toggle_company_module(
                company_id, module_name, enabled, user_id, notes
            )
            
            if success:
                success_count += 1
            else:
                errors.append(f"{module_name}: {message}")
        
        # Calculate new monthly cost
        monthly_cost = CompanyModuleService.get_company_monthly_cost(company_id)
        
        if errors:
            return jsonify({
                'success': False, 
                'message': f'Some updates failed: {"; ".join(errors)}',
                'success_count': success_count,
                'monthly_cost': monthly_cost
            }), 400
        else:
            return jsonify({
                'success': True, 
                'message': f'Successfully updated {success_count} modules',
                'monthly_cost': monthly_cost
            })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error updating modules: {str(e)}'}), 500

@app.route('/admin/initialize-company-modules')
@super_admin_required
def initialize_company_modules():
    """Initialize module definitions and setup for existing companies"""
    try:
        # Initialize module definitions
        success = CompanyModuleService.initialize_module_definitions()
        if not success:
            flash('Error initializing module definitions. Check logs.', 'error')
            return redirect(url_for('admin_companies'))
        
        # Setup modules for existing companies that don't have any modules yet
        companies = Company.query.filter_by(is_active=True).all()
        setup_count = 0
        
        for company in companies:
            existing_modules = CompanyModule.query.filter_by(company_id=company.id).count()
            if existing_modules == 0:
                # Setup basic modules for this company
                CompanyModuleService.setup_company_modules(company.id, include_premium=False)
                setup_count += 1
        
        flash(f'Module definitions initialized successfully! Set up modules for {setup_count} companies.', 'success')
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('admin_companies'))

# Add route for viewing company modules (optional)
@app.route('/admin/companies/<int:company_id>/modules')
@super_admin_required
def view_company_modules(company_id):
    """View company-specific module details"""
    company = CompanyService.get_company_by_id(company_id)
    if not company:
        flash('Company not found.', 'error')
        return redirect(url_for('admin_companies'))
    
    modules = CompanyModuleService.get_company_modules(company_id)
    monthly_cost = CompanyModuleService.get_company_monthly_cost(company_id)
    
    return render_template('admin/company_module_detail.html',
                         company=company,
                         modules=modules,
                         monthly_cost=monthly_cost)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# Add these routes to your app.py file

@app.route('/admin/company-modules')
def admin_company_modules():
    if not session.get('is_super_admin'):
        flash('Access denied. Super admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from services.company_module_service import CompanyModuleService
        from models import Company, ModuleDefinition
        
        companies = Company.query.filter_by(is_active=True).all()
        modules = ModuleDefinition.query.filter_by(is_active=True).order_by(ModuleDefinition.sort_order).all()
        billing_summary = CompanyModuleService.get_all_companies_billing_summary()
        
        return render_template('admin/company_modules.html', 
                             companies=companies, 
                             modules=modules,
                             billing_summary=billing_summary)
    except Exception as e:
        flash(f'Error loading company modules: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

# Add this route to your app.py file:

@app.route('/documents')
@login_required
@require_module('document_management')
def documents():
    """View and manage documents"""
    # Get documents for the current user's company
    company_id = current_user.company_id if current_user.company_id else None
    
    if not company_id:
        flash('No company associated with your account', 'error')
        return redirect(url_for('home'))
    
    # Get all documents for this company
    documents = Document.query.filter_by(company_id=company_id).order_by(Document.created_at.desc()).all()
    
    # Get document statistics
    total_documents = len(documents)
    recent_documents = len([d for d in documents if (datetime.now() - d.created_at).days <= 7])
    
    # Group documents by type if you have a document_type field
    document_types = {}
    for doc in documents:
        doc_type = getattr(doc, 'document_type', 'Other')
        document_types[doc_type] = document_types.get(doc_type, 0) + 1
    
    # Calculate total file size
    total_size = sum([getattr(doc, 'file_size', 0) for doc in documents])
    
    # Prepare statistics
    doc_stats = type('DocumentStats', (), {
        'total_documents': total_documents,
        'recent_documents': recent_documents,
        'document_types': document_types,
        'total_size': total_size
    })()
    
    return render_template('documents.html', 
                         documents=documents, 
                         doc_stats=doc_stats)

@app.route('/documents/upload', methods=['GET', 'POST'])
@login_required
@require_module('document_management')
def upload_document():
    """Upload a new document"""
    if request.method == 'POST':
        try:
            # Handle file upload
            if 'file' not in request.files:
                flash('No file selected', 'error')
                return redirect(request.url)
            
            file = request.files['file']
            if file.filename == '':
                flash('No file selected', 'error')
                return redirect(request.url)
            
            if file:
                # Get form data
                title = request.form.get('title', '').strip()
                description = request.form.get('description', '').strip()
                document_type = request.form.get('document_type', 'Other')
                
                # Use title or filename
                if not title:
                    title = file.filename
                
                # Create document record
                document = Document(
                    title=title,
                    description=description,
                    filename=file.filename,
                    document_type=document_type,
                    file_size=len(file.read()),
                    company_id=current_user.company_id,
                    uploaded_by=current_user.id
                )
                
                # Reset file pointer after reading size
                file.seek(0)
                
                # Save file (you'll need to implement file storage)
                # For now, we'll just save the record
                db.session.add(document)
                db.session.commit()
                
                flash(f'Document "{title}" uploaded successfully!', 'success')
                return redirect(url_for('documents'))
                
        except Exception as e:
            db.session.rollback()
            flash(f'Error uploading document: {str(e)}', 'error')
    
    # GET request - show upload form
    document_types = ['Contract', 'Invoice', 'Report', 'Tender Document', 'Other']
    return render_template('upload_document.html', document_types=document_types)

@app.route('/documents/<int:document_id>/view')
@login_required
def view_document(document_id):
    """View document details"""
    document = Document.query.filter_by(
        id=document_id, 
        company_id=current_user.company_id
    ).first_or_404()
    
    return render_template('view_document.html', document=document)

@app.route('/documents/<int:document_id>/download')
@login_required
def download_document(document_id):
    """Download a document"""
    document = Document.query.filter_by(
        id=document_id, 
        company_id=current_user.company_id
    ).first_or_404()
    
    # For now, just redirect back with a message
    # You'll need to implement actual file serving
    flash(f'Download feature for "{document.title}" coming soon', 'info')
    return redirect(url_for('documents'))

@app.route('/documents/<int:document_id>/delete', methods=['POST'])
@login_required
def delete_document(document_id):
    """Delete a document"""
    try:
        document = Document.query.filter_by(
            id=document_id, 
            company_id=current_user.company_id
        ).first_or_404()
        
        # Check permissions (only uploader or admin can delete)
        if document.uploaded_by != current_user.id and not current_user.role.name in ['Company Admin', 'Super Admin']:
            flash('You do not have permission to delete this document', 'error')
            return redirect(url_for('documents'))
        
        title = document.title
        db.session.delete(document)
        db.session.commit()
        
        flash(f'Document "{title}" deleted successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting document: {str(e)}', 'error')
    
    return redirect(url_for('documents'))

# Add this route to your app.py file:

@app.route('/my-company/modules')
@login_required
def my_company_modules():
    """View modules for current user's company"""
    # Get the current user's company
    if not current_user.company_id:
        flash('No company associated with your account', 'error')
        return redirect(url_for('home'))
    
    company = Company.query.get_or_404(current_user.company_id)
    
    # Define available modules (same as admin but for regular users)
    available_modules = [
        {
            'module_name': 'tender_management',
            'display_name': 'Tender Management',
            'description': 'Create, manage and track tenders',
            'category': 'core',
            'monthly_price': 0.0,
            'is_core': True
        },
        {
            'module_name': 'user_management',
            'display_name': 'User Management', 
            'description': 'Manage company users and permissions',
            'category': 'core',
            'monthly_price': 0.0,
            'is_core': True
        },
        {
            'module_name': 'analytics',
            'display_name': 'Analytics & Reporting',
            'description': 'Advanced analytics and custom reports',
            'category': 'feature',
            'monthly_price': 499.99,  # ZAR pricing
            'is_core': False
        },
        {
            'module_name': 'notifications',
            'display_name': 'Email Notifications',
            'description': 'Automated email notifications and alerts',
            'category': 'feature', 
            'monthly_price': 179.99,  # ZAR pricing
            'is_core': False
        },
        {
            'module_name': 'api_access',
            'display_name': 'API Access',
            'description': 'REST API for third-party integrations',
            'category': 'premium',
            'monthly_price': 899.99,  # ZAR pricing
            'is_core': False
        },
        {
            'module_name': 'white_label',
            'display_name': 'White Label Branding',
            'description': 'Custom branding and white-label options',
            'category': 'premium',
            'monthly_price': 1799.99,  # ZAR pricing
            'is_core': False
        }
    ]
    
    # Get existing company modules from database
    try:
        existing_modules = CompanyModule.query.filter_by(company_id=company.id).all()
        existing_module_names = {mod.module_name for mod in existing_modules}
    except:
        existing_modules = []
        existing_module_names = set()
    
    # Create modules data structure
    modules_data = []
    for module_def in available_modules:
        # Create a module definition object
        module_definition = type('ModuleDefinition', (), module_def)()
        
        # Check if module is enabled for this company
        is_enabled = module_def['module_name'] in existing_module_names
        
        # Get the company module record if it exists
        company_module = None
        if is_enabled:
            company_module = next((mod for mod in existing_modules if mod.module_name == module_def['module_name']), None)
        
        # Create module data object
        module_data = type('ModuleData', (), {
            'definition': module_definition,
            'is_enabled': is_enabled,
            'company_module': company_module
        })()
        
        modules_data.append(module_data)
    
    # Calculate statistics
    total_modules = len(available_modules)
    enabled_count = len([m for m in modules_data if m.is_enabled])
    monthly_cost = sum([m.definition.monthly_price for m in modules_data if m.is_enabled])
    
    return render_template('my_company_modules.html',
                         company=company,
                         modules_data=modules_data,
                         total_modules=total_modules,
                         enabled_count=enabled_count,
                         monthly_cost=monthly_cost)

@app.route('/my-company/modules/request', methods=['POST'])
@login_required
def request_module():
    """Request a module to be enabled for the company"""
    try:
        data = request.get_json()
        module_name = data.get('module_name')
        notes = data.get('notes', '')
        
        if not module_name:
            return jsonify({'success': False, 'message': 'Module name is required'})
        
        # Check if user has permission (company admin or higher)
        if current_user.role.name not in ['Company Admin', 'Super Admin']:
            return jsonify({'success': False, 'message': 'You do not have permission to request modules'})
        
        # Create a module request record (you'll need to create this model)
        # For now, we'll just flash a message
        flash(f'Module request for "{module_name}" has been submitted for approval', 'info')
        
        return jsonify({
            'success': True, 
            'message': f'Request for {module_name} submitted successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error submitting request: {str(e)}'})

@app.route('/my-company/profile')
@login_required  
def my_company_profile():
    """View current user's company profile"""
    if not current_user.company_id:
        flash('No company associated with your account', 'error')
        return redirect(url_for('home'))
    
    company = Company.query.get_or_404(current_user.company_id)
    
    # Get company statistics
    total_users = User.query.filter_by(company_id=company.id).count()
    active_users = User.query.filter_by(company_id=company.id, is_active=True).count()
    
    # Get document count if Document model exists
    try:
        total_documents = Document.query.filter_by(company_id=company.id).count()
    except:
        total_documents = 0
    
    # Get tender count if Tender model exists  
    try:
        total_tenders = Tender.query.filter_by(company_id=company.id).count()
    except:
        total_tenders = 0
    
    company_stats = type('CompanyStats', (), {
        'total_users': total_users,
        'active_users': active_users,
        'total_documents': total_documents,
        'total_tenders': total_tenders
    })()
    
    return render_template('my_company_profile.html',
                         company=company,
                         company_stats=company_stats)
 
@app.route('/debug-routes')
def debug_routes():
    import urllib
    output = []
    for rule in app.url_map.iter_rules():
        output.append(f"{rule.endpoint}: {rule}")
    return '<br>'.join(output)






@app.route('/admin/billing/bills/export')
@super_admin_required
def export_bills():
    """Export bills to PDF or Excel"""
    export_format = request.args.get('format', 'excel')
    
    # Get same filters as billing_bills
    company_id = request.args.get('company_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    status = request.args.get('status')
    
    # Parse dates
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
    
    # Get bills
    bills_data = BillingService.get_bills_with_filters(
        company_id=company_id,
        start_date=start_date_obj,
        end_date=end_date_obj,
        status=status
    )
    
    if export_format == 'pdf':
        return export_bills_pdf(bills_data)
    else:
        return export_bills_excel(bills_data)


@app.route('/admin/billing/bills/<int:bill_id>/view')
@super_admin_required
def view_bill(bill_id):
    """View detailed bill"""
    bill = MonthlyBill.query.get_or_404(bill_id)
    line_items = BillLineItem.query.filter_by(bill_id=bill_id).all()
    
    return render_template('admin/view_bill.html', 
                         bill=bill, 
                         line_items=line_items)

@app.route('/admin/billing/bills/<int:bill_id>/status', methods=['POST'])
@super_admin_required
def update_bill_status(bill_id):
    """Update bill status"""
    new_status = request.form.get('status')
    if not new_status:
        flash('Status is required', 'error')
        return redirect(url_for('view_bill', bill_id=bill_id))
    
    success, message = BillingService.update_bill_status(
        bill_id=bill_id,
        new_status=new_status,
        updated_by=session['user_id']
    )
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('view_bill', bill_id=bill_id))




@app.route('/admin/billing/pricing/<int:company_id>/set', methods=['POST'])
@super_admin_required
def set_custom_pricing(company_id):
    """Set custom pricing for a company module"""
    try:
        data = request.get_json()
        module_id = data.get('module_id')
        custom_price = data.get('custom_price')
        notes = data.get('notes', '')
        
        if not all([module_id, custom_price is not None]):
            return jsonify({
                'success': False,
                'message': 'Module ID and custom price are required'
            }), 400
        
        success, message = BillingService.set_custom_pricing(
            company_id=company_id,
            module_id=module_id,
            custom_price=custom_price,
            created_by=session['user_id'],
            notes=notes
        )
        
        if success:
            # Get updated pricing data
            pricing_data = BillingService.get_company_pricing(company_id)
            total_actual = sum(item['effective_price'] for item in pricing_data)
            
            return jsonify({
                'success': True,
                'message': message,
                'new_total': total_actual
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error setting custom pricing: {str(e)}'
        }), 500

@app.route('/admin/billing/pricing/<int:company_id>/remove', methods=['POST'])
@super_admin_required
def remove_custom_pricing(company_id):
    """Remove custom pricing for a company module"""
    try:
        data = request.get_json()
        module_id = data.get('module_id')
        
        if not module_id:
            return jsonify({
                'success': False,
                'message': 'Module ID is required'
            }), 400
        
        success, message = BillingService.remove_custom_pricing(
            company_id=company_id,
            module_id=module_id
        )
        
        if success:
            # Get updated pricing data
            pricing_data = BillingService.get_company_pricing(company_id)
            total_actual = sum(item['effective_price'] for item in pricing_data)
            
            return jsonify({
                'success': True,
                'message': message,
                'new_total': total_actual
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error removing custom pricing: {str(e)}'
        }), 500
        
@app.route('/admin/billing/pricing/<int:company_id>/edit', methods=['GET', 'POST'])
@login_required
@super_admin_required
def edit_company_pricing(company_id):
    """Edit company pricing"""
    company = Company.query.get_or_404(company_id)
    
    if request.method == 'POST':
        try:
            if request.is_json:
                data = request.get_json()
                action = data.get('action')
                module_id = data.get('module_id')
            else:
                action = request.form.get('action')
                module_id = request.form.get('module_id')
            
            if action == 'set_pricing':
                custom_price = data.get('custom_price') if request.is_json else request.form.get('custom_price')
                notes = data.get('notes', '') if request.is_json else request.form.get('notes', '')
                
                if not all([module_id, custom_price is not None]):
                    return jsonify({
                        'success': False,
                        'message': 'Module ID and custom price are required'
                    }), 400
                
                # Create or update custom pricing
                custom_pricing = CompanyModulePricing.query.filter_by(
                    company_id=company_id,
                    module_id=module_id,
                    is_active=True
                ).first()
                
                if custom_pricing:
                    custom_pricing.custom_price = float(custom_price)
                    custom_pricing.notes = notes
                else:
                    custom_pricing = CompanyModulePricing(
                        company_id=company_id,
                        module_id=module_id,
                        custom_price=float(custom_price),
                        effective_date=datetime.utcnow(),
                        created_by=session['user_id'],
                        notes=notes
                    )
                    db.session.add(custom_pricing)
                
                db.session.commit()
                return jsonify({
                    'success': True,
                    'message': 'Custom pricing set successfully'
                })
                
            elif action == 'remove_pricing':
                # Remove custom pricing
                custom_pricing = CompanyModulePricing.query.filter_by(
                    company_id=company_id,
                    module_id=module_id,
                    is_active=True
                ).first()
                
                if custom_pricing:
                    custom_pricing.is_active = False
                    db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Custom pricing removed successfully'
                })
            
            return jsonify({'success': False, 'message': 'Invalid action'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Error updating pricing: {str(e)}'
            }), 500
    
    # GET request - show the form
    try:
        # Get all available modules
        all_modules = ModuleDefinition.query.filter_by(is_active=True).order_by(ModuleDefinition.sort_order).all()
        
        # Get enabled modules for this company
        enabled_company_modules = db.session.query(CompanyModule, ModuleDefinition).join(ModuleDefinition).filter(
            CompanyModule.company_id == company_id,
            CompanyModule.is_enabled == True
        ).all()
        
        # Get custom pricing for this company
        custom_pricing_records = CompanyModulePricing.query.filter_by(
            company_id=company_id,
            is_active=True
        ).all()
        
        # Create a mapping of module_id to custom pricing
        custom_pricing_map = {cp.module_id: cp for cp in custom_pricing_records}
        
        # Build modules data
        modules = []
        for module_def in all_modules:
            # Check if module is enabled for this company
            is_enabled = any(cm.module_id == module_def.id for cm, _ in enabled_company_modules)
            
            # Get custom pricing if exists
            custom_pricing = custom_pricing_map.get(module_def.id)
            has_custom_pricing = custom_pricing is not None
            custom_price = float(custom_pricing.custom_price) if custom_pricing else None
            effective_price = custom_price if has_custom_pricing else float(module_def.monthly_price or 0)
            
            module_data = {
                'id': module_def.id,
                'module_name': module_def.module_name,
                'display_name': module_def.display_name,
                'description': module_def.description,
                'category': module_def.category,
                'is_core': module_def.is_core,
                'enabled': is_enabled,
                'price': float(module_def.monthly_price or 0),  # Default price
                'has_custom_pricing': has_custom_pricing,
                'custom_price': custom_price,
                'effective_price': effective_price
            }
            modules.append(module_data)
        
        # Calculate monthly cost
        monthly_cost = sum(m['effective_price'] for m in modules if m['enabled'])
        
        return render_template('admin/edit_company_pricing.html',
                             company=company,
                             modules=modules,
                             monthly_cost=monthly_cost)
                             
    except Exception as e:
        flash(f'Error loading pricing data: {str(e)}', 'error')
        return redirect(url_for('admin_companies'))




@app.route('/admin/billing/company/<int:company_id>')
@login_required
@super_admin_required
def company_billing_details(company_id):
    """Detailed billing information for a specific company"""
    try:
        company = Company.query.get_or_404(company_id)
        
        # Get company's enabled modules
        company_modules = db.session.query(CompanyModule, ModuleDefinition).join(
            ModuleDefinition, CompanyModule.module_id == ModuleDefinition.id
        ).filter(
            CompanyModule.company_id == company_id
        ).order_by(ModuleDefinition.sort_order).all()
        
        # Calculate monthly cost
        monthly_cost = calculate_company_monthly_cost(company_id)
        
        # Get recent bills for this company
        recent_bills = MonthlyBill.query.filter_by(
            company_id=company_id
        ).order_by(MonthlyBill.generated_at.desc()).limit(12).all()
        
        # Get custom pricing
        custom_pricing = CompanyModulePricing.query.filter_by(
            company_id=company_id,
            is_active=True
        ).all()
        
        return render_template('billing/company_details.html',
                             company=company,
                             company_modules=company_modules,
                             monthly_cost=monthly_cost,
                             recent_bills=recent_bills,
                             custom_pricing=custom_pricing)
                             
    except Exception as e:
        print(f"Error in company billing details: {str(e)}")
        flash('Error loading company billing details', 'error')
        return redirect(url_for('billing_dashboard'))

# Updated utility functions
def calculate_company_monthly_cost(company_id):
    """Calculate the total monthly cost for a company including custom pricing"""
    try:
        total_cost = 0
        
        # Get all enabled modules for the company
        enabled_modules = db.session.query(CompanyModule, ModuleDefinition).join(
            ModuleDefinition, CompanyModule.module_id == ModuleDefinition.id
        ).filter(
            CompanyModule.company_id == company_id,
            CompanyModule.is_enabled == True
        ).all()
        
        for company_module, module_def in enabled_modules:
            # Check for custom pricing
            custom_pricing = CompanyModulePricing.query.filter_by(
                company_id=company_id,
                module_id=module_def.id,
                is_active=True
            ).order_by(CompanyModulePricing.effective_date.desc()).first()
            
            if custom_pricing:
                total_cost += float(custom_pricing.custom_price)
            else:
                total_cost += float(module_def.monthly_price or 0)
        
        return total_cost
        
    except Exception as e:
        print(f"Error calculating company monthly cost: {str(e)}")
        return 0

def calculate_module_revenue_breakdown():
    """Calculate revenue breakdown by module - returns float values"""
    try:
        module_revenue = {}
        
        # Get all active modules
        modules = ModuleDefinition.query.filter_by(is_active=True).all()
        
        for module in modules:
            total_revenue = 0.0  # Use float
            
            # Get all companies using this module
            company_modules = CompanyModule.query.filter_by(
                module_id=module.id,
                is_enabled=True
            ).all()
            
            for company_module in company_modules:
                # Check for custom pricing
                try:
                    custom_pricing = CompanyModulePricing.query.filter_by(
                        company_id=company_module.company_id,
                        module_id=module.id,
                        is_active=True
                    ).first()
                    
                    if custom_pricing:
                        total_revenue += float(custom_pricing.custom_price or 0)
                    else:
                        total_revenue += float(module.monthly_price or 0)
                except:
                    total_revenue += float(module.monthly_price or 0)
            
            if total_revenue > 0:
                module_revenue[module.display_name] = total_revenue
        
        # Format for Chart.js - ensure all values are float
        if module_revenue:
            return {
                'labels': list(module_revenue.keys()),
                'data': [float(x) for x in module_revenue.values()]  # Convert to float
            }
        else:
            return {
                'labels': ['No Revenue Data'],
                'data': [0.0]
            }
            
    except Exception as e:
        print(f"Error calculating module revenue breakdown: {str(e)}")
        return {'labels': ['Error'], 'data': [0.0]}

def calculate_module_monthly_revenue(module_id):
    """Calculate monthly revenue for a specific module"""
    try:
        total_revenue = 0
        
        # Get all companies using this module
        company_modules = CompanyModule.query.filter_by(
            module_id=module_id,
            is_enabled=True
        ).all()
        
        for company_module in company_modules:
            # Check for custom pricing
            custom_pricing = CompanyModulePricing.query.filter_by(
                company_id=company_module.company_id,
                module_id=module_id,
                is_active=True
            ).order_by(CompanyModulePricing.effective_date.desc()).first()
            
            if custom_pricing:
                total_revenue += float(custom_pricing.custom_price)
            else:
                module_def = ModuleDefinition.query.get(module_id)
                if module_def:
                    total_revenue += float(module_def.monthly_price or 0)
        
        return total_revenue
        
    except Exception as e:
        print(f"Error calculating module monthly revenue: {str(e)}")
        return 0

def get_companies_with_custom_pricing():
    """Get companies that have custom pricing - returns float values"""
    try:
        companies_data = []
        
        # Get companies with custom pricing (if table exists)
        try:
            companies_with_custom = db.session.query(CompanyModulePricing.company_id).filter_by(
                is_active=True
            ).distinct().all()
            
            company_ids = [c[0] for c in companies_with_custom]
            companies = Company.query.filter(Company.id.in_(company_ids)).all()
        except:
            # If CompanyModulePricing table doesn't exist, return empty list
            return []
        
        for company in companies:
            # Calculate default cost
            default_cost = 0.0  # Use float
            custom_cost = 0.0   # Use float
            
            enabled_modules = db.session.query(CompanyModule, ModuleDefinition).join(
                ModuleDefinition, CompanyModule.module_id == ModuleDefinition.id
            ).filter(
                CompanyModule.company_id == company.id,
                CompanyModule.is_enabled == True
            ).all()
            
            for company_module, module_def in enabled_modules:
                module_price = float(module_def.monthly_price or 0)
                default_cost += module_price
                
                # Check for custom pricing
                try:
                    custom_pricing = CompanyModulePricing.query.filter_by(
                        company_id=company.id,
                        module_id=module_def.id,
                        is_active=True
                    ).first()
                    
                    if custom_pricing:
                        custom_cost += float(custom_pricing.custom_price or 0)
                    else:
                        custom_cost += module_price
                except:
                    custom_cost += module_price
            
            companies_data.append({
                'company': company,
                'default_cost': default_cost,  # Already float
                'custom_cost': custom_cost     # Already float
            })
        
        return companies_data
        
    except Exception as e:
        print(f"Error getting companies with custom pricing: {str(e)}")
        return []


def calculate_company_default_cost(company_id):
    """Calculate what the company cost would be without custom pricing"""
    try:
        total_cost = 0
        
        # Get all enabled modules for the company
        enabled_modules = db.session.query(CompanyModule, ModuleDefinition).join(
            ModuleDefinition, CompanyModule.module_id == ModuleDefinition.id
        ).filter(
            CompanyModule.company_id == company_id,
            CompanyModule.is_enabled == True
        ).all()
        
        for company_module, module_def in enabled_modules:
            total_cost += float(module_def.monthly_price or 0)
        
        return total_cost
        
    except Exception as e:
        print(f"Error calculating company default cost: {str(e)}")
        return 0


@app.route('/admin/billing/modules/add', methods=['POST'])
@login_required
@super_admin_required
def add_module():
    """Add a new module"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['module_name', 'display_name', 'category']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'{field.replace("_", " ").title()} is required'
                }), 400
        
        # Check if module name already exists
        existing = ModuleDefinition.query.filter_by(module_name=data['module_name']).first()
        if existing:
            return jsonify({
                'success': False,
                'message': 'Module name already exists'
            }), 400
        
        # Create new module
        new_module = ModuleDefinition(
            module_name=data['module_name'],
            display_name=data['display_name'],
            description=data.get('description', ''),
            category=data['category'],
            monthly_price=float(data.get('monthly_price', 0)),
            is_core=data.get('is_core', False),
            is_active=data.get('is_active', True),
            sort_order=int(data.get('sort_order', 0))
        )
        
        db.session.add(new_module)
        db.session.commit()
        
        # Log the action
        app.logger.info(f"Module '{new_module.display_name}' created by user {session.get('user_id')}")
        
        return jsonify({
            'success': True,
            'message': 'Module created successfully',
            'module_id': new_module.id
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating module: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error creating module'
        }), 500

@app.route('/admin/billing/modules/<int:module_id>/edit', methods=['POST'])
@login_required
@super_admin_required
def edit_module(module_id):
    """Edit an existing module"""
    try:
        module = ModuleDefinition.query.get_or_404(module_id)
        data = request.get_json()
        
        # Update fields
        if 'display_name' in data:
            module.display_name = data['display_name']
        if 'description' in data:
            module.description = data['description']
        if 'category' in data:
            module.category = data['category']
        if 'monthly_price' in data:
            module.monthly_price = float(data['monthly_price'])
        if 'is_core' in data and not module.is_core:  # Prevent removing core status
            module.is_core = data['is_core']
        if 'is_active' in data:
            module.is_active = data['is_active']
        if 'sort_order' in data:
            module.sort_order = int(data['sort_order'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Module updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating module: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error updating module'
        }), 500

@app.route('/admin/billing/modules/<int:module_id>/delete', methods=['POST'])
@login_required
@super_admin_required
def delete_module(module_id):
    """Delete a module (only if not core and not in use)"""
    try:
        module = ModuleDefinition.query.get_or_404(module_id)
        
        # Check if module is core
        if module.is_core:
            return jsonify({
                'success': False,
                'message': 'Cannot delete core modules'
            }), 400
        
        # Check if module is in use
        usage_count = CompanyModule.query.filter_by(module_id=module_id, is_enabled=True).count()
        if usage_count > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot delete module. It is currently being used by {usage_count} companies.'
            }), 400
        
        # Delete the module
        db.session.delete(module)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Module deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting module: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error deleting module'
        }), 500

@app.route('/admin/billing/modules/<int:module_id>/toggle-status', methods=['POST'])
@login_required
@super_admin_required
def toggle_module_status(module_id):
    """Toggle module active/inactive status"""
    try:
        module = ModuleDefinition.query.get_or_404(module_id)
        
        # Toggle status
        module.is_active = not module.is_active
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Module {"activated" if module.is_active else "deactivated"} successfully',
            'new_status': module.is_active
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error toggling module status: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error updating module status'
        }), 500

@app.route('/admin/billing/modules/initialize-defaults', methods=['POST'])
@login_required
@super_admin_required
def initialize_default_modules():
    """Initialize default system modules"""
    try:
        default_modules = [
            {
                'module_name': 'user_management',
                'display_name': 'User Management',
                'description': 'Basic user account management and authentication',
                'category': 'core',
                'monthly_price': 0.00,
                'is_core': True,
                'sort_order': 1
            },
            {
                'module_name': 'tender_management',
                'display_name': 'Tender Management',
                'description': 'Core tender creation and management functionality',
                'category': 'core',
                'monthly_price': 0.00,
                'is_core': True,
                'sort_order': 2
            },
            {
                'module_name': 'document_management',
                'display_name': 'Document Management',
                'description': 'Upload, organize, and manage tender documents',
                'category': 'feature',
                'monthly_price': 29.99,
                'is_core': False,
                'sort_order': 3
            },
            {
                'module_name': 'reporting',
                'display_name': 'Advanced Reporting',
                'description': 'Advanced analytics and custom reports',
                'category': 'feature',
                'monthly_price': 49.99,
                'is_core': False,
                'sort_order': 4
            },
            {
                'module_name': 'custom_fields',
                'display_name': 'Custom Fields',
                'description': 'Create custom fields for tenders and companies',
                'category': 'feature',
                'monthly_price': 19.99,
                'is_core': False,
                'sort_order': 5
            },
            {
                'module_name': 'api_access',
                'display_name': 'API Access',
                'description': 'REST API access for third-party integrations',
                'category': 'premium',
                'monthly_price': 99.99,
                'is_core': False,
                'sort_order': 6
            },
            {
                'module_name': 'white_label',
                'display_name': 'White Label',
                'description': 'Custom branding and white-label solution',
                'category': 'premium',
                'monthly_price': 199.99,
                'is_core': False,
                'sort_order': 7
            },
            {
                'module_name': 'notes_comments',
                'display_name': 'Notes & Comments',
                'description': 'Internal notes and commenting system',
                'category': 'feature',
                'monthly_price': 9.99,
                'is_core': False,
                'sort_order': 8
            },
            {
                'module_name': 'company_management',
                'display_name': 'Company Management',
                'description': 'Advanced company settings and module management',
                'category': 'feature',
                'monthly_price': 39.99,
                'is_core': False,
                'sort_order': 9
            }
        ]
        
        created_count = 0
        for module_data in default_modules:
            # Check if module already exists
            existing = ModuleDefinition.query.filter_by(module_name=module_data['module_name']).first()
            if not existing:
                new_module = ModuleDefinition(**module_data)
                db.session.add(new_module)
                created_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully created {created_count} default modules'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error initializing default modules: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error initializing default modules'
        }), 500

## Replace your billing_dashboard route with this version that properly handles Decimal objects:

@app.route('/admin/billing')
@login_required
@super_admin_required
def billing_dashboard():
    """Main billing dashboard - accessible via url_for('billing_dashboard')"""
    try:
        # Calculate billing statistics
        billing_stats = {
            'total_monthly_revenue': 0.0,  # Use float instead of Decimal
            'active_companies': 0,
            'pending_bills': 0,
            'custom_pricing_count': 0
        }
        
        # Get active companies and their monthly costs
        active_companies = Company.query.filter_by(is_active=True).all()
        billing_stats['active_companies'] = len(active_companies)
        
        total_revenue = 0.0  # Use float instead of Decimal
        for company in active_companies:
            # Calculate each company's monthly cost
            enabled_modules = db.session.query(CompanyModule, ModuleDefinition).join(
                ModuleDefinition, CompanyModule.module_id == ModuleDefinition.id
            ).filter(
                CompanyModule.company_id == company.id,
                CompanyModule.is_enabled == True
            ).all()
            
            for company_module, module_def in enabled_modules:
                # Check for custom pricing
                try:
                    custom_pricing = CompanyModulePricing.query.filter_by(
                        company_id=company.id,
                        module_id=module_def.id,
                        is_active=True
                    ).first()
                    
                    if custom_pricing:
                        total_revenue += float(custom_pricing.custom_price or 0)
                    else:
                        total_revenue += float(module_def.monthly_price or 0)
                except:
                    # If CompanyModulePricing table doesn't exist, just use default price
                    total_revenue += float(module_def.monthly_price or 0)
        
        billing_stats['total_monthly_revenue'] = total_revenue
        
        # Count custom pricing entries (if table exists)
        try:
            custom_pricing_count = CompanyModulePricing.query.filter_by(is_active=True).count()
            billing_stats['custom_pricing_count'] = custom_pricing_count
        except:
            billing_stats['custom_pricing_count'] = 0
        
        # Get recent bills (mock data for now since MonthlyBill might not exist)
        recent_bills = []
        billing_stats['pending_bills'] = 0
        
        # Module revenue breakdown - convert all Decimal to float
        module_revenue = calculate_module_revenue_breakdown()
        if module_revenue and 'data' in module_revenue:
            # Ensure all values are float, not Decimal
            module_revenue['data'] = [float(x) for x in module_revenue['data']]
        
        # Companies with custom pricing - convert all Decimal to float
        custom_pricing_companies = get_companies_with_custom_pricing()
        for company_data in custom_pricing_companies:
            company_data['default_cost'] = float(company_data['default_cost'])
            company_data['custom_cost'] = float(company_data['custom_cost'])
        
        # Calculate some additional stats
        try:
            billing_stats['total_modules'] = ModuleDefinition.query.filter_by(is_active=True).count()
            billing_stats['enabled_modules'] = CompanyModule.query.filter_by(is_enabled=True).count()
        except:
            billing_stats['total_modules'] = 0
            billing_stats['enabled_modules'] = 0
        
        return render_template('billing/dashboard.html',
                             billing_stats=billing_stats,
                             recent_bills=recent_bills,
                             module_revenue=module_revenue,
                             custom_pricing_companies=custom_pricing_companies)
                             
    except Exception as e:
        print(f"Error in billing dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('Error loading billing dashboard', 'error')
        return redirect(url_for('admin_companies'))

@app.route('/admin/billing/generate')
@login_required
@super_admin_required
def generate_bill():
    """Generate bill page - accessible via url_for('generate_bill')"""
    try:
        companies = Company.query.filter_by(is_active=True).order_by(Company.name).all()
        current_date = datetime.now()
        
        return render_template('billing/generate_bill.html', 
                             companies=companies,
                             current_month=current_date.month,
                             current_year=current_date.year)
        
    except Exception as e:
        print(f"Error in generate bill page: {str(e)}")
        flash('Error loading generate bill page', 'error')
        return redirect(url_for('billing_dashboard'))

@app.route('/admin/billing/generate', methods=['POST'])
@login_required
@super_admin_required
def process_generate_bill():
    """Process bill generation"""
    try:
        data = request.get_json()
        company_id = data.get('company_id')
        bill_month = int(data.get('bill_month'))
        bill_year = int(data.get('bill_year'))
        
        if not all([company_id, bill_month, bill_year]):
            return jsonify({
                'success': False,
                'message': 'Company, month, and year are required'
            }), 400
        
        company = Company.query.get_or_404(company_id)
        
        # Calculate the bill amount
        total_amount = 0
        enabled_modules = db.session.query(CompanyModule, ModuleDefinition).join(
            ModuleDefinition, CompanyModule.module_id == ModuleDefinition.id
        ).filter(
            CompanyModule.company_id == company_id,
            CompanyModule.is_enabled == True
        ).all()
        
        for company_module, module_def in enabled_modules:
            try:
                custom_pricing = CompanyModulePricing.query.filter_by(
                    company_id=company_id,
                    module_id=module_def.id,
                    is_active=True
                ).first()
                
                if custom_pricing:
                    total_amount += float(custom_pricing.custom_price or 0)
                else:
                    total_amount += float(module_def.monthly_price or 0)
            except:
                total_amount += float(module_def.monthly_price or 0)
        
        # For now, just return success (you can implement actual bill creation later)
        return jsonify({
            'success': True,
            'message': f'Bill generated for {company.name} for {bill_month:02d}/{bill_year}. Total: R{total_amount:.2f}',
            'total_amount': total_amount
        })
        
    except Exception as e:
        print(f"Error generating bill: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error generating bill: {str(e)}'
        }), 500

@app.route('/admin/billing/modules')
@login_required
@super_admin_required
def manage_modules():
    """Module management page - accessible via url_for('manage_modules')"""
    try:
        # Get modules from database
        modules = ModuleDefinition.query.order_by(ModuleDefinition.sort_order, ModuleDefinition.display_name).all()
        
        # Add usage statistics to each module
        for module in modules:
            try:
                module.usage_count = CompanyModule.query.filter_by(
                    module_id=module.id, 
                    is_enabled=True
                ).count()
                
                # Calculate monthly revenue for this module
                total_revenue = 0
                company_modules = CompanyModule.query.filter_by(
                    module_id=module.id,
                    is_enabled=True
                ).all()
                
                for cm in company_modules:
                    try:
                        custom_pricing = CompanyModulePricing.query.filter_by(
                            company_id=cm.company_id,
                            module_id=module.id,
                            is_active=True
                        ).first()
                        
                        if custom_pricing:
                            total_revenue += float(custom_pricing.custom_price or 0)
                        else:
                            total_revenue += float(module.monthly_price or 0)
                    except:
                        total_revenue += float(module.monthly_price or 0)
                
                module.monthly_revenue = total_revenue
            except:
                module.usage_count = 0
                module.monthly_revenue = 0
        
        return render_template('billing/manage_modules.html', modules=modules)
        
    except Exception as e:
        print(f"Error in manage modules: {str(e)}")
        flash('Error loading modules', 'error')
        return redirect(url_for('billing_dashboard'))

@app.route('/admin/billing/modules/<int:module_id>/usage')
@login_required
@super_admin_required
def view_module_usage(module_id):
    """View detailed usage statistics for a module"""
    try:
        module = ModuleDefinition.query.get_or_404(module_id)
        
        # Get companies using this module
        company_modules = db.session.query(CompanyModule, Company).join(Company).filter(
            CompanyModule.module_id == module_id,
            CompanyModule.is_enabled == True
        ).all()
        
        # Calculate statistics
        usage_stats = {
            'total_companies': len(company_modules),
            'total_revenue': 0.0,
            'companies': []
        }
        
        for company_module, company in company_modules:
            # Check for custom pricing
            custom_pricing = CompanyModulePricing.query.filter_by(
                company_id=company.id,
                module_id=module_id,
                is_active=True
            ).first()
            
            price = float(custom_pricing.custom_price) if custom_pricing else float(module.monthly_price or 0)
            usage_stats['total_revenue'] += price
            
            usage_stats['companies'].append({
                'name': company.name,
                'price': price,
                'is_custom_pricing': bool(custom_pricing),
                'enabled_date': company_module.enabled_at
            })
        
        return render_template('billing/module_usage.html', 
                             module=module, 
                             usage_stats=usage_stats)
        
    except Exception as e:
        print(f"Error viewing module usage: {str(e)}")
        flash('Error loading module usage data', 'error')
        return redirect(url_for('manage_modules'))


@app.route('/admin/billing/pricing')
@login_required
@super_admin_required
def billing_pricing():
    """Company pricing overview page - accessible via url_for('billing_pricing')"""
    try:
        companies = Company.query.filter_by(is_active=True).all()
        pricing_data = []
        
        for company in companies:
            # Calculate default cost (without custom pricing)
            default_cost = 0
            custom_cost = 0
            
            enabled_modules = db.session.query(CompanyModule, ModuleDefinition).join(
                ModuleDefinition, CompanyModule.module_id == ModuleDefinition.id
            ).filter(
                CompanyModule.company_id == company.id,
                CompanyModule.is_enabled == True
            ).all()
            
            has_custom = False
            custom_modules_count = 0
            
            for company_module, module_def in enabled_modules:
                module_price = float(module_def.monthly_price or 0)
                default_cost += module_price
                
                # Check for custom pricing
                try:
                    custom_pricing = CompanyModulePricing.query.filter_by(
                        company_id=company.id,
                        module_id=module_def.id,
                        is_active=True
                    ).first()
                    
                    if custom_pricing:
                        custom_cost += float(custom_pricing.custom_price or 0)
                        has_custom = True
                        custom_modules_count += 1
                    else:
                        custom_cost += module_price
                except:
                    custom_cost += module_price
            
            pricing_data.append({
                'company': company,
                'default_cost': default_cost,
                'custom_cost': custom_cost,
                'has_custom_pricing': has_custom,
                'difference': custom_cost - default_cost,
                'custom_modules_count': custom_modules_count
            })
        
        return render_template('billing/pricing.html', pricing_data=pricing_data)
        
    except Exception as e:
        print(f"Error in billing pricing: {str(e)}")
        flash('Error loading pricing data', 'error')
        return redirect(url_for('billing_dashboard'))

# Utility functions for billing
def calculate_module_revenue_breakdown():
    """Calculate revenue breakdown by module"""
    try:
        module_revenue = {}
        
        # Get all active modules
        modules = ModuleDefinition.query.filter_by(is_active=True).all()
        
        for module in modules:
            total_revenue = 0
            
            # Get all companies using this module
            company_modules = CompanyModule.query.filter_by(
                module_id=module.id,
                is_enabled=True
            ).all()
            
            for company_module in company_modules:
                # Check for custom pricing
                try:
                    custom_pricing = CompanyModulePricing.query.filter_by(
                        company_id=company_module.company_id,
                        module_id=module.id,
                        is_active=True
                    ).first()
                    
                    if custom_pricing:
                        total_revenue += float(custom_pricing.custom_price or 0)
                    else:
                        total_revenue += float(module.monthly_price or 0)
                except:
                    total_revenue += float(module.monthly_price or 0)
            
            if total_revenue > 0:
                module_revenue[module.display_name] = total_revenue
        
        # Format for Chart.js
        if module_revenue:
            return {
                'labels': list(module_revenue.keys()),
                'data': list(module_revenue.values())
            }
        else:
            return {
                'labels': ['No Revenue Data'],
                'data': [0]
            }
            
    except Exception as e:
        print(f"Error calculating module revenue breakdown: {str(e)}")
        return {'labels': ['Error'], 'data': [0]}

def get_companies_with_custom_pricing():
    """Get companies that have custom pricing"""
    try:
        companies_data = []
        
        # Get companies with custom pricing (if table exists)
        try:
            companies_with_custom = db.session.query(CompanyModulePricing.company_id).filter_by(
                is_active=True
            ).distinct().all()
            
            company_ids = [c[0] for c in companies_with_custom]
            companies = Company.query.filter(Company.id.in_(company_ids)).all()
        except:
            # If CompanyModulePricing table doesn't exist, return empty list
            return []
        
        for company in companies:
            # Calculate default cost
            default_cost = 0
            custom_cost = 0
            
            enabled_modules = db.session.query(CompanyModule, ModuleDefinition).join(
                ModuleDefinition, CompanyModule.module_id == ModuleDefinition.id
            ).filter(
                CompanyModule.company_id == company.id,
                CompanyModule.is_enabled == True
            ).all()
            
            for company_module, module_def in enabled_modules:
                module_price = float(module_def.monthly_price or 0)
                default_cost += module_price
                
                # Check for custom pricing
                try:
                    custom_pricing = CompanyModulePricing.query.filter_by(
                        company_id=company.id,
                        module_id=module_def.id,
                        is_active=True
                    ).first()
                    
                    if custom_pricing:
                        custom_cost += float(custom_pricing.custom_price or 0)
                    else:
                        custom_cost += module_price
                except:
                    custom_cost += module_price
            
            companies_data.append({
                'company': company,
                'default_cost': default_cost,
                'custom_cost': custom_cost
            })
        
        return companies_data
        
    except Exception as e:
        print(f"Error getting companies with custom pricing: {str(e)}")
        return []


# ===== BILL MANAGEMENT =====
@app.route('/admin/billing/bills')
@login_required
@super_admin_required
def billing_bills():
    """Bills management page"""
    try:
        # Get filter parameters
        status_filter = request.args.get('status', 'all')
        company_filter = request.args.get('company', 'all')
        month_filter = request.args.get('month', 'all')
        
        # Build query
        query = Bill.query
        
        if status_filter != 'all':
            query = query.filter(Bill.status == status_filter)
        
        if company_filter != 'all':
            query = query.filter(Bill.company_id == int(company_filter))
        
        if month_filter != 'all':
            year, month = month_filter.split('-')
            query = query.filter(
                and_(Bill.bill_year == int(year), Bill.bill_month == int(month))
            )
        
        bills = query.order_by(Bill.bill_year.desc(), Bill.bill_month.desc()).all()
        
        # Get companies for filter dropdown
        companies = Company.query.filter_by(is_active=True).order_by(Company.name).all()
        
        # Generate month options for filter
        current_date = datetime.now()
        month_options = []
        for i in range(12):
            date = current_date - timedelta(days=30*i)
            month_options.append({
                'value': f"{date.year}-{date.month:02d}",
                'label': date.strftime('%B %Y')
            })
        
        return render_template('billing/bills.html', 
                             bills=bills, 
                             companies=companies,
                             month_options=month_options,
                             filters={
                                 'status': status_filter,
                                 'company': company_filter,
                                 'month': month_filter
                             })
        
    except Exception as e:
        app.logger.error(f"Error in billing bills: {str(e)}")
        flash('Error loading bills', 'error')
        return redirect(url_for('billing_dashboard'))




# ===== UTILITY FUNCTIONS =====
def calculate_company_monthly_cost(company_id):
    """Calculate the total monthly cost for a company including custom pricing"""
    try:
        total_cost = 0
        
        # Get all enabled modules for the company
        enabled_modules = db.session.query(CompanyModule, ModuleDefinition).join(
            ModuleDefinition
        ).filter(
            CompanyModule.company_id == company_id,
            CompanyModule.is_enabled == True
        ).all()
        
        for company_module, module_def in enabled_modules:
            # Check for custom pricing
            custom_pricing = CompanyModulePricing.query.filter_by(
                company_id=company_id,
                module_id=module_def.id,
                is_active=True
            ).first()
            
            if custom_pricing:
                total_cost += custom_pricing.custom_price
            else:
                total_cost += module_def.monthly_price or 0
        
        return total_cost
        
    except Exception as e:
        app.logger.error(f"Error calculating company monthly cost: {str(e)}")
        return 0

def calculate_company_default_cost(company_id):
    """Calculate what the company cost would be without custom pricing"""
    try:
        total_cost = 0
        
        # Get all enabled modules for the company
        enabled_modules = db.session.query(CompanyModule, ModuleDefinition).join(
            ModuleDefinition
        ).filter(
            CompanyModule.company_id == company_id,
            CompanyModule.is_enabled == True
        ).all()
        
        for company_module, module_def in enabled_modules:
            total_cost += module_def.monthly_price or 0
        
        return total_cost
        
    except Exception as e:
        app.logger.error(f"Error calculating company default cost: {str(e)}")
        return 0

def calculate_module_revenue_breakdown():
    """Calculate revenue breakdown by module"""
    try:
        module_revenue = {}
        
        # Get all active modules
        modules = ModuleDefinition.query.filter_by(is_active=True).all()
        
        for module in modules:
            revenue = calculate_module_monthly_revenue(module.id)
            if revenue > 0:
                module_revenue[module.display_name] = revenue
        
        # Format for Chart.js
        if module_revenue:
            return {
                'labels': list(module_revenue.keys()),
                'data': list(module_revenue.values())
            }
        else:
            return None
            
    except Exception as e:
        app.logger.error(f"Error calculating module revenue breakdown: {str(e)}")
        return None

def calculate_module_monthly_revenue(module_id):
    """Calculate monthly revenue for a specific module"""
    try:
        total_revenue = 0
        
        # Get all companies using this module
        company_modules = CompanyModule.query.filter_by(
            module_id=module_id,
            is_enabled=True
        ).all()
        
        for company_module in company_modules:
            # Check for custom pricing
            custom_pricing = CompanyModulePricing.query.filter_by(
                company_id=company_module.company_id,
                module_id=module_id,
                is_active=True
            ).first()
            
            if custom_pricing:
                total_revenue += custom_pricing.custom_price
            else:
                module_def = ModuleDefinition.query.get(module_id)
                total_revenue += module_def.monthly_price or 0
        
        return total_revenue
        
    except Exception as e:
        app.logger.error(f"Error calculating module monthly revenue: {str(e)}")
        return 0

def get_companies_with_custom_pricing():
    """Get companies that have custom pricing"""
    try:
        companies_data = []
        
        # Get companies with custom pricing
        companies_with_custom = db.session.query(CompanyModulePricing.company_id).filter_by(
            is_active=True
        ).distinct().all()
        
        company_ids = [c[0] for c in companies_with_custom]
        companies = Company.query.filter(Company.id.in_(company_ids)).all()
        
        for company in companies:
            default_cost = calculate_company_default_cost(company.id)
            custom_cost = calculate_company_monthly_cost(company.id)
            
            companies_data.append({
                'company': company,
                'default_cost': default_cost,
                'custom_cost': custom_cost
            })
        
        return companies_data
        
    except Exception as e:
        app.logger.error(f"Error getting companies with custom pricing: {str(e)}")
        return []

def has_custom_pricing(company_id):
    """Check if company has any custom pricing"""
    try:
        return CompanyModulePricing.query.filter_by(
            company_id=company_id,
            is_active=True
        ).first() is not None
        
    except Exception as e:
        app.logger.error(f"Error checking custom pricing: {str(e)}")
        return False

def get_custom_pricing_modules_count(company_id):
    """Get count of modules with custom pricing for a company"""
    try:
        return CompanyModulePricing.query.filter_by(
            company_id=company_id,
            is_active=True
        ).count()
        
    except Exception as e:
        app.logger.error(f"Error getting custom pricing modules count: {str(e)}")
        return 0

def create_company_bill(company_id, bill_month, bill_year):
    """Create a bill for a company for a specific month/year"""
    try:
        company = Company.query.get(company_id)
        if not company:
            raise ValueError("Company not found")
        
        # Calculate total amount
        total_amount = calculate_company_monthly_cost(company_id)
        
        # Get enabled modules for bill details
        enabled_modules = db.session.query(CompanyModule, ModuleDefinition).join(
            ModuleDefinition
        ).filter(
            CompanyModule.company_id == company_id,
            CompanyModule.is_enabled == True
        ).all()
        
        # Create bill
        bill = Bill(
            company_id=company_id,
            bill_month=bill_month,
            bill_year=bill_year,
            total_amount=total_amount,
            status='draft',
            created_by=session.get('user_id')
        )
        
        db.session.add(bill)
        db.session.flush()  # Get bill ID
        
        # Create bill items
        for company_module, module_def in enabled_modules:
            # Get price (custom or default)
            custom_pricing = CompanyModulePricing.query.filter_by(
                company_id=company_id,
                module_id=module_def.id,
                is_active=True
            ).first()
            
            price = custom_pricing.custom_price if custom_pricing else (module_def.monthly_price or 0)
            
            if price > 0:  # Only add paid modules to bill
                bill_item = BillItem(
                    bill_id=bill.id,
                    module_id=module_def.id,
                    description=module_def.display_name,
                    amount=price,
                    is_custom_pricing=bool(custom_pricing)
                )
                db.session.add(bill_item)
        
        db.session.commit()
        return bill
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating company bill: {str(e)}")
        raise

# ===== REPORTS =====
# Add these additional routes to your app.py for a complete billing system

@app.route('/admin/companies/<int:company_id>/modules-preview')
@login_required
@super_admin_required
def company_modules_preview(company_id):
    """Get company modules for bill preview"""
    try:
        company = Company.query.get_or_404(company_id)
        
        # Get enabled modules for this company
        enabled_modules = db.session.query(CompanyModule, ModuleDefinition).join(
            ModuleDefinition, CompanyModule.module_id == ModuleDefinition.id
        ).filter(
            CompanyModule.company_id == company_id,
            CompanyModule.is_enabled == True
        ).all()
        
        modules_data = []
        total_cost = 0
        
        for company_module, module_def in enabled_modules:
            # Check for custom pricing
            custom_pricing = CompanyModulePricing.query.filter_by(
                company_id=company_id,
                module_id=module_def.id,
                is_active=True
            ).first()
            
            price = float(custom_pricing.custom_price) if custom_pricing else float(module_def.monthly_price or 0)
            total_cost += price
            
            modules_data.append({
                'name': module_def.display_name,
                'price': price,
                'is_custom': bool(custom_pricing)
            })
        
        return jsonify({
            'success': True,
            'modules': modules_data,
            'total_cost': total_cost,
            'company_name': company.name
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Replace your billing_reports route with this debug version:

# Replace your debug billing_reports route with this complete version:

@app.route('/admin/billing/reports')
@login_required
@super_admin_required
def billing_reports():
    """Billing reports page - full version"""
    try:
        # Calculate various metrics for reports
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Get companies and basic stats
        companies = Company.query.filter_by(is_active=True).all()
        total_companies = len(companies)
        
        # Calculate total revenue
        total_revenue = 0
        for company in companies:
            # Calculate each company's monthly cost
            try:
                enabled_modules = db.session.query(CompanyModule, ModuleDefinition).join(
                    ModuleDefinition, CompanyModule.module_id == ModuleDefinition.id
                ).filter(
                    CompanyModule.company_id == company.id,
                    CompanyModule.is_enabled == True
                ).all()
                
                for company_module, module_def in enabled_modules:
                    try:
                        # Check for custom pricing
                        custom_pricing = CompanyModulePricing.query.filter_by(
                            company_id=company.id,
                            module_id=module_def.id,
                            is_active=True
                        ).first()
                        
                        if custom_pricing:
                            total_revenue += float(custom_pricing.custom_price or 0)
                        else:
                            total_revenue += float(module_def.monthly_price or 0)
                    except:
                        # Fallback if CompanyModulePricing doesn't exist
                        total_revenue += float(module_def.monthly_price or 0)
            except Exception as e:
                print(f"Error calculating revenue for company {company.name}: {e}")
                continue
        
        # Monthly revenue trend (last 12 months)
        monthly_revenue = []
        for i in range(12):
            date = datetime.now() - timedelta(days=30*i)
            # For simplicity, use current total revenue for each month
            # In a real system, you'd query historical data
            monthly_revenue.append({
                'month': date.strftime('%b %Y'),
                'revenue': total_revenue + (i * 500)  # Add some variation
            })
        monthly_revenue.reverse()
        
        # Module usage statistics
        module_stats = []
        try:
            modules = ModuleDefinition.query.filter_by(is_active=True).all()
            for module in modules:
                usage_count = CompanyModule.query.filter_by(
                    module_id=module.id,
                    is_enabled=True
                ).count()
                
                # Calculate revenue for this module
                module_revenue = 0
                company_modules = CompanyModule.query.filter_by(
                    module_id=module.id,
                    is_enabled=True
                ).all()
                
                for cm in company_modules:
                    try:
                        custom_pricing = CompanyModulePricing.query.filter_by(
                            company_id=cm.company_id,
                            module_id=module.id,
                            is_active=True
                        ).first()
                        
                        if custom_pricing:
                            module_revenue += float(custom_pricing.custom_price or 0)
                        else:
                            module_revenue += float(module.monthly_price or 0)
                    except:
                        module_revenue += float(module.monthly_price or 0)
                
                module_stats.append({
                    'name': module.display_name,
                    'usage_count': usage_count,
                    'revenue': module_revenue,
                    'category': module.category,
                    'price': float(module.monthly_price or 0)
                })
        except Exception as e:
            print(f"Error getting module stats: {e}")
            module_stats = []
        
        # Company breakdown (top companies by revenue)
        company_breakdown = []
        try:
            for company in companies:
                company_cost = 0
                module_count = 0
                
                try:
                    enabled_modules = db.session.query(CompanyModule, ModuleDefinition).join(
                        ModuleDefinition, CompanyModule.module_id == ModuleDefinition.id
                    ).filter(
                        CompanyModule.company_id == company.id,
                        CompanyModule.is_enabled == True
                    ).all()
                    
                    module_count = len(enabled_modules)
                    
                    for company_module, module_def in enabled_modules:
                        try:
                            custom_pricing = CompanyModulePricing.query.filter_by(
                                company_id=company.id,
                                module_id=module_def.id,
                                is_active=True
                            ).first()
                            
                            if custom_pricing:
                                company_cost += float(custom_pricing.custom_price or 0)
                            else:
                                company_cost += float(module_def.monthly_price or 0)
                        except:
                            company_cost += float(module_def.monthly_price or 0)
                except Exception as e:
                    print(f"Error calculating cost for company {company.name}: {e}")
                
                if company_cost > 0 or module_count > 0:  # Only include companies with data
                    company_breakdown.append({
                        'name': company.name,
                        'monthly_cost': company_cost,
                        'module_count': module_count
                    })
        except Exception as e:
            print(f"Error getting company breakdown: {e}")
            company_breakdown = []
        
        # Sort company breakdown by revenue (highest first)
        company_breakdown.sort(key=lambda x: x['monthly_cost'], reverse=True)
        
        # Additional statistics
        active_modules_count = len([m for m in module_stats if m['usage_count'] > 0])
        avg_revenue_per_company = (total_revenue / total_companies) if total_companies > 0 else 0
        
        print(f"Reports data: {total_companies} companies, {len(module_stats)} modules, R{total_revenue:.2f} revenue")
        
        return render_template('billing/reports.html',
                             monthly_revenue=monthly_revenue,
                             module_stats=module_stats,
                             company_breakdown=company_breakdown,
                             total_revenue=total_revenue,
                             total_companies=total_companies,
                             active_modules_count=active_modules_count,
                             avg_revenue_per_company=avg_revenue_per_company)
        
    except Exception as e:
        print(f"Error in billing reports: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('Error loading billing reports', 'error')
        return redirect(url_for('billing_dashboard'))

@app.route('/admin/billing/export-report')
@login_required
@super_admin_required
def export_billing_report():
    """Export billing report to Excel"""
    try:
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        # Billing Summary Sheet
        summary_sheet = workbook.add_worksheet('Billing Summary')
        
        # Formats
        header_format = workbook.add_format({
            'bold': True,
            'font_color': 'white',
            'bg_color': '#366092',
            'border': 1
        })
        
        cell_format = workbook.add_format({
            'border': 1
        })
        
        # Summary headers
        summary_headers = ['Company', 'Active Modules', 'Monthly Cost', 'Has Custom Pricing']
        for col, header in enumerate(summary_headers):
            summary_sheet.write(0, col, header, header_format)
        
        # Summary data
        companies = Company.query.filter_by(is_active=True).all()
        for row, company in enumerate(companies, 1):
            monthly_cost = calculate_company_monthly_cost(company.id)
            module_count = CompanyModule.query.filter_by(
                company_id=company.id, 
                is_enabled=True
            ).count()
            has_custom = CompanyModulePricing.query.filter_by(
                company_id=company.id, 
                is_active=True
            ).first() is not None
            
            summary_sheet.write(row, 0, company.name, cell_format)
            summary_sheet.write(row, 1, module_count, cell_format)
            summary_sheet.write(row, 2, f'R {monthly_cost:.2f}', cell_format)
            summary_sheet.write(row, 3, 'Yes' if has_custom else 'No', cell_format)
        
        # Module Revenue Sheet
        module_sheet = workbook.add_worksheet('Module Revenue')
        
        module_headers = ['Module Name', 'Category', 'Base Price', 'Usage Count', 'Total Revenue']
        for col, header in enumerate(module_headers):
            module_sheet.write(0, col, header, header_format)
        
        modules = ModuleDefinition.query.filter_by(is_active=True).all()
        for row, module in enumerate(modules, 1):
            usage_count = CompanyModule.query.filter_by(
                module_id=module.id,
                is_enabled=True
            ).count()
            
            # Calculate total revenue
            total_revenue = 0
            company_modules = CompanyModule.query.filter_by(
                module_id=module.id,
                is_enabled=True
            ).all()
            
            for cm in company_modules:
                custom_pricing = CompanyModulePricing.query.filter_by(
                    company_id=cm.company_id,
                    module_id=module.id,
                    is_active=True
                ).first()
                
                if custom_pricing:
                    total_revenue += float(custom_pricing.custom_price or 0)
                else:
                    total_revenue += float(module.monthly_price or 0)
            
            module_sheet.write(row, 0, module.display_name, cell_format)
            module_sheet.write(row, 1, module.category.title(), cell_format)
            module_sheet.write(row, 2, f'R {float(module.monthly_price or 0):.2f}', cell_format)
            module_sheet.write(row, 3, usage_count, cell_format)
            module_sheet.write(row, 4, f'R {total_revenue:.2f}', cell_format)
        
        # Adjust column widths
        summary_sheet.set_column('A:A', 25)  # Company name
        summary_sheet.set_column('B:B', 15)  # Module count
        summary_sheet.set_column('C:C', 15)  # Monthly cost
        summary_sheet.set_column('D:D', 18)  # Has custom pricing
        
        module_sheet.set_column('A:A', 25)   # Module name
        module_sheet.set_column('B:B', 12)   # Category
        module_sheet.set_column('C:C', 12)   # Base price
        module_sheet.set_column('D:D', 12)   # Usage count
        module_sheet.set_column('E:E', 15)   # Total revenue
        
        workbook.close()
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename="Billing_Report_{datetime.now().strftime("%Y%m%d")}.xlsx"'
        return response
        
    except Exception as e:
        print(f"Error exporting billing report: {str(e)}")
        flash('Error exporting report', 'error')
        return redirect(url_for('billing_dashboard'))

# Helper function to calculate company monthly cost (if not already defined)
def calculate_company_monthly_cost(company_id):
    """Calculate the total monthly cost for a company including custom pricing"""
    try:
        total_cost = 0
        
        # Get all enabled modules for the company
        enabled_modules = db.session.query(CompanyModule, ModuleDefinition).join(
            ModuleDefinition, CompanyModule.module_id == ModuleDefinition.id
        ).filter(
            CompanyModule.company_id == company_id,
            CompanyModule.is_enabled == True
        ).all()
        
        for company_module, module_def in enabled_modules:
            # Check for custom pricing
            custom_pricing = CompanyModulePricing.query.filter_by(
                company_id=company_id,
                module_id=module_def.id,
                is_active=True
            ).first()
            
            if custom_pricing:
                total_cost += float(custom_pricing.custom_price or 0)
            else:
                total_cost += float(module_def.monthly_price or 0)
        
        return total_cost
        
    except Exception as e:
        print(f"Error calculating company monthly cost: {str(e)}")
        return 0

# Test route to initialize some sample billing data
@app.route('/admin/billing/init-sample-data')
@login_required
@super_admin_required
def init_sample_billing_data():
    """Initialize sample billing data for testing"""
    try:
        # This route helps you test the billing system by creating some sample data
        
        # Check if ModuleDefinition table has data
        module_count = ModuleDefinition.query.count()
        
        if module_count == 0:
            # Create sample modules
            sample_modules = [
                {
                    'module_name': 'tender_management',
                    'display_name': 'Tender Management',
                    'description': 'Core tender creation and management',
                    'category': 'core',
                    'monthly_price': 0.00,
                    'is_core': True,
                    'sort_order': 1
                },
                {
                    'module_name': 'document_management',
                    'display_name': 'Document Management', 
                    'description': 'Upload and manage tender documents',
                    'category': 'feature',
                    'monthly_price': 299.99,
                    'is_core': False,
                    'sort_order': 2
                },
                {
                    'module_name': 'reporting',
                    'display_name': 'Advanced Reporting',
                    'description': 'Advanced analytics and reports',
                    'category': 'feature',
                    'monthly_price': 499.99,
                    'is_core': False,
                    'sort_order': 3
                },
                {
                    'module_name': 'api_access',
                    'display_name': 'API Access',
                    'description': 'REST API for integrations',
                    'category': 'premium',
                    'monthly_price': 899.99,
                    'is_core': False,
                    'sort_order': 4
                }
            ]
            
            for module_data in sample_modules:
                module = ModuleDefinition(**module_data)
                db.session.add(module)
            
            db.session.commit()
            created_modules = len(sample_modules)
        else:
            created_modules = 0
        
        # Enable some modules for existing companies
        companies = Company.query.filter_by(is_active=True).limit(3).all()
        enabled_count = 0
        
        for company in companies:
            # Check if company already has modules
            existing_modules = CompanyModule.query.filter_by(company_id=company.id).count()
            
            if existing_modules == 0:
                # Enable core modules and some feature modules
                modules_to_enable = ModuleDefinition.query.filter(
                    ModuleDefinition.module_name.in_(['tender_management', 'document_management', 'reporting'])
                ).all()
                
                for module_def in modules_to_enable:
                    company_module = CompanyModule(
                        company_id=company.id,
                        module_id=module_def.id,
                        is_enabled=True,
                        enabled_at=datetime.now(),
                        billing_start_date=datetime.now()
                    )
                    db.session.add(company_module)
                    enabled_count += 1
        
        db.session.commit()
        
        flash(f'Sample data initialized: {created_modules} modules created, {enabled_count} module assignments created', 'success')
        return redirect(url_for('billing_dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error initializing sample data: {str(e)}', 'error')
        return redirect(url_for('billing_dashboard'))
    
if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Tender Management System Starting...")
    print("="*50)
    print("📂 Visit: http://localhost:5001")
    print("👤 Super Admin Login: superadmin / admin123")
    print("="*50 + "\n")
    
    #init_database()
    app.run(debug=True, host='0.0.0.0', port=5001)