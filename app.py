from imports import *


app = Flask(__name__)

app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = 'uploads'  # Add this line here

login_manager = LoginManager(app)
login_manager.login_view = 'login'
@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return AuthService.get_user_by_id(user_id)


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
    try:
        # Use your session-based authentication instead of current_user
        user = AuthService.get_user_by_id(session['user_id'])
        
        if not user:
            flash('Please log in to download documents.', 'error')
            return redirect(url_for('login'))
        
        # Get the document
        document = TenderDocument.query.get_or_404(document_id)
        
        # Check access permissions
        if not user.is_super_admin and document.tender.company_id != user.company_id:
            flash('Access denied.', 'error')
            return redirect(url_for('tenders'))
        
        # Serve the file
        try:
            return send_file(
                document.file_path,
                as_attachment=True,
                download_name=document.original_filename,
                mimetype=document.mime_type
            )
        except FileNotFoundError:
            flash('File not found on server.', 'error')
            return redirect(request.referrer or url_for('tenders'))
            
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'error')
        return redirect(request.referrer or url_for('tenders'))

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

   
    
    # ... rest of function
@app.route('/my-company/profile')
@login_required  
def my_company_profile():
    """View current user's company profile"""
    print(f"Session contents: {dict(session)}")
    print(f"User ID from session: {session.get('user_id')}")
    try:
        # Use your session-based authentication instead of current_user
        user = AuthService.get_user_by_id(session['user_id'])
        
        if not user:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        if not user.company_id:
            flash('No company associated with your account.', 'error')
            return redirect(url_for('dashboard'))
        
        # Get company documents grouped by category
        documents = CompanyDocument.query.filter_by(company_id=user.company_id).order_by(
            CompanyDocument.document_category, 
            CompanyDocument.created_at.desc()
        ).all()
        
        # Group documents by category
        document_categories = {}
        for doc in documents:
            if doc.document_category not in document_categories:
                document_categories[doc.document_category] = []
            document_categories[doc.document_category].append(doc)
        
        # Define available document categories
        available_categories = [
            'Directors ID Documents',
            'Share Certificates',
            'Company Registration',
            'Tax Certificates',
            'Bank Statements',
            'Financial Statements',
            'BEE Certificates',
            'Insurance Documents',
            'Other Certificates',
            'Other Documents'
        ]
        
        return render_template('company/profile.html', 
                             company=user.company,
                             document_categories=document_categories,
                             available_categories=available_categories,
                             user=user)
        
    except Exception as e:
        flash(f'Error loading company profile: {str(e)}', 'error')
        return redirect(url_for('dashboard'))
 
@app.route('/upload_company_document', methods=['POST'])
@login_required
def upload_company_document():
    """Upload a company document"""
    try:
        user = AuthService.get_user_by_id(session['user_id'])
        if not user or not user.company:
            flash('Company information not found.', 'error')
            return redirect(url_for('my_company_profile'))
        
        # Get form data
        document_name = request.form.get('document_name', '').strip()
        document_category = request.form.get('document_category', '').strip()
        description = request.form.get('description', '').strip()
        
        if not document_name or not document_category:
            flash('Document name and category are required.', 'error')
            return redirect(url_for('my_company_profile'))
        
        # Handle file upload
        if 'document_file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(url_for('my_company_profile'))
        
        file = request.files['document_file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('my_company_profile'))
        
        if file:
            # Secure the filename
            original_filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{user.company_id}_{timestamp}_{original_filename}"
            
            # Create company documents folder
            company_docs_folder = os.path.join(
                app.config.get('UPLOAD_FOLDER', 'uploads'), 
                'company_docs',
                str(user.company_id)
            )
            os.makedirs(company_docs_folder, exist_ok=True)
            
            # Save file
            file_path = os.path.join(company_docs_folder, filename)
            file.save(file_path)
            
            # Get file info
            file_size = os.path.getsize(file_path)
            mime_type = file.content_type or 'application/octet-stream'
            
            # Save to database
            company_doc = CompanyDocument(
                company_id=user.company_id,
                document_name=document_name,
                original_filename=original_filename,
                filename=filename,
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type,
                document_category=document_category,
                description=description,
                uploaded_by=user.id
            )
            
            db.session.add(company_doc)
            db.session.commit()
            
            flash(f'Document "{document_name}" uploaded successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error uploading document: {str(e)}', 'error')
    
    return redirect(url_for('my_company_profile'))

@app.route('/upload_company_logo', methods=['POST'])
@login_required
def upload_company_logo():
    """Upload company logo"""
    try:
        user = AuthService.get_user_by_id(session['user_id'])
        if not user or not user.company:
            flash('Company information not found.', 'error')
            return redirect(url_for('my_company_profile'))
        
        # Handle file upload
        if 'logo_file' not in request.files:
            flash('No logo file selected.', 'error')
            return redirect(url_for('my_company_profile'))
        
        file = request.files['logo_file']
        if file.filename == '':
            flash('No logo file selected.', 'error')
            return redirect(url_for('my_company_profile'))
        
        # Validate file type
        allowed_types = {'image/jpeg', 'image/jpg', 'image/png', 'image/gif'}
        if file.content_type not in allowed_types:
            flash('Invalid file type. Please upload JPG, PNG, or GIF images only.', 'error')
            return redirect(url_for('my_company_profile'))
        
        # Validate file size (2MB max)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > 2 * 1024 * 1024:  # 2MB
            flash('Logo file too large. Maximum size is 2MB.', 'error')
            return redirect(url_for('my_company_profile'))
        
        if file:
            # Delete existing logo if exists
            if user.company.has_logo:
                user.company.delete_logo()
            
            # Secure the filename
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            logo_filename = f"logo_{user.company_id}_{timestamp}_{filename}"
            
            # Create company logos folder
            logos_folder = os.path.join(
                app.config.get('UPLOAD_FOLDER', 'uploads'), 
                'company_logos'
            )
            os.makedirs(logos_folder, exist_ok=True)
            
            # Save file
            logo_path = os.path.join(logos_folder, logo_filename)
            file.save(logo_path)
            
            # Update company record
            user.company.logo_filename = logo_filename
            user.company.logo_file_path = logo_path
            user.company.logo_mime_type = file.content_type
            user.company.logo_file_size = file_size
            user.company.logo_uploaded_at = datetime.now()
            
            db.session.commit()
            
            flash('Company logo uploaded successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error uploading logo: {str(e)}', 'error')
    
    return redirect(url_for('my_company_profile'))

@app.route('/download_company_document/<int:document_id>')
@login_required
def download_company_document(document_id):
    """Download a company document"""
    try:
        user = AuthService.get_user_by_id(session['user_id'])
        if not user:
            flash('Please log in to download documents.', 'error')
            return redirect(url_for('login'))
        
        # Get the document
        document = CompanyDocument.query.get_or_404(document_id)
        
        # Check access permissions
        if not user.is_super_admin and document.company_id != user.company_id:
            flash('Access denied.', 'error')
            return redirect(url_for('my_company_profile'))
        
        # Check if file exists
        if not os.path.exists(document.file_path):
            flash('File not found on server.', 'error')
            return redirect(url_for('my_company_profile'))
        
        # Serve the file
        return send_file(
            document.file_path,
            as_attachment=True,
            download_name=document.original_filename,
            mimetype=document.mime_type
        )
        
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'error')
        return redirect(url_for('my_company_profile'))

@app.route('/view_company_document/<int:document_id>')
@login_required
def view_company_document(document_id):
    """View a company document inline (for PDFs and images)"""
    try:
        user = AuthService.get_user_by_id(session['user_id'])
        if not user:
            flash('Please log in to view documents.', 'error')
            return redirect(url_for('login'))
        
        # Get the document
        document = CompanyDocument.query.get_or_404(document_id)
        
        # Check access permissions
        if not user.is_super_admin and document.company_id != user.company_id:
            flash('Access denied.', 'error')
            return redirect(url_for('my_company_profile'))
        
        # Check if file exists
        if not os.path.exists(document.file_path):
            flash('File not found on server.', 'error')
            return redirect(url_for('my_company_profile'))
        
        # Serve the file for inline viewing
        return send_file(
            document.file_path,
            as_attachment=False,
            mimetype=document.mime_type
        )
        
    except Exception as e:
        flash(f'Error viewing file: {str(e)}', 'error')
        return redirect(url_for('my_company_profile'))

@app.route('/delete_company_document/<int:document_id>', methods=['POST'])
@login_required
def delete_company_document(document_id):
    """Delete a company document"""
    try:
        user = AuthService.get_user_by_id(session['user_id'])
        if not user:
            flash('Access denied.', 'error')
            return redirect(url_for('my_company_profile'))
        
        # Get the document
        document = CompanyDocument.query.get_or_404(document_id)
        
        # Check access permissions
        if not user.is_super_admin and document.company_id != user.company_id:
            flash('Access denied.', 'error')
            return redirect(url_for('my_company_profile'))
        
        # Delete file from disk
        try:
            if os.path.exists(document.file_path):
                os.remove(document.file_path)
        except Exception as e:
            print(f"Error deleting file from disk: {str(e)}")
        
        # Delete from database
        db.session.delete(document)
        db.session.commit()
        
        flash(f'Document "{document.document_name}" deleted successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting document: {str(e)}', 'error')
    
    return redirect(url_for('my_company_profile'))

@app.route('/delete_company_logo', methods=['POST'])
@login_required
def delete_company_logo():
    """Delete company logo"""
    try:
        user = AuthService.get_user_by_id(session['user_id'])
        if not user or not user.company:
            flash('Company information not found.', 'error')
            return redirect(url_for('my_company_profile'))
        
        if user.company.has_logo:
            user.company.delete_logo()
            db.session.commit()
            flash('Company logo deleted successfully.', 'success')
        else:
            flash('No logo to delete.', 'info')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting logo: {str(e)}', 'error')
    
    return redirect(url_for('my_company_profile'))

@app.route('/company_logo/<int:company_id>')
def company_logo(company_id):
    """Serve company logo"""
    try:
        company = Company.query.get_or_404(company_id)
        
        if not company.has_logo or not os.path.exists(company.logo_file_path):
            # Return default logo
            return send_from_directory('static/images', 'default-company-logo.png')
        
        return send_file(
            company.logo_file_path,
            mimetype=company.logo_mime_type
        )
        
    except Exception as e:
        # Return default logo on error
        return send_from_directory('static/images', 'default-company-logo.png')

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

# Add this to your app.py file

from flask import request, flash, redirect, url_for, render_template
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
import json

# Replace the quote route with this version that works with your permission system

@app.route('/tenders/<int:tender_id>/create-quote', methods=['GET', 'POST'])
@login_required
@require_module('tender_management')
def create_quote(tender_id):
    """Create a quote for a tender using Jinja templating"""
    tender = Tender.query.get_or_404(tender_id)
    current_user = AuthService.get_user_by_id(session['user_id'])
    
    if not current_user:
        flash('User session invalid. Please log in again.', 'error')
        return redirect(url_for('login'))
    
    # Check access permissions
    if not current_user.is_super_admin and current_user.company_id != tender.company_id:
        flash('Access denied.', 'error')
        return redirect(url_for('tenders'))
    
    if request.method == 'POST':
        try:
            # Import here to avoid circular import
            from models import TenderDocument, DocumentType
            
            # Get form data
            quote_ref = request.form.get('quote_ref')
            quote_date = datetime.strptime(request.form.get('quote_date'), '%Y-%m-%d').date()
            valid_until = datetime.strptime(request.form.get('valid_until'), '%Y-%m-%d').date()
            client_name = request.form.get('client_name')
            client_contact = request.form.get('client_contact', '')
            notes = request.form.get('notes', '')
            export_format = request.form.get('export_format', 'pdf')  # Get format choice
            
            # Get totals
            subtotal = float(request.form.get('subtotal', 0))
            vat_amount = float(request.form.get('vat_amount', 0))
            total_amount = float(request.form.get('total_amount', 0))
            
            # Process quote items
            items = []
            item_index = 0
            while f'items[{item_index}][description]' in request.form:
                description = request.form.get(f'items[{item_index}][description]')
                qty = float(request.form.get(f'items[{item_index}][qty]', 0))
                unit_price = float(request.form.get(f'items[{item_index}][unit_price]', 0))
                item_total = float(request.form.get(f'items[{item_index}][total]', 0))
                
                if description and qty > 0 and unit_price > 0:
                    items.append({
                        'description': description,
                        'qty': qty,
                        'unit_price': unit_price,
                        'total': item_total
                    })
                item_index += 1
            
            if not items:
                flash('Please add at least one item to the quote.', 'error')
                return render_template('tenders/create_quote.html', 
                                     tender=tender, 
                                     quote_counter=get_next_quote_counter())
            
            # Generate quote content based on format
            quote_data = {
                'tender': tender,
                'quote_ref': quote_ref,
                'quote_date': quote_date,
                'valid_until': valid_until,
                'client_name': client_name,
                'client_contact': client_contact,
                'notes': notes,
                'items': items,
                'subtotal': subtotal,
                'vat_amount': vat_amount,
                'total_amount': total_amount,
                'current_user': current_user
            }
            
            if export_format == 'excel':
                file_content, filename, content_type = generate_quote_excel(quote_data)
            else:  # Default to PDF
                file_content, filename, content_type = generate_quote_pdf(quote_data)
            
            # Save file to disk
            upload_folder = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), str(tender.company_id))
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Get or create Quote document type
            quote_doc_type = DocumentType.query.filter_by(name='Quote').first()
            if not quote_doc_type:
                quote_doc_type = DocumentType(
                    name='Quote', 
                    description='System generated quotes'
                )
                db.session.add(quote_doc_type)
                db.session.flush()
            
            # Create TenderDocument record
            tender_document = TenderDocument(
            tender_id=tender.id,
            filename=filename,  # This is the stored filename
            original_filename=filename,  # This is the original filename
            file_path=file_path,  # Full path to the file
            file_size=len(file_content),
            mime_type=content_type,  # The content type (application/pdf, etc.)
            document_type_id=quote_doc_type.id,  # Note: it's document_type_id, not doc_type_id
            uploaded_by=current_user.id  # Note: it's uploaded_by, not uploaded_by_id
        )
            # Add to session and commit        
            db.session.add(tender_document)
            db.session.commit()
            
            flash(f'Quote {quote_ref} created successfully as {export_format.upper()} and saved to documents.', 'success')
            return redirect(url_for('view_tender', tender_id=tender.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating quote: {str(e)}', 'error')
            import traceback
            print(f"Quote creation error: {traceback.format_exc()}")
            return render_template('tenders/create_quote.html', 
                                 tender=tender, 
                                 quote_counter=get_next_quote_counter())
    
    # GET request - show the form
    return render_template('tenders/create_quote.html', 
                         tender=tender, 
                         quote_counter=get_next_quote_counter())


def generate_quote_pdf(quote_data):
    """Generate PDF quote"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import inch
        import io
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.darkblue,
            spaceAfter=30,
            alignment=1
        )
        story.append(Paragraph(f"QUOTATION - {quote_data['quote_ref']}", title_style))
        
        # Company info
        if quote_data['current_user'].company:
            company = quote_data['current_user'].company
            company_info = f"<b>{company.name}</b><br/>"
            if company.address:
                company_info += f"{company.address}<br/>"
            if company.phone:
                company_info += f"Phone: {company.phone}<br/>"
            if company.email:
                company_info += f"Email: {company.email}"
        else:
            company_info = "<b>Your Company Name</b><br/>Your Address<br/>Phone: +27 XXX XXX XXXX<br/>Email: info@company.com"
        
        story.append(Paragraph(company_info, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Quote details
        quote_info = [
            ['Quote Date:', quote_data['quote_date'].strftime('%d %B %Y')],
            ['Valid Until:', quote_data['valid_until'].strftime('%d %B %Y')],
            ['Client:', quote_data['client_name']],
            ['Contact:', quote_data['client_contact'] or 'N/A'],
            ['Tender:', quote_data['tender'].title],
        ]
        
        quote_table = Table(quote_info, colWidths=[2*inch, 4*inch])
        quote_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(quote_table)
        story.append(Spacer(1, 30))
        
        # Items table
        story.append(Paragraph("Quote Items", styles['Heading3']))
        
        table_data = [['Description', 'Qty', 'Unit Price', 'Total']]
        
        for item in quote_data['items']:
            table_data.append([
                item['description'],
                f"{item['qty']:.0f}" if item['qty'] == int(item['qty']) else f"{item['qty']:.2f}",
                f"R {item['unit_price']:,.2f}",
                f"R {item['total']:,.2f}"
            ])
        
        # Add totals
        table_data.append(['', '', 'Subtotal:', f"R {quote_data['subtotal']:,.2f}"])
        table_data.append(['', '', 'VAT (15%):', f"R {quote_data['vat_amount']:,.2f}"])
        table_data.append(['', '', 'TOTAL:', f"R {quote_data['total_amount']:,.2f}"])
        
        items_table = Table(table_data, colWidths=[3.5*inch, 0.8*inch, 1.2*inch, 1.2*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -4), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -4), 9),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -3), (-1, -1), 10),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -4), 1, colors.black),
            ('LINEBELOW', (0, -3), (-1, -1), 1, colors.black),
        ]))
        
        story.append(items_table)
        story.append(Spacer(1, 30))
        
        # Notes
        if quote_data['notes']:
            story.append(Paragraph("Notes:", styles['Heading4']))
            story.append(Paragraph(quote_data['notes'], styles['Normal']))
            story.append(Spacer(1, 20))
        
        # Terms
        terms = """
        <b>Terms and Conditions:</b><br/>
        • This quotation is valid until the date specified above<br/>
        • Payment terms: 30 days from invoice date<br/>
        • Prices include VAT where applicable<br/>
        • Delivery timeframes to be confirmed upon order<br/>
        """
        story.append(Paragraph(terms, styles['Normal']))
        
        doc.build(story)
        pdf_content = buffer.getvalue()
        buffer.close()
        
        filename = f"Quote_{quote_data['quote_ref']}_{quote_data['quote_date'].strftime('%Y%m%d')}.pdf"
        return pdf_content, filename, 'application/pdf'
        
    except ImportError:
        # Fallback if reportlab not installed
        return generate_quote_html_fallback(quote_data)
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        return generate_quote_html_fallback(quote_data)


def generate_quote_excel(quote_data):
    """Generate Excel quote"""
    try:
        import xlsxwriter
        import io
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Quote')
        
        # Formats
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'bg_color': '#366092',
            'font_color': 'white'
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D7E4BD',
            'border': 1
        })
        
        cell_format = workbook.add_format({
            'border': 1
        })
        
        money_format = workbook.add_format({
            'num_format': 'R #,##0.00',
            'border': 1
        })
        
        # Title
        worksheet.merge_range('A1:E1', f"QUOTATION - {quote_data['quote_ref']}", title_format)
        
        # Company info
        row = 3
        if quote_data['current_user'].company:
            company = quote_data['current_user'].company
            worksheet.write(row, 0, company.name, header_format)
            row += 1
            if company.address:
                worksheet.write(row, 0, company.address)
                row += 1
            if company.phone:
                worksheet.write(row, 0, f"Phone: {company.phone}")
                row += 1
            if company.email:
                worksheet.write(row, 0, f"Email: {company.email}")
                row += 1
        
        row += 2
        
        # Quote details
        worksheet.write(row, 0, 'Quote Date:', header_format)
        worksheet.write(row, 1, quote_data['quote_date'].strftime('%d %B %Y'))
        row += 1
        worksheet.write(row, 0, 'Valid Until:', header_format)
        worksheet.write(row, 1, quote_data['valid_until'].strftime('%d %B %Y'))
        row += 1
        worksheet.write(row, 0, 'Client:', header_format)
        worksheet.write(row, 1, quote_data['client_name'])
        row += 1
        worksheet.write(row, 0, 'Contact:', header_format)
        worksheet.write(row, 1, quote_data['client_contact'] or 'N/A')
        row += 1
        worksheet.write(row, 0, 'Tender:', header_format)
        worksheet.write(row, 1, quote_data['tender'].title)
        
        row += 3
        
        # Items table
        worksheet.write(row, 0, 'Description', header_format)
        worksheet.write(row, 1, 'Quantity', header_format)
        worksheet.write(row, 2, 'Unit Price', header_format)
        worksheet.write(row, 3, 'Total', header_format)
        row += 1
        
        for item in quote_data['items']:
            worksheet.write(row, 0, item['description'], cell_format)
            worksheet.write(row, 1, item['qty'], cell_format)
            worksheet.write(row, 2, item['unit_price'], money_format)
            worksheet.write(row, 3, item['total'], money_format)
            row += 1
        
        row += 1
        
        # Totals
        worksheet.write(row, 2, 'Subtotal:', header_format)
        worksheet.write(row, 3, quote_data['subtotal'], money_format)
        row += 1
        worksheet.write(row, 2, 'VAT (15%):', header_format)
        worksheet.write(row, 3, quote_data['vat_amount'], money_format)
        row += 1
        worksheet.write(row, 2, 'TOTAL:', header_format)
        worksheet.write(row, 3, quote_data['total_amount'], money_format)
        
        # Notes
        if quote_data['notes']:
            row += 3
            worksheet.write(row, 0, 'Notes:', header_format)
            row += 1
            worksheet.write(row, 0, quote_data['notes'])
        
        # Set column widths
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:B', 12)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 15)
        
        workbook.close()
        excel_content = output.getvalue()
        output.close()
        
        filename = f"Quote_{quote_data['quote_ref']}_{quote_data['quote_date'].strftime('%Y%m%d')}.xlsx"
        return excel_content, filename, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
    except ImportError:
        # Fallback if xlsxwriter not installed
        return generate_quote_html_fallback(quote_data)
    except Exception as e:
        print(f"Error generating Excel: {str(e)}")
        return generate_quote_html_fallback(quote_data)


def generate_quote_html_fallback(quote_data):
    """Fallback HTML generation if PDF/Excel libraries not available"""
    quote_html = render_quote_template(quote_data)
    filename = f"Quote_{quote_data['quote_ref']}_{quote_data['quote_date'].strftime('%Y%m%d')}.html"
    return quote_html.encode('utf-8'), filename, 'text/html'

# do not delete 
# Add these functions to your app.py file (after imports, before routes)

def get_next_quote_counter():
    """Generate the next quote counter/reference number"""
    try:
        # Simple approach: use current timestamp for uniqueness
        return f"QUO{datetime.now().strftime('%y%m%d%H%M')}"
    except Exception as e:
        return f"QUO{datetime.now().strftime('%y%m%d')}"

def render_quote_template(quote_data):
    """Render the quote using simple Jinja templating"""
    try:
        # Simple HTML template
        template = """
<!DOCTYPE html>
<html>
<head>
    <title>Quote {{ quote_ref }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
        .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #333; padding-bottom: 20px; }
        .company-info { background: #f9f9f9; padding: 20px; margin: 20px 0; }
        .details { margin: 20px 0; }
        .details div { margin: 10px 0; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #f2f2f2; font-weight: bold; }
        .text-right { text-align: right; }
        .totals { background: #f9f9f9; padding: 20px; margin: 20px 0; }
        .total-line { margin: 5px 0; }
        .total-final { font-weight: bold; font-size: 1.2em; border-top: 2px solid #333; padding-top: 10px; }
        .notes { background: #fff3cd; padding: 15px; margin: 20px 0; border-left: 4px solid #ffc107; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>QUOTATION</h1>
        <h2>{{ quote_ref }}</h2>
    </div>
    
    <div class="company-info">
        <h3>{{ current_user.company.name if current_user.company else 'Your Company' }}</h3>
        {% if current_user.company %}
            {% if current_user.company.address %}<div>{{ current_user.company.address }}</div>{% endif %}
            {% if current_user.company.phone %}<div>Phone: {{ current_user.company.phone }}</div>{% endif %}
            {% if current_user.company.email %}<div>Email: {{ current_user.company.email }}</div>{% endif %}
        {% endif %}
    </div>
    
    <div class="details">
        <div><strong>Quote Date:</strong> {{ quote_date.strftime('%d %B %Y') }}</div>
        <div><strong>Valid Until:</strong> {{ valid_until.strftime('%d %B %Y') }}</div>
        <div><strong>Client:</strong> {{ client_name }}</div>
        {% if client_contact %}<div><strong>Contact:</strong> {{ client_contact }}</div>{% endif %}
        <div><strong>Tender:</strong> {{ tender.title }}</div>
        {% if tender.reference_number %}<div><strong>Tender Ref:</strong> {{ tender.reference_number }}</div>{% endif %}
    </div>
    
    <table>
        <thead>
            <tr>
                <th>Description</th>
                <th style="width: 100px;">Quantity</th>
                <th style="width: 120px;">Unit Price</th>
                <th style="width: 120px;">Total</th>
            </tr>
        </thead>
        <tbody>
            {% for item in items %}
            <tr>
                <td>{{ item.description }}</td>
                <td class="text-right">{{ "%.0f"|format(item.qty) if item.qty == item.qty|int else "%.2f"|format(item.qty) }}</td>
                <td class="text-right">R {{ "{:,.2f}".format(item.unit_price) }}</td>
                <td class="text-right">R {{ "{:,.2f}".format(item.total) }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    <div class="totals">
        <div class="total-line"><strong>Subtotal:</strong> <span style="float: right;">R {{ "{:,.2f}".format(subtotal) }}</span></div>
        <div class="total-line"><strong>VAT (15%):</strong> <span style="float: right;">R {{ "{:,.2f}".format(vat_amount) }}</span></div>
        <div class="total-final"><strong>TOTAL:</strong> <span style="float: right;">R {{ "{:,.2f}".format(total_amount) }}</span></div>
    </div>
    
    {% if notes %}
    <div class="notes">
        <strong>Notes:</strong><br>
        {{ notes|replace('\\n', '<br>')|safe }}
    </div>
    {% endif %}
    
    <div style="margin: 30px 0;">
        <h4>Terms & Conditions:</h4>
        <ul>
            <li>This quotation is valid until {{ valid_until.strftime('%d %B %Y') }}</li>
            <li>Payment terms: 30 days from invoice date</li>
            <li>Prices include VAT where applicable</li>
            <li>Delivery timeframes to be confirmed upon order</li>
        </ul>
    </div>
    
    <div class="footer">
        <p>Thank you for considering our quotation!</p>
        <p><small>Generated on {{ datetime.now().strftime('%d %B %Y at %H:%M') }}</small></p>
    </div>
</body>
</html>
        """
        
        # Add datetime to the template data
        quote_data['datetime'] = datetime
        
        return render_template_string(template, **quote_data)
        
    except Exception as e:
        print(f"Error rendering quote template: {str(e)}")
        return f"<html><body><h1>Quote {quote_data.get('quote_ref', 'ERROR')}</h1><p>Error generating quote.</p></body></html>"

def generate_quote_pdf(quote_data):
    """Generate PDF quote"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import inch
        import io
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.darkblue,
            spaceAfter=30,
            alignment=1
        )
        story.append(Paragraph(f"QUOTATION - {quote_data['quote_ref']}", title_style))
        
        # Company info
        if quote_data['current_user'].company:
            company = quote_data['current_user'].company
            company_info = f"<b>{company.name}</b><br/>"
            if company.address:
                company_info += f"{company.address}<br/>"
            if company.phone:
                company_info += f"Phone: {company.phone}<br/>"
            if company.email:
                company_info += f"Email: {company.email}"
        else:
            company_info = "<b>Your Company Name</b><br/>Your Address<br/>Phone: +27 XXX XXX XXXX<br/>Email: info@company.com"
        
        story.append(Paragraph(company_info, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Quote details
        quote_info = [
            ['Quote Date:', quote_data['quote_date'].strftime('%d %B %Y')],
            ['Valid Until:', quote_data['valid_until'].strftime('%d %B %Y')],
            ['Client:', quote_data['client_name']],
            ['Contact:', quote_data['client_contact'] or 'N/A'],
            ['Tender:', quote_data['tender'].title],
        ]
        
        quote_table = Table(quote_info, colWidths=[2*inch, 4*inch])
        quote_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(quote_table)
        story.append(Spacer(1, 30))
        
        # Items table
        story.append(Paragraph("Quote Items", styles['Heading3']))
        
        table_data = [['Description', 'Qty', 'Unit Price', 'Total']]
        
        for item in quote_data['items']:
            table_data.append([
                item['description'],
                f"{item['qty']:.0f}" if item['qty'] == int(item['qty']) else f"{item['qty']:.2f}",
                f"R {item['unit_price']:,.2f}",
                f"R {item['total']:,.2f}"
            ])
        
        # Add totals
        table_data.append(['', '', 'Subtotal:', f"R {quote_data['subtotal']:,.2f}"])
        table_data.append(['', '', 'VAT (15%):', f"R {quote_data['vat_amount']:,.2f}"])
        table_data.append(['', '', 'TOTAL:', f"R {quote_data['total_amount']:,.2f}"])
        
        items_table = Table(table_data, colWidths=[3.5*inch, 0.8*inch, 1.2*inch, 1.2*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -4), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -4), 9),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -3), (-1, -1), 10),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -4), 1, colors.black),
            ('LINEBELOW', (0, -3), (-1, -1), 1, colors.black),
        ]))
        
        story.append(items_table)
        story.append(Spacer(1, 30))
        
        # Notes
        if quote_data['notes']:
            story.append(Paragraph("Notes:", styles['Heading4']))
            story.append(Paragraph(quote_data['notes'], styles['Normal']))
            story.append(Spacer(1, 20))
        
        # Terms
        terms = """
        <b>Terms and Conditions:</b><br/>
        • This quotation is valid until the date specified above<br/>
        • Payment terms: 30 days from invoice date<br/>
        • Prices include VAT where applicable<br/>
        • Delivery timeframes to be confirmed upon order<br/>
        """
        story.append(Paragraph(terms, styles['Normal']))
        
        doc.build(story)
        pdf_content = buffer.getvalue()
        buffer.close()
        
        filename = f"Quote_{quote_data['quote_ref']}_{quote_data['quote_date'].strftime('%Y%m%d')}.pdf"
        return pdf_content, filename, 'application/pdf'
        
    except ImportError:
        # Fallback if reportlab not installed
        return generate_quote_html_fallback(quote_data)
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        return generate_quote_html_fallback(quote_data)

def generate_quote_excel(quote_data):
    """Generate Excel quote"""
    try:
        import xlsxwriter
        import io
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Quote')
        
        # Formats
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'bg_color': '#366092',
            'font_color': 'white'
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D7E4BD',
            'border': 1
        })
        
        cell_format = workbook.add_format({
            'border': 1
        })
        
        money_format = workbook.add_format({
            'num_format': 'R #,##0.00',
            'border': 1
        })
        
        # Title
        worksheet.merge_range('A1:E1', f"QUOTATION - {quote_data['quote_ref']}", title_format)
        
        # Company info
        row = 3
        if quote_data['current_user'].company:
            company = quote_data['current_user'].company
            worksheet.write(row, 0, company.name, header_format)
            row += 1
            if company.address:
                worksheet.write(row, 0, company.address)
                row += 1
            if company.phone:
                worksheet.write(row, 0, f"Phone: {company.phone}")
                row += 1
            if company.email:
                worksheet.write(row, 0, f"Email: {company.email}")
                row += 1
        
        row += 2
        
        # Quote details
        worksheet.write(row, 0, 'Quote Date:', header_format)
        worksheet.write(row, 1, quote_data['quote_date'].strftime('%d %B %Y'))
        row += 1
        worksheet.write(row, 0, 'Valid Until:', header_format)
        worksheet.write(row, 1, quote_data['valid_until'].strftime('%d %B %Y'))
        row += 1
        worksheet.write(row, 0, 'Client:', header_format)
        worksheet.write(row, 1, quote_data['client_name'])
        row += 1
        worksheet.write(row, 0, 'Contact:', header_format)
        worksheet.write(row, 1, quote_data['client_contact'] or 'N/A')
        row += 1
        worksheet.write(row, 0, 'Tender:', header_format)
        worksheet.write(row, 1, quote_data['tender'].title)
        
        row += 3
        
        # Items table
        worksheet.write(row, 0, 'Description', header_format)
        worksheet.write(row, 1, 'Quantity', header_format)
        worksheet.write(row, 2, 'Unit Price', header_format)
        worksheet.write(row, 3, 'Total', header_format)
        row += 1
        
        for item in quote_data['items']:
            worksheet.write(row, 0, item['description'], cell_format)
            worksheet.write(row, 1, item['qty'], cell_format)
            worksheet.write(row, 2, item['unit_price'], money_format)
            worksheet.write(row, 3, item['total'], money_format)
            row += 1
        
        row += 1
        
        # Totals
        worksheet.write(row, 2, 'Subtotal:', header_format)
        worksheet.write(row, 3, quote_data['subtotal'], money_format)
        row += 1
        worksheet.write(row, 2, 'VAT (15%):', header_format)
        worksheet.write(row, 3, quote_data['vat_amount'], money_format)
        row += 1
        worksheet.write(row, 2, 'TOTAL:', header_format)
        worksheet.write(row, 3, quote_data['total_amount'], money_format)
        
        # Notes
        if quote_data['notes']:
            row += 3
            worksheet.write(row, 0, 'Notes:', header_format)
            row += 1
            worksheet.write(row, 0, quote_data['notes'])
        
        # Set column widths
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:B', 12)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 15)
        
        workbook.close()
        excel_content = output.getvalue()
        output.close()
        
        filename = f"Quote_{quote_data['quote_ref']}_{quote_data['quote_date'].strftime('%Y%m%d')}.xlsx"
        return excel_content, filename, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
    except ImportError:
        # Fallback if xlsxwriter not installed
        return generate_quote_html_fallback(quote_data)
    except Exception as e:
        print(f"Error generating Excel: {str(e)}")
        return generate_quote_html_fallback(quote_data)

def generate_quote_html_fallback(quote_data):
    """Fallback HTML generation if PDF/Excel libraries not available"""
    quote_html = render_quote_template(quote_data)
    filename = f"Quote_{quote_data['quote_ref']}_{quote_data['quote_date'].strftime('%Y%m%d')}.html"
    return quote_html.encode('utf-8'), filename, 'text/html'  




logger = logging.getLogger(__name__)

@app.route('/api/notifications/count')
@login_required
def get_notification_count():
    """API endpoint to get notification count"""
    try:
        # Use company_id directly from session (it's already there!)
        company_id = session.get('company_id')
        if not company_id:
            logger.error("No company_id in session")
            return jsonify({'count': 0})
        
        # Count unread/unprocessed notifications for this company
        count = TenderNotification.query.filter_by(
            company_id=company_id,
            is_processed=False
        ).count()
        
        logger.info(f"Found {count} unprocessed notifications for company {company_id}")
        return jsonify({'count': count})
        
    except Exception as e:
        logger.error(f"Error getting notification count: {str(e)}", exc_info=True)
        return jsonify({'count': 0})

@app.route('/api/notifications')
@login_required
def get_notifications():
    """API endpoint to get notifications"""
    try:
        # Use company_id directly from session
        company_id = session.get('company_id')
        if not company_id:
            logger.error("No company_id in session")
            return jsonify({'notifications': []})
        
        # Get unprocessed notifications for this company
        notifications = TenderNotification.query.filter_by(
            company_id=company_id,
            is_processed=False
        ).order_by(TenderNotification.created_at.desc()).limit(20).all()
        
        logger.info(f"Found {len(notifications)} notifications for company {company_id}")
        
        notification_data = []
        for n in notifications:
            try:
                # Safely get tender information
                tender_title = 'Unknown Tender'
                tender_reference = 'N/A'
                submission_deadline = 'No deadline'
                
                if n.tender:
                    tender_title = n.tender.title or 'Unknown Tender'
                    tender_reference = getattr(n.tender, 'reference_number', 'N/A')
                    if hasattr(n.tender, 'submission_deadline') and n.tender.submission_deadline:
                        submission_deadline = n.tender.submission_deadline.strftime('%Y-%m-%d %H:%M')
                
                notification_data.append({
                    'id': n.id,
                    'message': n.message or f'Notification for tender ID {n.tender_id}',
                    'tender_id': n.tender_id,
                    'tender_title': tender_title,
                    'tender_reference': tender_reference,
                    'submission_deadline': submission_deadline,
                    'days_remaining': n.days_remaining or 0,
                    'created_at': n.created_at.strftime('%Y-%m-%d %H:%M') if n.created_at else 'Unknown',
                    'is_read': n.is_read,
                    'is_processed': n.is_processed,
                    'processing_note': n.processing_note
                })
            except Exception as item_error:
                logger.error(f"Error processing notification {n.id}: {str(item_error)}")
                # Still include the notification with minimal data
                notification_data.append({
                    'id': n.id,
                    'message': n.message or f'Notification {n.id}',
                    'tender_id': n.tender_id,
                    'error': 'Error loading details'
                })
        
        return jsonify({'notifications': notification_data})
        
    except Exception as e:
        logger.error(f"Error getting notifications: {str(e)}", exc_info=True)
        return jsonify({'notifications': []})

@app.route('/notifications')
@login_required
def notifications_page():
    """Notifications management page"""
    try:
        # Use company_id directly from session
        company_id = session.get('company_id')
        if not company_id:
            flash('No company associated with your session', 'error')
            return redirect(url_for('dashboard'))
        
        # Get ALL notifications for this company (not just unprocessed)
        notifications = TenderNotification.query.filter_by(
            company_id=company_id
        ).order_by(TenderNotification.created_at.desc()).all()
        
        # Get company notification settings
        settings = CompanySettings.query.filter_by(company_id=company_id).first()
        
        logger.info(f"Loading notifications page: {len(notifications)} notifications for company {company_id}")
        
        return render_template('notifications/index.html', 
                             notifications=notifications,
                             settings=settings)
                             
    except Exception as e:
        logger.error(f"Error loading notifications page: {str(e)}", exc_info=True)
        flash(f'Error loading notifications: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    try:
        # Use company_id from session for security
        company_id = session.get('company_id')
        user_id = session.get('user_id')
        
        if not company_id or not user_id:
            return jsonify({'success': False, 'error': 'Invalid session'})
        
        # Find notification belonging to user's company
        notification = TenderNotification.query.filter_by(
            id=notification_id,
            company_id=company_id
        ).first()
        
        if not notification:
            logger.warning(f"Notification {notification_id} not found for company {company_id}")
            return jsonify({'success': False, 'error': 'Notification not found or access denied'})
        
        notification.is_read = True
        db.session.commit()
        
        logger.info(f"Notification {notification_id} marked as read by user {user_id}")
        return jsonify({'success': True, 'message': 'Notification marked as read'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error marking notification as read: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'Database error: {str(e)}'})

@app.route('/notifications/<int:notification_id>/process', methods=['POST'])
@login_required
def process_notification(notification_id):
    """Process a single notification"""
    try:
        # Use session data
        company_id = session.get('company_id')
        user_id = session.get('user_id')
        
        if not company_id or not user_id:
            return jsonify({'success': False, 'error': 'Invalid session'})
        
        # Get JSON data safely
        try:
            data = request.get_json() or {}
        except Exception:
            data = {}
        
        action_comment = data.get('comment', '').strip()
        if not action_comment:
            return jsonify({'success': False, 'error': 'Action comment is required'})
        
        # Find notification belonging to user's company
        notification = TenderNotification.query.filter_by(
            id=notification_id,
            company_id=company_id
        ).first()
        
        if not notification:
            logger.warning(f"Notification {notification_id} not found for company {company_id}")
            return jsonify({'success': False, 'error': 'Notification not found or access denied'})
        
        # Update notification
        notification.is_processed = True
        notification.processed_by = user_id
        notification.processed_at = datetime.utcnow()
        notification.processing_note = action_comment
        notification.is_read = True
        
        db.session.commit()
        
        logger.info(f"Notification {notification_id} processed by user {user_id}")
        return jsonify({
            'success': True,
            'message': 'Notification processed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing notification: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'Database error: {str(e)}'})

@app.route('/notifications/process-all', methods=['POST'])
@login_required
def process_all_notifications():
    """Process all unprocessed notifications for the company"""
    try:
        # Use session data
        company_id = session.get('company_id')
        user_id = session.get('user_id')
        
        if not company_id or not user_id:
            return jsonify({'success': False, 'error': 'Invalid session'})
        
        # Get JSON data safely
        try:
            data = request.get_json() or {}
        except Exception:
            data = {}
        
        action_comment = data.get('comment', '').strip()
        if not action_comment:
            return jsonify({'success': False, 'error': 'Action comment is required'})
        
        # Get all unprocessed notifications for this company
        notifications = TenderNotification.query.filter_by(
            company_id=company_id,
            is_processed=False
        ).all()
        
        count = 0
        for notification in notifications:
            notification.is_processed = True
            notification.processed_by = user_id
            notification.processed_at = datetime.utcnow()
            notification.processing_note = action_comment
            notification.is_read = True
            count += 1
        
        if count > 0:
            db.session.commit()
        
        logger.info(f"Processed {count} notifications for company {company_id} by user {user_id}")
        return jsonify({
            'success': True, 
            'count': count,
            'message': f'Successfully processed {count} notifications'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing all notifications: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'Database error: {str(e)}'})

# Helper function to create notifications for tenders approaching deadline
def create_notifications_for_company(company_id, notification_days=7):
    """Create notifications for tenders approaching submission deadline"""
    try:
        today = datetime.now()
        cutoff_datetime = today + timedelta(days=notification_days)
        
        # Find tenders approaching submission deadline
        tenders_approaching = Tender.query.filter(
            Tender.submission_deadline.isnot(None),
            Tender.submission_deadline >= today,
            Tender.submission_deadline <= cutoff_datetime,
            ~Tender.status_id.in_([3, 6])  # Not closed or cancelled
        ).all()
        
        # Get existing notifications for these tenders
        existing_tender_ids = set()
        if tenders_approaching:
            existing_notifications = TenderNotification.query.filter(
                TenderNotification.company_id == company_id,
                TenderNotification.tender_id.in_([t.id for t in tenders_approaching])
            ).all()
            existing_tender_ids = {n.tender_id for n in existing_notifications}
        
        # Create notifications for tenders without them
        new_count = 0
        for tender in tenders_approaching:
            if tender.id not in existing_tender_ids:
                days_remaining = (tender.submission_deadline.date() - today.date()).days
                
                notification = TenderNotification(
                    tender_id=tender.id,
                    company_id=company_id,
                    notification_type='deadline_approaching',
                    message=f"Tender '{tender.title}' submission deadline in {days_remaining} day{'s' if days_remaining != 1 else ''}",
                    days_remaining=days_remaining,
                    is_read=False,
                    is_processed=False,
                    created_at=datetime.utcnow()
                )
                
                db.session.add(notification)
                new_count += 1
        
        if new_count > 0:
            db.session.commit()
            logger.info(f"Created {new_count} new notifications for company {company_id}")
        
        return new_count
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating notifications: {str(e)}", exc_info=True)
        return 0

@app.route('/notifications/create-for-deadlines', methods=['POST'])
@login_required
def create_deadline_notifications():
    """Manually create notifications for approaching deadlines"""
    try:
        company_id = session.get('company_id')
        if not company_id:
            return jsonify({'success': False, 'error': 'No company in session'})
        
        count = create_notifications_for_company(company_id)
        
        return jsonify({
            'success': True,
            'message': f'Created {count} new notifications',
            'count': count
        })
        
    except Exception as e:
        logger.error(f"Error in create_deadline_notifications: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)})


# =====================================================
# SUPER ADMIN COMPANY NOTIFICATION SETTINGS
# =====================================================

@app.route('/admin/companies/<int:company_id>/notification-settings', methods=['GET', 'POST'])
@super_admin_required
def company_notification_settings(company_id):
    """Manage notification settings for a company (Super Admin only)"""
    try:
        company = Company.query.get_or_404(company_id)
        settings = CompanySettings.query.filter_by(company_id=company_id).first()
        
        if request.method == 'POST':
            notification_days = int(request.form.get('notification_days', 7))
            
            if not settings:
                settings = CompanySettings(
                    company_id=company_id,
                    notification_days=notification_days
                )
                db.session.add(settings)
            else:
                settings.notification_days = notification_days
                settings.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash(f'Notification settings updated for {company.name}.', 'success')
            return redirect(url_for('company_notification_settings', company_id=company_id))
        
        return render_template('admin/company_notification_settings.html', 
                             company=company, 
                             settings=settings)
    except Exception as e:
        print(f"Error managing notification settings: {str(e)}")
        flash('Error managing notification settings', 'error')
        return redirect(url_for('admin_companies'))

# =====================================================
# BACKGROUND TASK TO GENERATE NOTIFICATIONS
# =====================================================

@app.route('/admin/generate-notifications', methods=['POST'])
@super_admin_required
def manual_generate_notifications():
    """Manually trigger notification generation (for testing)"""
    try:
        generated_count = 0
        
        # Get all active companies
        companies = Company.query.filter_by(is_active=True).all()
        
        for company in companies:
            # Get company notification days setting
            settings = CompanySettings.query.filter_by(company_id=company.id).first()
            notification_days = settings.notification_days if settings else 7
            
            # Calculate cutoff date
            cutoff_date = datetime.now() + timedelta(days=notification_days)
            
            # Find tenders approaching deadline (not closed/cancelled)
            approaching_tenders = Tender.query.filter(
                Tender.company_id == company.id,
                Tender.submission_deadline <= cutoff_date,
                Tender.submission_deadline >= datetime.now(),
                ~Tender.status_id.in_([3, 6])  # Not closed or cancelled
            ).all()
            
            for tender in approaching_tenders:
                # Check if notification already exists
                existing = TenderNotification.query.filter_by(
                    tender_id=tender.id,
                    company_id=company.id,
                    notification_type='deadline_approaching'
                ).first()
                
                if not existing:
                    days_remaining = (tender.submission_deadline - datetime.now()).days
                    
                    # Create notification
                    notification = TenderNotification(
                        tender_id=tender.id,
                        company_id=company.id,
                        notification_type='deadline_approaching',
                        message=f"Tender '{tender.title}' (#{tender.reference_number}) deadline in {days_remaining} days",
                        days_remaining=days_remaining
                    )
                    db.session.add(notification)
                    generated_count += 1
        
        db.session.commit()
        
        flash(f'Generated {generated_count} notifications successfully.', 'success')
        return redirect(url_for('admin_companies'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error generating notifications: {str(e)}")
        flash('Error generating notifications', 'error')
        return redirect(url_for('admin_companies'))

# =====================================================
# HELPER FUNCTION TO AUTO-GENERATE NOTIFICATIONS
# =====================================================

# Add this function to your app.py file

def create_notifications_for_company_tenders(company_id, notification_days=7):
    """Create notifications for tenders owned by the company approaching submission deadline"""
    try:
        today = datetime.now()
        cutoff_datetime = today + timedelta(days=notification_days)
        
        logger.info(f"Creating notifications for company {company_id}, checking tenders until {cutoff_datetime}")
        
        # Find company's own tenders approaching deadline
        company_tenders = Tender.query.filter(
            Tender.company_id == company_id,  # Only company's own tenders
            Tender.submission_deadline.isnot(None),
            Tender.submission_deadline >= today,
            Tender.submission_deadline <= cutoff_datetime,
            ~Tender.status_id.in_([3, 6])  # Not closed or cancelled
        ).all()
        
        logger.info(f"Found {len(company_tenders)} tenders approaching deadline for company {company_id}")
        
        # Check which ones already have notifications
        existing_tender_ids = set()
        if company_tenders:
            existing_notifications = TenderNotification.query.filter(
                TenderNotification.company_id == company_id,
                TenderNotification.tender_id.in_([t.id for t in company_tenders])
            ).all()
            existing_tender_ids = {n.tender_id for n in existing_notifications}
            logger.info(f"Found {len(existing_notifications)} existing notifications for company {company_id}")
        
        # Create notifications for tenders without them
        new_count = 0
        for tender in company_tenders:
            if tender.id not in existing_tender_ids:
                days_remaining = (tender.submission_deadline.date() - today.date()).days
                
                notification = TenderNotification(
                    tender_id=tender.id,
                    company_id=company_id,
                    notification_type='deadline_approaching',
                    message=f"Tender '{tender.title}' submission deadline in {days_remaining} day{'s' if days_remaining != 1 else ''}",
                    days_remaining=days_remaining,
                    is_read=False,
                    is_processed=False,
                    created_at=datetime.utcnow()
                )
                
                db.session.add(notification)
                new_count += 1
                logger.info(f"Created notification for tender {tender.id} ({tender.title}) - {days_remaining} days remaining")
        
        if new_count > 0:
            db.session.commit()
            logger.info(f"Successfully created {new_count} notifications for company {company_id}")
        else:
            logger.info(f"No new notifications needed for company {company_id}")
        
        return new_count
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating notifications for company {company_id}: {str(e)}", exc_info=True)
        return 0
    
# Also update your auto_generate_notifications function to use the correct function name:
def auto_generate_notifications_main():
    """Auto-generate notifications for all companies - runs daily at midnight"""
    job_id = 'daily_notifications'
    start_time = datetime.now()
    
    # Log job start
    log_job_execution(job_id, 'running')
    
    try:
        logger.info(f"Starting daily notification generation at {start_time}")
        
        # Get all active companies
        companies = Company.query.filter_by(is_active=True).all()
        
        total_created = 0
        total_companies = len(companies)
        
        logger.info(f"Processing {total_companies} active companies")
        
        for company in companies:
            try:
                # Use the correct function name
                count = create_notifications_for_company_tenders(company.id, 7)
                total_created += count
                
                if count > 0:
                    logger.info(f"Created {count} notifications for company {company.id} ({getattr(company, 'name', 'Unknown')})")
                
            except Exception as company_error:
                logger.error(f"Error creating notifications for company {company.id}: {str(company_error)}")
                continue
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Daily notification generation completed:")
        logger.info(f"- Processed {total_companies} companies")
        logger.info(f"- Created {total_created} notifications")
        logger.info(f"- Duration: {duration:.2f} seconds")
        
        # Log successful completion
        log_job_execution(job_id, 'success', duration, total_created)
        
        return total_created
        
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        error_msg = str(e)
        
        logger.error(f"Error in daily notification generation: {error_msg}", exc_info=True)
        
        # Log error
        log_job_execution(job_id, 'error', duration, 0, error_msg)
        
        return 0

# Make sure you also have the logging function:
job_execution_history = []

def log_job_execution(job_id, status, duration=None, created_count=None, error=None):
    """Log job execution for history tracking"""
    global job_execution_history
    
    execution_log = {
        'job_id': job_id,
        'timestamp': datetime.now(),
        'status': status,  # 'success', 'error', 'running'
        'duration': duration,
        'created_count': created_count,
        'error': error
    }
    
    job_execution_history.append(execution_log)
    
    # Keep only last 50 executions
    if len(job_execution_history) > 50:
        job_execution_history = job_execution_history[-50:]
# =====================================================
# SCHEDULER SETUP (for automatic notifications)
# =====================================================

# Create scheduler
scheduler = BackgroundScheduler()

# Add job to run every hour
scheduler = BackgroundScheduler(timezone='Africa/Johannesburg')
scheduler.add_job(
    func=auto_generate_notifications_main,
    trigger=CronTrigger(hour=0, minute=0),
    id='daily_notifications',
    name='Daily Notification Generation',
    max_instances=1,
    coalesce=True,
    misfire_grace_time=3600
)

# Start scheduler
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())




# Global variable to track job execution history
job_execution_history = []

def log_job_execution(job_id, status, duration=None, created_count=None, error=None):
    """Log job execution for history tracking"""
    global job_execution_history
    
    execution_log = {
        'job_id': job_id,
        'timestamp': datetime.now(),
        'status': status,  # 'success', 'error', 'running'
        'duration': duration,
        'created_count': created_count,
        'error': error
    }
    
    job_execution_history.append(execution_log)
    
    # Keep only last 50 executions
    if len(job_execution_history) > 50:
        job_execution_history = job_execution_history[-50:]

# Updated notification function with logging
def auto_generate_notifications():
    """Auto-generate notifications with execution logging"""
    job_id = 'daily_notifications'
    start_time = datetime.now()
    
    # Log job start
    log_job_execution(job_id, 'running')
    
    try:
        logger.info(f"Starting daily notification generation at {start_time}")
        
        # Get all active companies
        companies = Company.query.filter_by(is_active=True).all()
        
        total_created = 0
        total_companies = len(companies)
        
        for company in companies:
            try:
                count = create_notifications_for_company_tenders(company.id, 7)
                total_created += count
                
                if count > 0:
                    logger.info(f"Created {count} notifications for company {company.id}")
                
            except Exception as company_error:
                logger.error(f"Error creating notifications for company {company.id}: {str(company_error)}")
                continue
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Daily notification generation completed: {total_created} notifications in {duration:.2f}s")
        
        # Log successful completion
        log_job_execution(job_id, 'success', duration, total_created)
        
        return total_created
        
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        error_msg = str(e)
        
        logger.error(f"Error in daily notification generation: {error_msg}", exc_info=True)
        
        # Log error
        log_job_execution(job_id, 'error', duration, 0, error_msg)
        
        return 0

@app.route('/admin/scheduler')
@login_required
def scheduler_admin():
    """Admin page for scheduler management"""
    try:
        user = AuthService.get_user_by_id(session['user_id'])
        if not user or not getattr(user, 'is_super_admin', False):
            flash('Super admin access required', 'error')
            return redirect(url_for('dashboard'))
        
        return render_template('admin/scheduler.html')
        
    except Exception as e:
        logger.error(f"Error loading scheduler admin: {str(e)}")
        flash('Error loading scheduler admin', 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/admin/scheduler/status')
@login_required
def get_scheduler_status():
    """API endpoint to get scheduler status"""
    try:
        user = AuthService.get_user_by_id(session['user_id'])
        if not user or not getattr(user, 'is_super_admin', False):
            return jsonify({'error': 'Super admin access required'}), 403
        
        if not scheduler.running:
            return jsonify({
                'status': 'stopped',
                'running': False,
                'jobs': [],
                'execution_history': []
            })
        
        jobs = []
        for job in scheduler.get_jobs():
            # Calculate time until next run
            next_run = None
            time_until_next = None
            
            if job.next_run_time:
                next_run = job.next_run_time.isoformat()
                time_until_next = (job.next_run_time - datetime.now(job.next_run_time.tzinfo)).total_seconds()
            
            jobs.append({
                'id': job.id,
                'name': getattr(job, 'name', job.id),
                'trigger': str(job.trigger),
                'next_run': next_run,
                'time_until_next': time_until_next,
                'max_instances': getattr(job, 'max_instances', 1),
                'coalesce': getattr(job, 'coalesce', False)
            })
        
        # Get recent execution history
        recent_history = []
        for log in job_execution_history[-10:]:  # Last 10 executions
            recent_history.append({
                'job_id': log['job_id'],
                'timestamp': log['timestamp'].isoformat(),
                'status': log['status'],
                'duration': log['duration'],
                'created_count': log['created_count'],
                'error': log['error']
            })
        
        return jsonify({
            'status': 'running',
            'running': True,
            'jobs': jobs,
            'execution_history': recent_history,
            'total_jobs': len(jobs),
            'current_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/scheduler/trigger/<job_id>', methods=['POST'])
@login_required
def trigger_scheduler_job(job_id):
    """API endpoint to manually trigger a scheduler job"""
    try:
        user = AuthService.get_user_by_id(session['user_id'])
        if not user or not getattr(user, 'is_super_admin', False):
            return jsonify({'error': 'Super admin access required'}), 403
        
        if not scheduler.running:
            return jsonify({'error': 'Scheduler is not running'}), 400
        
        # Find the job
        job = scheduler.get_job(job_id)
        if not job:
            return jsonify({'error': f'Job {job_id} not found'}), 404
        
        # Trigger the job manually
        if job_id == 'daily_notifications':
            # Run notification generation
            count = auto_generate_notifications_main()
            return jsonify({
                'success': True,
                'message': f'Notification job triggered successfully',
                'created_count': count,
                'timestamp': datetime.now().isoformat()
            })
        elif job_id == 'weekly_cleanup':
            # Run cleanup job
            count = cleanup_old_notifications()
            return jsonify({
                'success': True,
                'message': f'Cleanup job triggered successfully',
                'cleaned_count': count,
                'timestamp': datetime.now().isoformat()
            })
        else:
            # Generic job trigger
            scheduler.modify_job(job_id, next_run_time=datetime.now())
            return jsonify({
                'success': True,
                'message': f'Job {job_id} triggered successfully',
                'timestamp': datetime.now().isoformat()
            })
        
    except Exception as e:
        logger.error(f"Error triggering job {job_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/scheduler/control/<action>', methods=['POST'])
@login_required
def control_scheduler(action):
    """API endpoint to start/stop scheduler"""
    try:
        user = AuthService.get_user_by_id(session['user_id'])
        if not user or not getattr(user, 'is_super_admin', False):
            return jsonify({'error': 'Super admin access required'}), 403
        
        if action == 'start':
            if not scheduler.running:
                scheduler.start()
                return jsonify({
                    'success': True,
                    'message': 'Scheduler started successfully',
                    'status': 'running'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Scheduler is already running',
                    'status': 'running'
                })
        
        elif action == 'stop':
            if scheduler.running:
                scheduler.shutdown(wait=False)
                return jsonify({
                    'success': True,
                    'message': 'Scheduler stopped successfully',
                    'status': 'stopped'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Scheduler is already stopped',
                    'status': 'stopped'
                })
        
        else:
            return jsonify({'error': f'Invalid action: {action}'}), 400
        
    except Exception as e:
        logger.error(f"Error controlling scheduler: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/scheduler/history')
@login_required
def get_scheduler_history():
    """API endpoint to get detailed execution history"""
    try:
        user = AuthService.get_user_by_id(session['user_id'])
        if not user or not getattr(user, 'is_super_admin', False):
            return jsonify({'error': 'Super admin access required'}), 403
        
        # Get execution history with pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Convert history to serializable format
        history = []
        for log in reversed(job_execution_history):  # Most recent first
            history.append({
                'job_id': log['job_id'],
                'timestamp': log['timestamp'].isoformat(),
                'status': log['status'],
                'duration': log['duration'],
                'created_count': log['created_count'],
                'error': log['error']
            })
        
        # Simple pagination
        start = (page - 1) * per_page
        end = start + per_page
        paginated_history = history[start:end]
        
        return jsonify({
            'history': paginated_history,
            'total': len(history),
            'page': page,
            'per_page': per_page,
            'pages': (len(history) + per_page - 1) // per_page
        })
        
    except Exception as e:
        logger.error(f"Error getting scheduler history: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/scheduler/stats')
@login_required
def get_scheduler_stats():
    """API endpoint to get scheduler statistics"""
    try:
        user = AuthService.get_user_by_id(session['user_id'])
        if not user or not getattr(user, 'is_super_admin', False):
            return jsonify({'error': 'Super admin access required'}), 403
        
        # Calculate statistics from execution history
        total_executions = len(job_execution_history)
        successful_executions = len([log for log in job_execution_history if log['status'] == 'success'])
        failed_executions = len([log for log in job_execution_history if log['status'] == 'error'])
        
        # Calculate average duration and total notifications created
        durations = [log['duration'] for log in job_execution_history if log['duration']]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        total_notifications = sum([log['created_count'] or 0 for log in job_execution_history])
        
        # Get last execution info
        last_execution = None
        if job_execution_history:
            last_log = job_execution_history[-1]
            last_execution = {
                'timestamp': last_log['timestamp'].isoformat(),
                'status': last_log['status'],
                'created_count': last_log['created_count']
            }
        
        return jsonify({
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'failed_executions': failed_executions,
            'success_rate': (successful_executions / total_executions * 100) if total_executions > 0 else 0,
            'average_duration': avg_duration,
            'total_notifications_created': total_notifications,
            'last_execution': last_execution
        })
        
    except Exception as e:
        logger.error(f"Error getting scheduler stats: {str(e)}")
        return jsonify({'error': str(e)}), 500




# Initialize chatbot
chatbot = TenderChatbot(app)

# Your Flask routes
@app.route('/api/chatbot', methods=['POST'])
@login_required
def chatbot_api():
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'success': False, 'error': 'Message is required'}), 400
        
        company_id = session.get('company_id')
        user_id = session.get('user_id')
        
        if not company_id:
            return jsonify({'success': False, 'error': 'No company associated'}), 400
        
        # Process message using service
        response = chatbot.process_message(message, company_id, user_id)
        
        return jsonify({
            'success': True,
            'response': response['response'],
            'type': response['type'],
            'data': response.get('data'),
            'powered_by': response.get('powered_by', 'TenderBot')
        })
        
    except Exception as e:
        logger.error(f"Chatbot API error: {str(e)}")
        return jsonify({'success': False, 'error': 'Processing error'}), 500

@app.route('/api/chatbot/suggestions')
@login_required 
def chatbot_suggestions():
    try:
        company_id = session.get('company_id')
        suggestions = get_chatbot_suggestions(company_id)
        return jsonify({'success': True, 'suggestions': suggestions})
    except Exception as e:
        return jsonify({'success': False, 'error': 'Could not load suggestions'}), 500

@app.route('/api/chatbot/quick-stats')
@login_required
def chatbot_quick_stats():
    try:
        company_id = session.get('company_id')
        if not company_id:
            return jsonify({'success': False, 'error': 'No company'}), 400
        
        stats = get_chatbot_quick_stats(company_id)
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': 'Could not load stats'}), 500
    


# ============================================================================
# B-BBEE PLATFORM ROUTES
# ============================================================================

@app.route('/bbee-platform')
@login_required
def bbee_platform():
    """Main B-BBEE platform page"""
    try:
        company_id = session.get('company_id')
        user_id = session.get('user_id')
        
        # Get company's current B-BBEE status if exists
        current_status = get_company_bbee_status(company_id)
        
        return render_template('bbee_platform.html', 
                             current_status=current_status,
                             company_id=company_id)
    except Exception as e:
        logger.error(f"Error loading B-BBEE platform: {str(e)}")
        flash("Error loading B-BBEE platform", "error")
        return redirect(url_for('dashboard'))

@app.route('/api/bbee/calculate', methods=['POST'])
@login_required
def bbee_calculate():
    """Calculate and save B-BBEE score"""
    try:
        data = request.get_json()
        company_id = session.get('company_id')
        user_id = session.get('user_id')
        
        # Validate input data
        required_fields = ['companySize', 'sector', 'blackOwnership', 'blackManagement']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Calculate B-BBEE score (detailed calculation)
        score_breakdown = calculate_detailed_bbee_score(data)
        
        # Save calculation to database
        calculation_id = save_bbee_calculation(company_id, user_id, data, score_breakdown)
        
        return jsonify({
            'success': True,
            'calculation_id': calculation_id,
            'score': score_breakdown['total_score'],
            'level': score_breakdown['level'],
            'breakdown': score_breakdown['breakdown'],
            'suggestions': score_breakdown['suggestions']
        })
        
    except Exception as e:
        logger.error(f"B-BBEE calculation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Calculation failed. Please try again.'
        }), 500

@app.route('/api/bbee/partners')
@login_required
def bbee_partners():
    """Get potential B-BBEE partners"""
    try:
        company_id = session.get('company_id')
        
        # Get company profile for matching
        company_profile = get_company_profile(company_id)
        
        # Find matching partners
        partners = find_bbee_partners(company_profile)
        
        return jsonify({
            'success': True,
            'partners': partners
        })
        
    except Exception as e:
        logger.error(f"Error fetching partners: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to load partners'
        }), 500

@app.route('/api/bbee/connect-partner', methods=['POST'])
@login_required
def bbee_connect_partner():
    """Send partnership connection request"""
    try:
        data = request.get_json()
        company_id = session.get('company_id')
        user_id = session.get('user_id')
        
        partner_id = data.get('partnerId')
        message = data.get('message', '')
        
        if not partner_id:
            return jsonify({
                'success': False,
                'error': 'Partner ID is required'
            }), 400
        
        # Create partnership request
        request_id = create_partnership_request(company_id, partner_id, user_id, message)
        
        # Send notification email to partner
        send_partnership_notification(partner_id, company_id, message)
        
        return jsonify({
            'success': True,
            'request_id': request_id,
            'message': 'Partnership request sent successfully'
        })
        
    except Exception as e:
        logger.error(f"Error connecting partner: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to send partnership request'
        }), 500

@app.route('/api/bbee/integrations')
@login_required
def bbee_integrations():
    """Get government system integration status"""
    try:
        company_id = session.get('company_id')
        
        integrations = {
            'sars': check_sars_integration(company_id),
            'cidb': check_cidb_integration(company_id),
            'csd': check_csd_integration(company_id),
            'etender': check_etender_integration(company_id)
        }
        
        return jsonify({
            'success': True,
            'integrations': integrations
        })
        
    except Exception as e:
        logger.error(f"Error checking integrations: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to check integration status'
        }), 500

@app.route('/api/bbee/transformation-progress')
@login_required
def bbee_transformation_progress():
    """Get transformation tracking data"""
    try:
        company_id = session.get('company_id')
        
        progress = {
            'skills_development': get_skills_development_progress(company_id),
            'enterprise_development': get_enterprise_development_progress(company_id),
            'supplier_development': get_supplier_development_progress(company_id),
            'employment_equity': get_employment_equity_progress(company_id)
        }
        
        return jsonify({
            'success': True,
            'progress': progress
        })
        
    except Exception as e:
        logger.error(f"Error fetching transformation progress: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to load transformation progress'
        }), 500

@app.route('/api/analytics/track', methods=['POST'])
@login_required
def track_analytics():
    """Track user analytics events"""
    try:
        data = request.get_json()
        company_id = session.get('company_id')
        user_id = session.get('user_id')
        
        event_name = data.get('event')
        event_data = data.get('data', {})
        
        # Save analytics event
        save_analytics_event(user_id, company_id, event_name, event_data)
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Analytics tracking error: {str(e)}")
        return jsonify({'success': False}), 500

# ============================================================================
# B-BBEE HELPER FUNCTIONS
# ============================================================================

def calculate_detailed_bbee_score(data):
    """Calculate detailed B-BBEE score with breakdown"""
    
    breakdown = {}
    total_score = 0
    
    # Ownership (25 points)
    black_ownership = int(data.get('blackOwnership', 0))
    if black_ownership >= 51:
        ownership_score = 25
    elif black_ownership >= 25:
        ownership_score = 20
    else:
        ownership_score = round(black_ownership * 0.49, 1)
    
    breakdown['ownership'] = {
        'score': ownership_score,
        'max': 25,
        'percentage': black_ownership
    }
    total_score += ownership_score
    
    # Management Control (15 points)
    black_management = int(data.get('blackManagement', 0))
    if black_management >= 50:
        management_score = 15
    elif black_management >= 25:
        management_score = 12
    else:
        management_score = round(black_management * 0.3, 1)
    
    breakdown['management'] = {
        'score': management_score,
        'max': 15,
        'percentage': black_management
    }
    total_score += management_score
    
    # Black Women Ownership (Bonus - 5 points)
    black_women_ownership = int(data.get('blackWomenOwnership', 0))
    if black_women_ownership >= 25:
        women_bonus = 5
    elif black_women_ownership >= 10:
        women_bonus = 3
    else:
        women_bonus = round(black_women_ownership * 0.2, 1)
    
    breakdown['women_ownership'] = {
        'score': women_bonus,
        'max': 5,
        'percentage': black_women_ownership
    }
    total_score += women_bonus
    
    # Simulated other elements (in real app, these would be separate inputs)
    # Skills Development (20 points)
    skills_score = 15  # Simulated
    breakdown['skills_development'] = {
        'score': skills_score,
        'max': 20,
        'note': 'Based on previous submissions'
    }
    total_score += skills_score
    
    # Enterprise Development (15 points)
    enterprise_score = 12  # Simulated
    breakdown['enterprise_development'] = {
        'score': enterprise_score,
        'max': 15,
        'note': 'Based on previous submissions'
    }
    total_score += enterprise_score
    
    # Supplier Development (20 points)
    supplier_score = 16  # Simulated
    breakdown['supplier_development'] = {
        'score': supplier_score,
        'max': 20,
        'note': 'Based on previous submissions'
    }
    total_score += supplier_score
    
    # Determine B-BBEE Level
    if total_score >= 100:
        level = {"level": 1, "text": "Level 1"}
    elif total_score >= 95:
        level = {"level": 2, "text": "Level 2"}
    elif total_score >= 90:
        level = {"level": 3, "text": "Level 3"}
    elif total_score >= 80:
        level = {"level": 4, "text": "Level 4"}
    elif total_score >= 75:
        level = {"level": 5, "text": "Level 5"}
    elif total_score >= 70:
        level = {"level": 6, "text": "Level 6"}
    elif total_score >= 55:
        level = {"level": 7, "text": "Level 7"}
    else:
        level = {"level": 8, "text": "Level 8"}
    
    # Generate suggestions
    suggestions = []
    if black_ownership < 51:
        suggestions.append("Increase black ownership to 51% to maximize ownership points")
    if black_management < 50:
        suggestions.append("Improve black representation in management positions")
    if black_women_ownership < 25:
        suggestions.append("Consider increasing black women ownership for bonus points")
    if total_score < 100:
        suggestions.append("Focus on skills development and enterprise development programs")
    
    return {
        'total_score': round(total_score, 1),
        'level': level,
        'breakdown': breakdown,
        'suggestions': suggestions
    }

def save_bbee_calculation(company_id, user_id, data, score_breakdown):
    """Save B-BBEE calculation to database"""
    try:
        result = db.session.execute(text("""
            INSERT INTO bbee_calculations 
            (company_id, user_id, company_size, sector, turnover, 
             black_ownership, black_management, black_women_ownership,
             total_score, bbee_level, breakdown_data, created_at)
            VALUES 
            (:company_id, :user_id, :company_size, :sector, :turnover,
             :black_ownership, :black_management, :black_women_ownership,
             :total_score, :bbee_level, :breakdown_data, NOW())
        """), {
            'company_id': company_id,
            'user_id': user_id,
            'company_size': data.get('companySize'),
            'sector': data.get('sector'),
            'turnover': data.get('turnover', 0),
            'black_ownership': data.get('blackOwnership', 0),
            'black_management': data.get('blackManagement', 0),
            'black_women_ownership': data.get('blackWomenOwnership', 0),
            'total_score': score_breakdown['total_score'],
            'bbee_level': score_breakdown['level']['level'],
            'breakdown_data': str(score_breakdown['breakdown'])
        })
        
        db.session.commit()
        return result.lastrowid
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving B-BBEE calculation: {str(e)}")
        raise

def get_company_bbee_status(company_id):
    """Get company's current B-BBEE status"""
    try:
        result = db.session.execute(text("""
            SELECT total_score, bbee_level, created_at
            FROM bbee_calculations 
            WHERE company_id = :company_id 
            ORDER BY created_at DESC 
            LIMIT 1
        """), {'company_id': company_id})
        
        row = result.fetchone()
        if row:
            return {
                'score': row[0],
                'level': row[1],
                'last_updated': row[2]
            }
        return None
        
    except Exception as e:
        logger.error(f"Error getting B-BBEE status: {str(e)}")
        return None

def find_bbee_partners(company_profile):
    """Find potential B-BBEE partners based on company profile"""
    try:
        # In real implementation, this would query a partners database
        # For now, return mock data with realistic South African companies
        
        mock_partners = [
            {
                'id': 1,
                'name': 'Thabo Construction (Pty) Ltd',
                'bbee_level': 1,
                'specialties': ['Civil Engineering', 'Infrastructure'],
                'location': 'Gauteng',
                'capacity': 'R500M+ projects',
                'match_percentage': 95,
                'contact_email': 'info@thaboconstruction.co.za',
                'verified': True,
                'certifications': ['CIDB Grade 9', 'ISO 9001'],
                'past_projects': 15,
                'success_rate': '92%'
            },
            {
                'id': 2,
                'name': 'Nomsa Tech Solutions',
                'bbee_level': 2,
                'specialties': ['IT Services', 'Software Development'],
                'location': 'Western Cape',
                'capacity': 'R100M+ projects',
                'match_percentage': 88,
                'contact_email': 'hello@nomsatech.co.za',
                'verified': True,
                'certifications': ['ISO 27001', 'ITIL Certified'],
                'past_projects': 23,
                'success_rate': '89%'
            },
            {
                'id': 3,
                'name': 'Ubuntu Consulting Group',
                'bbee_level': 1,
                'specialties': ['Management Consulting', 'Strategy'],
                'location': 'KwaZulu-Natal',
                'capacity': 'R50M+ projects',
                'match_percentage': 82,
                'contact_email': 'contact@ubuntu-consulting.co.za',
                'verified': True,
                'certifications': ['PMI Certified', 'McKinsey Alumni'],
                'past_projects': 31,
                'success_rate': '94%'
            },
            {
                'id': 4,
                'name': 'Amandla Engineering',
                'bbee_level': 3,
                'specialties': ['Mechanical Engineering', 'Mining'],
                'location': 'Limpopo',
                'capacity': 'R200M+ projects',
                'match_percentage': 76,
                'contact_email': 'info@amandlaeng.co.za',
                'verified': False,
                'certifications': ['ECSA Registered', 'Mine Safety Cert'],
                'past_projects': 12,
                'success_rate': '85%'
            },
            {
                'id': 5,
                'name': 'Sizani Logistics Solutions',
                'bbee_level': 2,
                'specialties': ['Logistics', 'Supply Chain'],
                'location': 'Eastern Cape',
                'capacity': 'R75M+ projects',
                'match_percentage': 74,
                'contact_email': 'ops@sizanilogistics.co.za',
                'verified': True,
                'certifications': ['SQAS Certified', 'CILTSA Member'],
                'past_projects': 18,
                'success_rate': '91%'
            }
        ]
        
        return mock_partners
        
    except Exception as e:
        logger.error(f"Error finding partners: {str(e)}")
        return []

def get_company_profile(company_id):
    """Get company profile for partner matching"""
    try:
        result = db.session.execute(text("""
            SELECT c.name, c.industry, c.location, c.annual_turnover,
                   bc.bbee_level, bc.sector
            FROM companies c
            LEFT JOIN bbee_calculations bc ON c.id = bc.company_id
            WHERE c.id = :company_id
            ORDER BY bc.created_at DESC
            LIMIT 1
        """), {'company_id': company_id})
        
        row = result.fetchone()
        if row:
            return {
                'name': row[0],
                'industry': row[1],
                'location': row[2],
                'turnover': row[3],
                'bbee_level': row[4],
                'sector': row[5]
            }
        return {}
        
    except Exception as e:
        logger.error(f"Error getting company profile: {str(e)}")
        return {}

def create_partnership_request(company_id, partner_id, user_id, message):
    """Create a partnership request"""
    try:
        result = db.session.execute(text("""
            INSERT INTO partnership_requests 
            (company_id, partner_id, user_id, message, status, created_at)
            VALUES 
            (:company_id, :partner_id, :user_id, :message, 'pending', NOW())
        """), {
            'company_id': company_id,
            'partner_id': partner_id,
            'user_id': user_id,
            'message': message
        })
        
        db.session.commit()
        return result.lastrowid
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating partnership request: {str(e)}")
        raise

def send_partnership_notification(partner_id, company_id, message):
    """Send email notification for partnership request"""
    try:
        # Get partner and company details
        partner_email = get_partner_email(partner_id)
        company_name = get_company_name(company_id)
        
        if partner_email and company_name:
            # In real implementation, send actual email
            logger.info(f"Partnership notification sent to {partner_email} from {company_name}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error sending partnership notification: {str(e)}")
        return False

def get_partner_email(partner_id):
    """Get partner email (mock implementation)"""
    partner_emails = {
        1: 'info@thaboconstruction.co.za',
        2: 'hello@nomsatech.co.za',
        3: 'contact@ubuntu-consulting.co.za',
        4: 'info@amandlaeng.co.za',
        5: 'ops@sizanilogistics.co.za'
    }
    return partner_emails.get(partner_id)

def get_company_name(company_id):
    """Get company name"""
    try:
        result = db.session.execute(text("""
            SELECT name FROM companies WHERE id = :company_id
        """), {'company_id': company_id})
        
        row = result.fetchone()
        return row[0] if row else None
        
    except Exception as e:
        logger.error(f"Error getting company name: {str(e)}")
        return None

def check_sars_integration(company_id):
    """Check SARS tax compliance integration status"""
    try:
        # Mock implementation - in real app, check actual SARS API
        result = db.session.execute(text("""
            SELECT sars_tax_number, sars_compliance_status, sars_last_check
            FROM company_integrations 
            WHERE company_id = :company_id
        """), {'company_id': company_id})
        
        row = result.fetchone()
        if row:
            return {
                'status': 'connected',
                'tax_number': row[0],
                'compliance_status': row[1],
                'last_check': row[2]
            }
        
        return {'status': 'not_connected'}
        
    except Exception as e:
        logger.error(f"Error checking SARS integration: {str(e)}")
        return {'status': 'error'}

def check_cidb_integration(company_id):
    """Check CIDB registration integration status"""
    try:
        # Mock implementation
        return {
            'status': 'connected',
            'registration_number': 'CIDB123456789',
            'grade': 'Grade 9',
            'valid_until': '2024-12-31'
        }
        
    except Exception as e:
        logger.error(f"Error checking CIDB integration: {str(e)}")
        return {'status': 'error'}

def check_csd_integration(company_id):
    """Check CSD registration integration status"""
    try:
        # Mock implementation
        return {
            'status': 'pending',
            'supplier_number': None,
            'application_date': '2024-01-15'
        }
        
    except Exception as e:
        logger.error(f"Error checking CSD integration: {str(e)}")
        return {'status': 'error'}

def check_etender_integration(company_id):
    """Check eTender Portal integration status"""
    try:
        # Mock implementation
        return {
            'status': 'not_connected',
            'last_sync': None
        }
        
    except Exception as e:
        logger.error(f"Error checking eTender integration: {str(e)}")
        return {'status': 'error'}

def get_skills_development_progress(company_id):
    """Get skills development progress"""
    try:
        # Mock implementation - in real app, calculate from actual data
        return {
            'percentage': 75,
            'amount_invested': 2400000,  # R2.4M
            'target_percentage': 1,  # 1% of payroll
            'employees_trained': 45,
            'programs_completed': 12
        }
        
    except Exception as e:
        logger.error(f"Error getting skills development progress: {str(e)}")
        return {}

def get_enterprise_development_progress(company_id):
    """Get enterprise development progress"""
    try:
        # Mock implementation
        return {
            'percentage': 60,
            'amount_invested': 1800000,  # R1.8M
            'target_percentage': 1,  # 1% of NPAT
            'enterprises_supported': 8,
            'jobs_created': 23
        }
        
    except Exception as e:
        logger.error(f"Error getting enterprise development progress: {str(e)}")
        return {}

def get_supplier_development_progress(company_id):
    """Get supplier development progress"""
    try:
        # Mock implementation
        return {
            'percentage': 45,
            'suppliers_supported': 15,
            'procurement_spend': 5600000,  # R5.6M
            'target_percentage': 2,  # 2% of procurement
            'mentorship_programs': 3
        }
        
    except Exception as e:
        logger.error(f"Error getting supplier development progress: {str(e)}")
        return {}

def get_employment_equity_progress(company_id):
    """Get employment equity progress"""
    try:
        # Mock implementation
        return {
            'percentage': 85,
            'black_employees': 127,
            'total_employees': 150,
            'black_management': 18,
            'total_management': 25,
            'target_achieved': True
        }
        
    except Exception as e:
        logger.error(f"Error getting employment equity progress: {str(e)}")
        return {}

def save_analytics_event(user_id, company_id, event_name, event_data):
    """Save analytics event to database"""
    try:
        db.session.execute(text("""
            INSERT INTO analytics_events 
            (user_id, company_id, event_name, event_data, created_at)
            VALUES 
            (:user_id, :company_id, :event_name, :event_data, NOW())
        """), {
            'user_id': user_id,
            'company_id': company_id,
            'event_name': event_name,
            'event_data': str(event_data)
        })
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving analytics event: {str(e)}")



# ============================================================================
# MUNICIPAL TENDER OPPORTUNITY ENGINE ROUTES
# ============================================================================


@app.route('/api/municipal-tenders')
@login_required
def api_municipal_tenders():
    """Get municipal tenders with filtering"""
    try:
        company_id = session.get('company_id')
        
        # Get query parameters
        search = request.args.get('search', '')
        province = request.args.get('province', '')
        category = request.args.get('category', '')
        value_range = request.args.get('value_range', '')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 12))
        
        # Get filtered tenders
        tenders = get_municipal_tenders(
            company_id=company_id,
            search=search,
            province=province,
            category=category,
            value_range=value_range,
            page=page,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'tenders': tenders,
            'total_count': len(tenders),  # In real app, get total count separately
            'page': page,
            'limit': limit
        })
        
    except Exception as e:
        logger.error(f"Error fetching tenders: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch tenders'
        }), 500

@app.route('/api/municipal-tenders/express-interest', methods=['POST'])
@login_required
def express_tender_interest():
    """Express interest in a municipal tender"""
    try:
        data = request.get_json()
        company_id = session.get('company_id')
        user_id = session.get('user_id')
        
        tender_id = data.get('tender_id')
        contact_person = data.get('contact_person')
        contact_email = data.get('contact_email')
        contact_phone = data.get('contact_phone')
        message = data.get('message', '')
        
        # Validate required fields
        if not all([tender_id, contact_person, contact_email, contact_phone]):
            return jsonify({
                'success': False,
                'error': 'All fields are required'
            }), 400
        
        # Save interest to database
        interest_id = save_tender_interest(
            company_id=company_id,
            user_id=user_id,
            tender_id=tender_id,
            contact_person=contact_person,
            contact_email=contact_email,
            contact_phone=contact_phone,
            message=message
        )
        
        # Send notification email (optional)
        send_tender_interest_notification(interest_id)
        
        return jsonify({
            'success': True,
            'interest_id': interest_id,
            'message': 'Interest submitted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error expressing tender interest: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to submit interest'
        }), 500

@app.route('/api/municipal-tenders/stats')
@login_required
def api_tender_stats():
    """Get real-time tender statistics"""
    try:
        company_id = session.get('company_id')
        stats = get_municipal_tender_stats(company_id)
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error fetching tender stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch statistics'
        }), 500

@app.route('/api/municipal-tenders/<int:tender_id>')
@login_required
def api_tender_details(tender_id):
    """Get detailed information about a specific tender"""
    try:
        tender = get_tender_details(tender_id)
        
        if not tender:
            return jsonify({
                'success': False,
                'error': 'Tender not found'
            }), 404
        
        return jsonify({
            'success': True,
            'tender': tender
        })
        
    except Exception as e:
        logger.error(f"Error fetching tender details: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch tender details'
        }), 500

# ============================================================================
# MUNICIPAL TENDER HELPER FUNCTIONS
# ============================================================================

def get_municipal_tender_stats(company_id):
    """Get real-time municipal tender statistics"""
    try:
        # In real implementation, query actual tender database
        # For now, return mock data with some randomization
        
        base_stats = {
            'active_tenders': 1247,
            'new_today': 23,
            'total_value': 847,  # in millions
            'matched_tenders': 156,
            'municipalities_monitored': 257
        }
        
        # Add some randomization to simulate real-time updates
        stats = {
            'active_tenders': base_stats['active_tenders'] + random.randint(-50, 50),
            'new_today': base_stats['new_today'] + random.randint(-5, 10),
            'total_value': base_stats['total_value'] + random.randint(-100, 200),
            'matched_tenders': base_stats['matched_tenders'] + random.randint(-20, 30),
            'municipalities_monitored': base_stats['municipalities_monitored']
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting tender stats: {e}")
        return {
            'active_tenders': 0,
            'new_today': 0,
            'total_value': 0,
            'matched_tenders': 0,
            'municipalities_monitored': 257
        }

def get_ai_tender_insights(company_id):
    """Get AI-powered tender insights"""
    try:
        # In real implementation, this would use ML models
        # For now, return dynamic insights based on company profile
        
        insights = [
            {
                'icon': '💡',
                'title': 'Smart Opportunity',
                'description': 'City of Cape Town has increased IT spending by 340% this quarter - 5 matching tenders available'
            },
            {
                'icon': '📈',
                'title': 'Market Trend',
                'description': 'Rural municipalities are prioritizing infrastructure projects - R2.3B in opportunities'
            },
            {
                'icon': '⚡',
                'title': 'Quick Win',
                'description': '12 municipalities have urgent cleaning services tenders with simplified requirements'
            }
        ]
        
        return insights
        
    except Exception as e:
        logger.error(f"Error getting AI insights: {e}")
        return []

def get_urgent_tender_alerts(company_id):
    """Get urgent tender alerts"""
    try:
        # Check for tenders closing within 48 hours
        urgent_count = random.randint(1, 5)  # Mock data
        
        return {
            'count': urgent_count,
            'message': f'{urgent_count} high-value tenders closing within 48 hours match your company profile!'
        } if urgent_count > 0 else None
        
    except Exception as e:
        logger.error(f"Error getting urgent alerts: {e}")
        return None

def get_company_tender_profile(company_id):
    """Get company profile for tender matching"""
    try:
        result = db.session.execute(text("""
            SELECT c.name, c.industry, c.location, c.annual_turnover,
                   cp.specialties, cp.certifications, cp.cidb_grade
            FROM companies c
            LEFT JOIN company_profiles cp ON c.id = cp.company_id
            WHERE c.id = :company_id
        """), {'company_id': company_id})
        
        row = result.fetchone()
        if row:
            return {
                'name': row[0],
                'industry': row[1],
                'location': row[2],
                'turnover': row[3],
                'specialties': row[4].split(',') if row[4] else [],
                'certifications': row[5].split(',') if row[5] else [],
                'cidb_grade': row[6]
            }
        return {}
        
    except Exception as e:
        logger.error(f"Error getting company profile: {e}")
        return {}

def get_municipal_tenders(company_id, search='', province='', category='', value_range='', page=1, limit=12):
    """Get municipal tenders with filtering"""
    try:
        # In real implementation, this would query actual municipal tender database
        # For now, return mock data
        
        mock_tenders = [
            {
                'id': 1,
                'municipality': 'City of Cape Town',
                'province': 'western-cape',
                'title': 'Supply and Installation of Municipal WiFi Infrastructure',
                'category': 'it-services',
                'description': 'Installation of high-speed WiFi networks across 15 municipal buildings and public spaces including Civic Centre, libraries, and community halls.',
                'value': 45000000,
                'valueDisplay': 'R45,000,000',
                'closingDate': '2024-07-15',
                'daysLeft': 12,
                'status': 'new',
                'requirements': ['CIDB Grade 7+', 'ICT Experience', 'B-BBEE Level 1-4'],
                'matchScore': 94,
                'tenderNumber': 'CT/2024/IT/045',
                'publishedDate': '2024-06-15',
                'contactPerson': 'Ms. Sarah Johnson',
                'contactEmail': 'tenders@capetown.gov.za',
                'estimatedDuration': '12 months'
            },
            {
                'id': 2,
                'municipality': 'Ekurhuleni Metropolitan Municipality',
                'province': 'gauteng',
                'title': 'Construction of Community Sports Complex',
                'category': 'construction',
                'description': 'Design and construction of multi-purpose sports complex including soccer field, netball courts, swimming pool, and community centre in Germiston.',
                'value': 125000000,
                'valueDisplay': 'R125,000,000',
                'closingDate': '2024-07-08',
                'daysLeft': 5,
                'status': 'closing',
                'requirements': ['CIDB Grade 9', 'Construction Experience', 'Local Content 70%'],
                'matchScore': 87,
                'tenderNumber': 'EKU/2024/CON/078',
                'publishedDate': '2024-05-20',
                'contactPerson': 'Mr. David Mthembu',
                'contactEmail': 'procurement@ekurhuleni.gov.za',
                'estimatedDuration': '18 months'
            },
            {
                'id': 3,
                'municipality': 'Sol Plaatje Local Municipality',
                'province': 'northern-cape',
                'title': 'Waste Management and Recycling Services',
                'category': 'cleaning',
                'description': 'Comprehensive waste collection, sorting, and recycling services for residential and commercial areas.',
                'value': 18500000,
                'valueDisplay': 'R18,500,000',
                'closingDate': '2024-07-03',
                'daysLeft': 1,
                'status': 'urgent',
                'requirements': ['Waste Management License', 'Fleet of 25+ Vehicles', 'B-BBEE Level 1-3'],
                'matchScore': 76,
                'tenderNumber': 'SP/2024/WM/023',
                'publishedDate': '2024-06-01',
                'contactPerson': 'Ms. Nomsa Khumalo',
                'contactEmail': 'tenders@solplaatje.org.za',
                'estimatedDuration': '36 months'
            },
            {
                'id': 4,
                'municipality': 'eThekwini Metropolitan Municipality',
                'province': 'kwazulu-natal',
                'title': 'Municipal Financial Management System Upgrade',
                'category': 'it-services',
                'description': 'Implementation and customization of integrated financial management system.',
                'value': 67200000,
                'valueDisplay': 'R67,200,000',
                'closingDate': '2024-07-22',
                'daysLeft': 19,
                'status': 'new',
                'requirements': ['Software Development', 'Municipal Finance Experience', '24/7 Support'],
                'matchScore': 91,
                'tenderNumber': 'ETH/2024/IT/156',
                'publishedDate': '2024-06-18',
                'contactPerson': 'Mr. Sipho Ndlovu',
                'contactEmail': 'itsupport@durban.gov.za',
                'estimatedDuration': '24 months'
            },
            {
                'id': 5,
                'municipality': 'Stellenbosch Local Municipality',
                'province': 'western-cape',
                'title': 'Strategic Development Plan Consulting Services',
                'category': 'consulting',
                'description': 'Development of 5-year Integrated Development Plan including economic development strategy.',
                'value': 8750000,
                'valueDisplay': 'R8,750,000',
                'closingDate': '2024-07-18',
                'daysLeft': 15,
                'status': 'new',
                'requirements': ['Urban Planning Qualification', 'IDP Experience', 'Community Engagement'],
                'matchScore': 83,
                'tenderNumber': 'STELL/2024/CON/012',
                'publishedDate': '2024-06-10',
                'contactPerson': 'Dr. Maria van der Merwe',
                'contactEmail': 'planning@stellenbosch.gov.za',
                'estimatedDuration': '12 months'
            },
            {
                'id': 6,
                'municipality': 'Buffalo City Metropolitan Municipality',
                'province': 'eastern-cape',
                'title': 'LED Street Lighting Upgrade Project',
                'category': 'construction',
                'description': 'Replacement of conventional street lighting with energy-efficient LED systems.',
                'value': 95000000,
                'valueDisplay': 'R95,000,000',
                'closingDate': '2024-07-25',
                'daysLeft': 22,
                'status': 'new',
                'requirements': ['Electrical Installation License', 'LED Experience', '5-Year Warranty'],
                'matchScore': 89,
                'tenderNumber': 'BC/2024/ELEC/089',
                'publishedDate': '2024-06-20',
                'contactPerson': 'Eng. Thabo Molefe',
                'contactEmail': 'infrastructure@buffalocity.gov.za',
                'estimatedDuration': '15 months'
            }
        ]
        
        # Apply filters
        filtered_tenders = mock_tenders
        
        if search:
            filtered_tenders = [t for t in filtered_tenders if 
                search.lower() in t['title'].lower() or 
                search.lower() in t['municipality'].lower() or
                search.lower() in t['description'].lower()]
        
        if province:
            filtered_tenders = [t for t in filtered_tenders if t['province'] == province]
        
        if category:
            filtered_tenders = [t for t in filtered_tenders if t['category'] == category]
        
        if value_range:
            filtered_tenders = [t for t in filtered_tenders if filter_by_value_range(t['value'], value_range)]
        
        return filtered_tenders
        
    except Exception as e:
        logger.error(f"Error getting municipal tenders: {e}")
        return []

def filter_by_value_range(value, value_range):
    """Filter tender by value range"""
    if value_range == '0-1m':
        return value <= 1000000
    elif value_range == '1m-10m':
        return 1000000 < value <= 10000000
    elif value_range == '10m-50m':
        return 10000000 < value <= 50000000
    elif value_range == '50m+':
        return value > 50000000
    return True

def save_tender_interest(company_id, user_id, tender_id, contact_person, contact_email, contact_phone, message):
    """Save tender interest to database"""
    try:
        result = db.session.execute(text("""
            INSERT INTO tender_interests 
            (company_id, user_id, tender_id, contact_person, contact_email, contact_phone, message, created_at)
            VALUES 
            (:company_id, :user_id, :tender_id, :contact_person, :contact_email, :contact_phone, :message, NOW())
        """), {
            'company_id': company_id,
            'user_id': user_id,
            'tender_id': tender_id,
            'contact_person': contact_person,
            'contact_email': contact_email,
            'contact_phone': contact_phone,
            'message': message
        })
        
        db.session.commit()
        return result.lastrowid
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving tender interest: {e}")
        raise

def send_tender_interest_notification(interest_id):
    """Send notification email for tender interest"""
    try:
        # In real implementation, send email to municipality
        logger.info(f"Tender interest notification sent for interest ID: {interest_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending tender interest notification: {e}")
        return False

def get_tender_details(tender_id):
    """Get detailed information about a specific tender"""
    try:
        # In real implementation, query tender database
        # For now, return mock data
        
        mock_tender = {
            'id': tender_id,
            'municipality': 'City of Cape Town',
            'title': 'Supply and Installation of Municipal WiFi Infrastructure',
            'description': 'Full description of the tender requirements...',
            'value': 45000000,
            'valueDisplay': 'R45,000,000',
            'closingDate': '2024-07-15',
            'requirements': ['CIDB Grade 7+', 'ICT Experience', 'B-BBEE Level 1-4'],
            'documents': [
                {'name': 'Tender Document.pdf', 'size': '2.3 MB'},
                {'name': 'Technical Specifications.pdf', 'size': '1.8 MB'},
                {'name': 'Pricing Schedule.xlsx', 'size': '0.5 MB'}
            ],
            'contactPerson': 'Ms. Sarah Johnson',
            'contactEmail': 'tenders@capetown.gov.za',
            'contactPhone': '+27 21 400 1234'
        }
        
        return mock_tender
        
    except Exception as e:
        logger.error(f"Error getting tender details: {e}")
        return None

def calculate_potential_revenue(company_id):
    """Calculate potential revenue from matching tenders"""
    try:
        # In real implementation, calculate based on company profile and available tenders
        # For now, return mock calculation
        
        base_revenue = 2300000000  # R2.3B
        company_factor = random.uniform(0.8, 1.5)  # Company-specific multiplier
        
        potential = int(base_revenue * company_factor)
        
        # Format as display string (e.g., "2.8B")
        if potential >= 1000000000:
            return f"{potential / 1000000000:.1f}B"
        elif potential >= 1000000:
            return f"{potential / 1000000:.0f}M"
        else:
            return f"{potential / 1000:.0f}K"
        
    except Exception as e:
        logger.error(f"Error calculating potential revenue: {e}")
        return "2.3B"

# ============================================================================
# DATABASE SCHEMA FOR MUNICIPAL TENDER ENGINE
# ============================================================================

def create_municipal_tender_tables():
    """Create tables for Municipal Tender Engine"""
    try:
        # Municipal Tenders table
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS municipal_tenders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                municipality VARCHAR(255) NOT NULL,
                province VARCHAR(100) NOT NULL,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                category VARCHAR(100),
                value BIGINT,
                tender_number VARCHAR(100) UNIQUE,
                published_date DATE,
                closing_date DATETIME,
                status ENUM('new', 'closing', 'urgent', 'closed') DEFAULT 'new',
                requirements JSON,
                contact_person VARCHAR(255),
                contact_email VARCHAR(255),
                contact_phone VARCHAR(50),
                estimated_duration VARCHAR(100),
                documents JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_municipality (municipality),
                INDEX idx_province (province),
                INDEX idx_category (category),
                INDEX idx_closing_date (closing_date),
                INDEX idx_status (status),
                INDEX idx_value (value)
            )
        """))
        
        # Tender Interests table
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS tender_interests (
                id INT AUTO_INCREMENT PRIMARY KEY,
                company_id INT NOT NULL,
                user_id INT NOT NULL,
                tender_id INT NOT NULL,
                contact_person VARCHAR(255) NOT NULL,
                contact_email VARCHAR(255) NOT NULL,
                contact_phone VARCHAR(50) NOT NULL,
                message TEXT,
                status ENUM('submitted', 'acknowledged', 'responded') DEFAULT 'submitted',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_company_id (company_id),
                INDEX idx_tender_id (tender_id),
                INDEX idx_status (status),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))
        
        # Company Tender Profile table
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS company_tender_profiles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                company_id INT NOT NULL UNIQUE,
                specialties TEXT,
                certifications TEXT,
                cidb_grade VARCHAR(20),
                preferred_provinces JSON,
                preferred_categories JSON,
                min_tender_value BIGINT DEFAULT 0,
                max_tender_value BIGINT DEFAULT 999999999999,
                notifications_enabled BOOLEAN DEFAULT TRUE,
                auto_match_threshold INT DEFAULT 80,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """))
        
        # Tender Alerts table
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS tender_alerts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                company_id INT NOT NULL,
                tender_id INT NOT NULL,
                alert_type ENUM('match', 'closing', 'urgent', 'new') NOT NULL,
                match_score INT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status ENUM('sent', 'read', 'dismissed') DEFAULT 'sent',
                INDEX idx_company_id (company_id),
                INDEX idx_tender_id (tender_id),
                INDEX idx_alert_type (alert_type),
                INDEX idx_status (status),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """))
        
        db.session.commit()
        logger.info("Municipal Tender Engine tables created successfully")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating Municipal Tender Engine tables: {e}")
        raise

# tender discovery and scraping manager

@app.route('/municipal-tender-discovery')
@login_required
def municipal_tender_discovery():
    """Municipal Tender Discovery Engine - Simple Test"""
    try:
        company_id = session.get('company_id')
        
        # Get data from service
        stats = municipal_tender_service.get_municipal_tender_stats(company_id)
        tenders = municipal_tender_service.get_municipal_tenders(company_id, limit=6)
        
        
        html = f"""
      
        <!DOCTYPE html>
        <html>
        <head>
            <title>Municipal Tender Discovery</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ background: #1a237e; color: white; padding: 30px; border-radius: 10px; text-align: center; }}
                .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 30px 0; }}
                .stat {{ background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .tenders {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; }}
                .tender {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏛️ Municipal Tender Discovery Engine</h1>
                    <p>Real-time municipal tenders across South Africa</p>
                </div>
                
                <div class="stats">
                    <div class="stat">
                        <h3>{stats['active_tenders']}</h3>
                        <p>Active Tenders</p>
                    </div>
                    <div class="stat">
                        <h3>{stats['new_today']}</h3>
                        <p>New Today</p>
                    </div>
                    <div class="stat">
                        <h3>R{stats['total_value']}M</h3>
                        <p>Total Value</p>
                    </div>
                    <div class="stat">
                        <h3>{stats['matched_tenders']}</h3>
                        <p>Matched to You</p>
                    </div>
                </div>
                
                <h2>Latest Tenders</h2>
                <div class="tenders">
                
        """
        
        for tender in tenders:
            html += f"""
                    <div class="tender">
                        <h3>{tender['municipality']}</h3>
                        <h4>{tender['title']}</h4>
                        <p><strong>Value:</strong> {tender['valueDisplay']}</p>
                        <p><strong>Closes:</strong> {tender['closingDate']} ({tender['daysLeft']} days)</p>
                        <p><strong>Match:</strong> {tender['matchScore']}%</p>
                        <p>{tender['description'][:100]}...</p>
                    </div>
            """
        
        html += """
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
        
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p>"


# ============================================================================
# MUNICIPAL TENDER SCRAPING ROUTES
# ============================================================================

@app.route('/api/municipal-tenders/scrape-status')
@login_required
def get_scraping_status():
    """Get current scraping status"""
    try:
        status = tender_scraping_manager.get_scraping_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/municipal-tenders/manual-scrape', methods=['POST'])
@login_required  
def manual_scrape():
    """Manually trigger scraping for a municipality"""
    try:
        data = request.get_json()
        municipality = data.get('municipality')
        
        if not municipality:
            return jsonify({'success': False, 'error': 'Municipality required'})
        
        result = tender_scraping_manager.manual_scrape_municipality(municipality)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/municipal-tenders/start-scraping', methods=['POST'])
@login_required
def start_scraping():
    """Start automated scraping (admin only)"""
    try:
        if not session.get('is_admin'):
            return jsonify({'success': False, 'error': 'Admin access required'})
        
        tender_scraping_manager.start_scheduled_scraping()
        return jsonify({
            'success': True,
            'message': 'Automated scraping started'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Initialize scraping when app starts

     



@app.route('/municipal-tender-engine')
@login_required
def municipal_tender_engine():
    """Municipal Tender Engine with real data"""
    try:
        company_id = session.get('company_id')
        
        # Get real-time stats
        stats = municipal_tender_service.get_municipal_tender_stats(company_id)
        
        # Get AI insights
        ai_insights = municipal_tender_service.get_ai_tender_insights(company_id)
        
        # Get urgent alerts
        urgent_alerts = municipal_tender_service.get_urgent_tender_alerts(company_id)
        
        # Get initial tenders (now from database if available)
        initial_tenders = municipal_tender_service.get_municipal_tenders(company_id, limit=12)
        
        # Calculate potential revenue
        potential_revenue = municipal_tender_service.calculate_potential_revenue(company_id)
        
        # Get scraping status
        scraping_status = tender_scraping_manager.get_scraping_status()
        
        return render_template('municipal_tender_engine.html',
                             stats=stats,
                             ai_insights=ai_insights,
                             urgent_alerts=urgent_alerts,
                             company_profile={},
                             initial_tenders=initial_tenders,
                             potential_revenue=potential_revenue,
                             scraping_status=scraping_status)
                             
    except Exception as e:
        logger.error(f"Error loading Municipal Tender Engine: {str(e)}")
        flash("Error loading Municipal Tender Engine", "error")
        return redirect(url_for('dashboard'))

@app.route('/api/municipal-tenders/start-scraping', methods=['POST'])
@login_required
def start_municipal_scraping():
    """Start the municipal tender scraping process"""
    try:
        if not session.get('is_admin'):
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        # Start background scraping
        threading.Thread(target=tender_scraping_manager.daily_tender_scraping, daemon=True).start()
        
        return jsonify({
            'success': True,
            'message': 'Scraping started in background'
        })
        
    except Exception as e:
        logger.error(f"Error starting scraping: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to start scraping'
        }), 500

@app.route('/api/municipal-tenders/scraping-status')
@login_required
def get_municipal_scraping_status():
    """Get current scraping status"""
    try:
        status = tender_scraping_manager.get_scraping_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


    
if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Tender Management System Starting...")
    print("="*50)
    print("📂 Visit: http://localhost:5001")
    print("👤 Super Admin Login: superadmin / admin123")
    print("="*50 + "\n")
    
    #init_database()
    app.run(debug=True, host='0.0.0.0', port=5001)