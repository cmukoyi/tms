# routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from services import AuthService
from utils.decorators import login_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
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
            return redirect(url_for('reports.dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'error')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout and clear session"""
    username = session.get('username', 'User')
    session.clear()
    flash(f'Goodbye, {username}! You have been logged out.', 'info')
    return redirect(url_for('main.home'))