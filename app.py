from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from functools import wraps
import os
import pymysql
pymysql.install_as_MySQLdb()
from datetime import datetime, timedelta
from flask_migrate import Migrate
from werkzeug.utils import secure_filename

from datetime import datetime
from zoneinfo import ZoneInfo
import tzlocal  # optional helper to get local timezone name, install with: pip install tzlocal
from services.company_module_service import CompanyModuleService, require_company_module


# In app.py, instead of:
from services import AuthService

# Use:
from services import AuthService  # This will import from your original services.py file
from services.module_service import ModuleService
# Import our modules
from config import Config
from models import db, User, Company, Role, Tender, TenderCategory, TenderStatus, TenderDocument, DocumentType, CustomField, TenderNote, TenderHistory
from services import (
    AuthService, CompanyService, RoleService, TenantService,
    TenderService, TenderCategoryService, TenderStatusService, 
    DocumentTypeService, TenderDocumentService, CustomFieldService, TenderHistoryService
)

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

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    user = AuthService.get_user_by_id(session['user_id'])
    
    # Get additional context based on user role
    context = {'user': user}
    
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
        
    elif user.company_id and user.role.name == 'Company Admin':
        # Company admin stats - use direct queries
        user_count = User.query.filter_by(company_id=user.company_id, is_active=True).count()
        tender_count = Tender.query.filter_by(company_id=user.company_id).count()
        
        context['company_stats'] = {
            'user_count': user_count,
            'tender_count': tender_count
        }
        
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
def tenders():
    """View tenders with simple pagination"""
    user = AuthService.get_user_by_id(session['user_id'])
    
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
                         per_page=per_page)

@app.route('/tenders/create', methods=['GET', 'POST'])
@login_required
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
def view_tender(tender_id):
    """View tender details with notes"""
    user = AuthService.get_user_by_id(session['user_id'])
    tender = TenderService.get_tender_by_id(tender_id)
    
    if not tender:
        flash('Tender not found.', 'error')
        return redirect(url_for('tenders'))
    
    # Check access permissions
    if not user.is_super_admin and tender.company_id != user.company_id:
        flash('Access denied.', 'error')
        return redirect(url_for('tenders'))
    
    # Get tender documents
    documents = TenderDocumentService.get_tender_documents(tender_id)
    document_types = DocumentTypeService.get_all_document_types()
    custom_fields = CustomFieldService.get_all_custom_fields()
    
    # Get tender notes ordered by creation date (newest first)
    tender_notes = TenderNote.query.filter_by(tender_id=tender_id).order_by(TenderNote.created_at.desc()).all()
    
    # Get tender history
    tender_history = TenderHistoryService.get_tender_history(tender_id)

    return render_template('tenders/view.html', 
                         tender=tender, 
                         documents=documents,
                         document_types=document_types,
                         custom_fields=custom_fields,
                         tender_notes=tender_notes,
                         tender_history=tender_history,
                         current_user=user)  # Pass current user for template

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
        
        # Log note addition
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
    else:
        flash(message, 'error')
    
    TenderHistoryService.log_document_uploaded(
        tender_id=tender_id,
        performed_by_id=user.id,
        document_name=document.original_filename,
        document_type=document.doc_type.name,
       
    )
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
@app.route('/admin/companies')
@super_admin_required
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
    
    return render_template('admin/create_company.html', available_modules=all_modules)



@app.route('/admin/companies/<int:company_id>/edit', methods=['GET', 'POST'])
@super_admin_required
def edit_company(company_id):
    """Edit company details and manage modules"""
    # Get company directly from database
    company = Company.query.get_or_404(company_id)
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            address = request.form.get('address', '').strip()
            is_active = 'is_active' in request.form
            
            # Validation
            if not name or not email:
                flash('Company name and email are required', 'error')
                return redirect(url_for('edit_company', company_id=company_id))
            
            # Check if email is taken by another company
            existing_company = Company.query.filter(
                Company.email == email,
                Company.id != company_id
            ).first()
            
            if existing_company:
                flash('Email already exists for another company', 'error')
                return redirect(url_for('edit_company', company_id=company_id))
            
            # Update company
            company.name = name
            company.email = email
            company.phone = phone if phone else None
            company.address = address if address else None
            company.is_active = is_active
            
            db.session.commit()
            flash('Company updated successfully!', 'success')
            return redirect(url_for('admin_companies'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating company: {str(e)}', 'error')
    
    # GET request - show the form
    # Get company stats
    user_count = User.query.filter_by(company_id=company_id, is_active=True).count()
    tender_count = Tender.query.filter_by(company_id=company_id).count()
    
    company_stats = type('CompanyStats', (), {
        'user_count': user_count,
        'tender_count': tender_count
    })()
    
    # Define available modules (you can move this to a database table later)
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
            'monthly_price': 499.99,  # ~R500/month
            'is_core': False
        },
        {
            'module_name': 'notifications',
            'display_name': 'Email Notifications',
            'description': 'Automated email notifications and alerts',
            'category': 'feature', 
            'monthly_price': 179.99,  # ~R180/month
            'is_core': False
        },
        {
            'module_name': 'api_access',
            'display_name': 'API Access',
            'description': 'REST API for third-party integrations',
            'category': 'premium',
            'monthly_price': 899.99,  # ~R900/month
            'is_core': False
        },
        {
            'module_name': 'white_label',
            'display_name': 'White Label Branding',
            'description': 'Custom branding and white-label options',
            'category': 'premium',
            'monthly_price': 1799.99,  # ~R1800/month
            'is_core': False
        }
    ]
    
    # Get currently enabled modules (from database or default)
    enabled_modules = get_company_enabled_modules(company_id)
    
    # Prepare modules data for template
    modules_data = []
    monthly_cost = 0.0
    enabled_count = 0
    
    for module in available_modules:
        is_enabled = module['module_name'] in enabled_modules or module['is_core']
        
        module_data = type('ModuleData', (), {
            'definition': type('ModuleDef', (), module)(),
            'is_enabled': is_enabled,
            'company_module': type('CompanyModule', (), {
                'enabled_at': datetime.now()
            })() if is_enabled else None
        })()
        
        modules_data.append(module_data)
        
        if is_enabled:
            enabled_count += 1
            monthly_cost += module['monthly_price']
    
    return render_template('admin/edit_company.html',
                         company=company,
                         company_stats=company_stats,
                         modules_data=modules_data,
                         enabled_count=enabled_count,
                         total_modules=len(available_modules),
                         monthly_cost=monthly_cost)

def get_company_enabled_modules(company_id):
    """Get list of enabled modules for a company"""
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

@app.route('/admin/companies/<int:company_id>/modules/batch-update', methods=['POST'])
@super_admin_required
def update_company_modules(company_id):
    """Update company module settings"""
    try:
        company = Company.query.get_or_404(company_id)
        data = request.get_json()
        changes = data.get('changes', [])
        
        # Simple storage - you can implement proper database storage later
        # For now, we'll store in a simple way or just return success
        
        # Calculate new monthly cost
        module_prices = {
            'tender_management': 0.0,
            'user_management': 0.0,
            'analytics': 29.99,
            'notifications': 9.99,
            'api_access': 49.99,
            'white_label': 99.99
        }
        
        monthly_cost = 0.0
        for change in changes:
            if change.get('enabled'):
                module_name = change.get('module_name')
                monthly_cost += module_prices.get(module_name, 0.0)
        
        # Always include core modules
        monthly_cost += module_prices.get('tender_management', 0.0)
        monthly_cost += module_prices.get('user_management', 0.0)
        
        return jsonify({
            'success': True,
            'message': 'Modules updated successfully',
            'monthly_cost': monthly_cost
        })
        
    except Exception as e:
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

@app.route('/admin/companies/<int:company_id>/view')
@super_admin_required
def view_company(company_id):
    """Admin - View company details"""
    company = CompanyService.get_company_by_id(company_id)
    if not company:
        flash('Company not found.', 'error')
        return redirect(url_for('admin_companies'))
    
    users = AuthService.get_users_by_company(company_id)
    stats = CompanyService.get_company_stats(company_id)
    
    return render_template('admin/view_company.html', 
                         company=company, users=users, stats=stats)

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
def admin_users():
    """Admin - Manage users"""
    users = AuthService.get_all_users()
    return render_template('admin/users.html', users=users)

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
@super_admin_required
def admin_roles():
    """Admin - Manage roles"""
    roles = RoleService.get_all_roles()
    return render_template('admin/roles.html', roles=roles)

# Company Admin Routes (keeping existing ones)
@app.route('/company/users')
@company_admin_required
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
   
if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Tender Management System Starting...")
    print("="*50)
    print("📂 Visit: http://localhost:5001")
    print("👤 Super Admin Login: superadmin / admin123")
    print("="*50 + "\n")
    
    #init_database()
    app.run(debug=True, host='0.0.0.0', port=5001)