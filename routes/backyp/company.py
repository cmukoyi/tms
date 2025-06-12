# routes/company.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from utils.decorators import login_required
from services.company_module_service import CompanyModuleService
from services import AuthService
from models import Company, User, Tender, CompanyModule, ModuleDefinition

company_bp = Blueprint('company', __name__)

@company_bp.route('/my-company/modules')
@login_required
def my_company_modules():
    """View modules for current user's company"""
    user = AuthService.get_user_by_id(session['user_id'])
    
    # Get the current user's company
    if not user.company_id:
        flash('No company associated with your account', 'error')
        return redirect(url_for('main.home'))
    
    company = Company.query.get_or_404(user.company_id)
    
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

@company_bp.route('/my-company/modules/request', methods=['POST'])
@login_required
def request_module():
    """Request a module to be enabled for the company"""
    try:
        user = AuthService.get_user_by_id(session['user_id'])
        data = request.get_json()
        module_name = data.get('module_name')
        notes = data.get('notes', '')
        
        if not module_name:
            return jsonify({'success': False, 'message': 'Module name is required'})
        
        # Check if user has permission (company admin or higher)
        if user.role.name not in ['Company Admin', 'Super Admin']:
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

@company_bp.route('/my-company-modules')
@login_required
def my_company_modules_alt():
    """Alternative route - View modules available to the current user's company"""
    user = AuthService.get_user_by_id(session['user_id'])
    
    if not user.company_id:
        flash('No company associated with your account', 'error')
        return redirect(url_for('main.home'))
    
    company = Company.query.get_or_404(user.company_id)
    
    # Get all available modules (you can move this to a database table later)
    available_modules = [
        {
            'module_name': 'tender_management',
            'display_name': 'Tender Management',
            'description': 'Create, manage and track tenders',
            'category': 'core',
            'monthly_price': 0.0,
            'is_core': True,
            'is_enabled': True  # Core modules are always enabled
        },
        {
            'module_name': 'user_management',
            'display_name': 'User Management', 
            'description': 'Manage company users and permissions',
            'category': 'core',
            'monthly_price': 0.0,
            'is_core': True,
            'is_enabled': True  # Core modules are always enabled
        },
        {
            'module_name': 'document_management',
            'display_name': 'Document Management',
            'description': 'Upload, organize and manage documents',
            'category': 'feature',
            'monthly_price': 299.99,
            'is_core': False,
            'is_enabled': True  # You can set this based on company modules
        },
        {
            'module_name': 'reporting',
            'display_name': 'Advanced Reporting',
            'description': 'Advanced analytics and custom reports',
            'category': 'feature',
            'monthly_price': 499.99,
            'is_core': False,
            'is_enabled': False
        },
        {
            'module_name': 'custom_fields',
            'display_name': 'Custom Fields',
            'description': 'Create custom fields for tenders',
            'category': 'feature',
            'monthly_price': 199.99,
            'is_core': False,
            'is_enabled': False
        },
        {
            'module_name': 'notes_comments',
            'display_name': 'Notes & Comments',
            'description': 'Add notes and comments to tenders',
            'category': 'feature',
            'monthly_price': 149.99,
            'is_core': False,
            'is_enabled': True
        }
    ]
    
    # Calculate total monthly cost
    monthly_cost = sum([m['monthly_price'] for m in available_modules if m['is_enabled']])
    
    return render_template('my_company_modules.html', 
                         company=company,
                         modules=available_modules,
                         monthly_cost=monthly_cost)

@company_bp.route('/company-notes')
@login_required
def company_notes():
    """View company notes and comments"""
    user = AuthService.get_user_by_id(session['user_id'])
    
    if not user.company_id:
        flash('No company associated with your account', 'error')
        return redirect(url_for('main.home'))
    
    # For now, just redirect to dashboard with a message
    flash('Company notes feature coming soon!', 'info')
    return redirect(url_for('reports.dashboard'))