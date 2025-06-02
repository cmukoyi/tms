from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from functools import wraps
import os
import pymysql
pymysql.install_as_MySQLdb()
from datetime import datetime, timedelta
from flask_migrate import Migrate


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



# Initialize Flask app
app = Flask(__name__)

app.config.from_object(Config)

@app.context_processor
def inject_year():
    from datetime import datetime
    return dict(current_year=datetime.now().year)

# Initialize database
db.init_app(app)

migrate = Migrate(app, db)


# Decorators (keeping existing ones)
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

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    user = AuthService.get_user_by_id(session['user_id'])
    
    # Get additional context based on user role
    context = {'user': user}
    
    if user.is_super_admin:
        context['total_companies'] = len(CompanyService.get_all_companies())
        context['total_users'] = len(AuthService.get_all_users())
        context['tender_stats'] = TenderService.get_tender_stats()
    elif user.company_id and user.role.name == 'Company Admin':
        context['company_stats'] = CompanyService.get_company_stats(user.company_id)
        context['company_users'] = AuthService.get_users_by_company(user.company_id)
        context['tender_stats'] = TenderService.get_tender_stats(user.company_id)
    
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

@app.route('/documents/<int:document_id>/download')
@login_required
def download_document(document_id):
    """Download tender document"""
    user = AuthService.get_user_by_id(session['user_id'])
    document = TenderDocument.query.get(document_id)
    
    if not document:
        flash('Document not found.', 'error')
        return redirect(url_for('tenders'))
    
    # Check access permissions
    tender = document.tender
    if not user.is_super_admin and tender.company_id != user.company_id:
        flash('Access denied.', 'error')
        return redirect(url_for('tenders'))
    
    try:
        return send_file(document.file_path, 
                        as_attachment=True, 
                        download_name=document.original_filename)
    except FileNotFoundError:
        flash('File not found on server.', 'error')
        return redirect(url_for('view_tender', tender_id=tender.id))

@app.route('/documents/<int:document_id>/delete', methods=['POST'])
@login_required
def delete_document(document_id):
    """Delete tender document"""
    user = AuthService.get_user_by_id(session['user_id'])
    document = TenderDocument.query.get(document_id)
    
    if not document:
        flash('Document not found.', 'error')
        return redirect(url_for('tenders'))
    
    tender = document.tender
    
    # Check access permissions
    if not user.is_super_admin and tender.company_id != user.company_id:
        flash('Access denied.', 'error')
        return redirect(url_for('tenders'))
    
    success, message = TenderDocumentService.delete_document(document_id)
    if success:
        flash(message, 'success')
        # Log document deletion
        TenderHistoryService.log_document_deleted(
            tender_id=tender.id,
            performed_by_id=user.id,
            document_name=document.original_filename
            
        )
    else:
        flash(message, 'error')
        # Log document deletion failure
        TenderHistoryService.log_document_deletion_failed(
            tender_id=tender.id,
            performed_by_id=user.id,
            document_name=document.original_filename
           
        )
    
    return redirect(url_for('view_tender', tender_id=tender.id))

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
    companies = CompanyService.get_all_companies()
    
    # Add stats for each company
    for company in companies:
        company.stats = CompanyService.get_company_stats(company.id)
    
    return render_template('admin/companies.html', companies=companies)

@app.route('/admin/companies/create', methods=['GET', 'POST'])
@super_admin_required
def create_company():
    """Admin - Create new company with admin user"""
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
        
        if not name or not email:
            flash('Company name and email are required.', 'error')
            return render_template('admin/create_company.html')
        
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
            flash(message, 'success')
            flash(f'Company Admin created - Username: {admin_info["username"]}, Password: {admin_info["password"]}', 'info')
            flash('⚠️ Please save the admin credentials and share them securely with the company admin!', 'warning')
            return redirect(url_for('admin_companies'))
        else:
            flash(message, 'error')
    
    return render_template('admin/create_company.html')

@app.route('/admin/companies/<int:company_id>/edit', methods=['GET', 'POST'])
@super_admin_required
def edit_company(company_id):
    """Admin - Edit company details"""
    company = CompanyService.get_company_by_id(company_id)
    if not company:
        flash('Company not found.', 'error')
        return redirect(url_for('admin_companies'))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        is_active = 'is_active' in request.form
        
        if not name or not email:
            flash('Company name and email are required.', 'error')
            return render_template('admin/edit_company.html', company=company)
        
        # Update company
        success, message = CompanyService.update_company(
            company_id=company_id,
            name=name,
            email=email,
            phone=phone if phone else None,
            address=address if address else None,
            is_active=is_active
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('admin_companies'))
        else:
            flash(message, 'error')
    
    return render_template('admin/edit_company.html', company=company)

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

@app.route('/admin/companies/<int:company_id>/users')
@super_admin_required
def view_company_users(company_id):
    company = CompanyService.get_company_by_id(company_id)
    if not company:
        flash('Company not found.', 'error')
        return redirect(url_for('admin_companies'))
    
    users = AuthService.get_users_by_company(company_id)
    return render_template('admin/users.html', users=users, company=company)

def init_database():
    """Initialize database with default data"""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create default roles
        success, message = RoleService.create_default_roles()
        if success:
            print("✓ Default roles created")
        else:
            print(f"✗ Error creating roles: {message}")
        
        # Create default tender categories
        success, message = TenderCategoryService.create_default_categories()
        if success:
            print("✓ Default tender categories created")
        else:
            print(f"✗ Error creating categories: {message}")
        
        # Create default tender statuses
        success, message = TenderStatusService.create_default_statuses()
        if success:
            print("✓ Default tender statuses created")
        else:
            print(f"✗ Error creating statuses: {message}")
        
        # Create default document types
        success, message = DocumentTypeService.create_default_document_types()
        if success:
            print("✓ Default document types created")
        else:
            print(f"✗ Error creating document types: {message}")
        
        # Create super admin if doesn't exist
        if not User.query.filter_by(is_super_admin=True).first():
            super_admin_role = RoleService.get_role_by_name('Super Admin')
            if super_admin_role:
                super_admin, message = AuthService.create_user(
                    username='superadmin',
                    email='admin@system.com',
                    password='admin123',  # Change this in production!
                    first_name='Super',
                    last_name='Admin',
                    company_id=None,
                    role_id=super_admin_role.id,
                    is_super_admin=True
                )
                
                if super_admin:
                    print("✓ Super admin created successfully")
                    print("  Username: superadmin")
                    print("  Password: admin123")
                    print("  ⚠️  CHANGE THE DEFAULT PASSWORD IN PRODUCTION!")
                else:
                    print(f"✗ Error creating super admin: {message}")
            else:
                print("✗ Super Admin role not found")
        else:
            print("✓ Super admin already exists")

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Tender Management System Starting...")
    print("="*50)
    print("📂 Visit: http://localhost:5001")
    print("👤 Super Admin Login: superadmin / admin123")
    print("="*50 + "\n")
    
    init_database()
    app.run(debug=True, host='0.0.0.0', port=5001)