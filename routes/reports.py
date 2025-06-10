# routes/reports.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.decorators import login_required
from utils.export_helpers import (export_tenders_pdf, export_tenders_excel, 
                                 export_tenders_by_category_pdf, export_tenders_by_category_excel)
from utils.helpers import can_access_module
from services import AuthService, TenderService, CompanyService
from models import Tender, TenderStatus, Company, User
from datetime import datetime, timedelta

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/dashboard')
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

@reports_bp.route('/reports')
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

@reports_bp.route('/reports/tenders')
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

@reports_bp.route('/active_tenders_report')
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