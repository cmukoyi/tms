# routes/users.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.decorators import login_required, company_admin_required
from werkzeug.utils import secure_filename
from services import AuthService, CompanyService, RoleService
from models import db, User, Company
from datetime import datetime
import os

users_bp = Blueprint('users', __name__)

@users_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    user = AuthService.get_user_by_id(session['user_id'])
    
    context = {
        'user': user,
        'company': user.company if user.company else None
    }
    
    return render_template('user/profile.html', **context)

@users_bp.route('/profile/edit', methods=['GET', 'POST'])
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
                    from flask import current_app
                    # Save the uploaded file
                    filename = secure_filename(file.filename)
                    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'profiles')
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
                    return redirect(url_for('users.edit_profile'))
                
                user.password_hash = AuthService.hash_password(new_password)
            
            db.session.commit()
            flash('Profile updated successfully', 'success')
            return redirect(url_for('users.profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'error')
    
    return render_template('user/edit_profile.html', user=user)

@users_bp.route('/company/users')
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

@users_bp.route('/company/users/create', methods=['GET', 'POST'])
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
                return redirect(url_for('users.company_users'))
            else:
                flash(message, 'error')
    
    # Get roles available for company users (excluding Super Admin)
    roles = RoleService.get_company_roles()
    company = CompanyService.get_company_by_id(current_user.company_id) if not current_user.is_super_admin else None

    return render_template('company/create_user.html', roles=roles, company=company)

@users_bp.route('/my-company/profile')
@login_required
def my_company_profile():
    """View current user's company profile"""
    user = AuthService.get_user_by_id(session['user_id'])
    
    if not user.company_id:
        flash('No company associated with your account', 'error')
        return redirect(url_for('main.home'))
    
    company = Company.query.get_or_404(user.company_id)
    
    # Get company statistics
    total_users = User.query.filter_by(company_id=company.id).count()
    active_users = User.query.filter_by(company_id=company.id, is_active=True).count()
    
    # Get document count if Document model exists
    try:
        from models import Document
        total_documents = Document.query.filter_by(company_id=company.id).count()
    except:
        total_documents = 0
    
    # Get tender count if Tender model exists  
    try:
        from models import Tender
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

@users_bp.route('/company-users')
@login_required  
def company_users_redirect():
    """View company users (for company admins)"""
    user = AuthService.get_user_by_id(session['user_id'])
    
    if not user.company_id:
        flash('No company associated with your account', 'error')
        return redirect(url_for('main.home'))
    
    # Check if user is company admin
    if user.role.name not in ['Company Admin', 'Super Admin']:
        flash('You do not have permission to view company users', 'error')
        return redirect(url_for('reports.dashboard'))
    
    # Redirect to the proper company users page
    return redirect(url_for('admin.view_company_users', company_id=user.company_id))