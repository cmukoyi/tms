# routes/tenders.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.decorators import login_required
from services import (
    AuthService, TenderService, TenderCategoryService, TenderStatusService, 
    CustomFieldService, CompanyService, TenderDocumentService, 
    DocumentTypeService, TenderHistoryService
)
from models import Tender, TenderNote, db
from datetime import datetime

tenders_bp = Blueprint('tenders', __name__)

@tenders_bp.route('/tenders', methods=['GET', 'POST'])
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

@tenders_bp.route('/tenders/create', methods=['GET', 'POST'])
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
                return redirect(url_for('tenders.view_tender', tender_id=tender.id))
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

@tenders_bp.route('/tenders/<int:tender_id>')
@login_required
def view_tender(tender_id):
    """View tender details with notes"""
    user = AuthService.get_user_by_id(session['user_id'])
    tender = TenderService.get_tender_by_id(tender_id)
    
    if not tender:
        flash('Tender not found.', 'error')
        return redirect(url_for('tenders.tenders'))
    
    # Check access permissions
    if not user.is_super_admin and tender.company_id != user.company_id:
        flash('Access denied.', 'error')
        return redirect(url_for('tenders.tenders'))
    
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
                         current_user=user)

@tenders_bp.route('/tenders/<int:tender_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_tender(tender_id):
    """Edit tender"""
    user = AuthService.get_user_by_id(session['user_id'])
    tender = TenderService.get_tender_by_id(tender_id)
    
    if not tender:
        flash('Tender not found.', 'error')
        return redirect(url_for('tenders.tenders'))
    
    # Check access permissions
    if not user.is_super_admin and tender.company_id != user.company_id:
        flash('Access denied.', 'error')
        return redirect(url_for('tenders.tenders'))
    
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
                return redirect(url_for('tenders.view_tender', tender_id=tender_id))
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

@tenders_bp.route('/tenders/<int:tender_id>/delete', methods=['POST'])
@login_required
def delete_tender(tender_id):
    """Delete tender"""
    user = AuthService.get_user_by_id(session['user_id'])
    tender = TenderService.get_tender_by_id(tender_id)
    
    if not tender:
        flash('Tender not found.', 'error')
        return redirect(url_for('tenders.tenders'))
    
    # Check access permissions
    if not user.is_super_admin and tender.company_id != user.company_id:
        flash('Access denied.', 'error')
        return redirect(url_for('tenders.tenders'))
    
    success, message = TenderService.delete_tender(tender_id)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('tenders.tenders'))

@tenders_bp.route('/tenders/<int:tender_id>/upload', methods=['POST'])
@login_required
def upload_tender_document(tender_id):
    """Upload document to tender"""
    user = AuthService.get_user_by_id(session['user_id'])
    tender = TenderService.get_tender_by_id(tender_id)
    
    if not tender:
        flash('Tender not found.', 'error')
        return redirect(url_for('tenders.tenders'))
    
    # Check access permissions
    if not user.is_super_admin and tender.company_id != user.company_id:
        flash('Access denied.', 'error')
        return redirect(url_for('tenders.tenders'))
    
    if 'document' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('tenders.view_tender', tender_id=tender_id))
    
    file = request.files['document']
    document_type_id = request.form.get('document_type_id')
    
    if not document_type_id:
        flash('Document type is required.', 'error')
        return redirect(url_for('tenders.view_tender', tender_id=tender_id))
    
    from flask import current_app
    document, message = TenderDocumentService.save_document(
        file=file,
        tender_id=tender_id,
        document_type_id=int(document_type_id),
        uploaded_by=user.id,
        upload_folder=current_app.config['UPLOAD_FOLDER']
    )
    
    if document:
        flash(message, 'success')
        # Log document upload
        TenderHistoryService.log_document_uploaded(
            tender_id=tender_id,
            performed_by_id=user.id,
            document_name=document.original_filename,
            document_type=document.doc_type.name,
        )
    else:
        flash(message, 'error')
    
    return redirect(url_for('tenders.view_tender', tender_id=tender_id))

# Tender Notes Routes
@tenders_bp.route('/tender/<int:tender_id>/notes', methods=['POST'])
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
            return redirect(url_for('tenders.view_tender', tender_id=tender_id))
        
        # Get note content from form
        note_content = request.form.get('note_content', '').strip()
        
        if not note_content:
            flash('Note content cannot be empty.', 'error')
            return redirect(url_for('tenders.view_tender', tender_id=tender_id))
        
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
    
    return redirect(url_for('tenders.view_tender', tender_id=tender_id) + '#notes')

@tenders_bp.route('/tender/notes/<int:note_id>/edit', methods=['POST'])
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
            return redirect(url_for('tenders.view_tender', tender_id=tender_id))
        
        # Get new content from form
        new_content = request.form.get('note_content', '').strip()
        
        if not new_content:
            flash('Note content cannot be empty.', 'error')
            return redirect(url_for('tenders.view_tender', tender_id=tender_id) + '#notes')
        
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
    
    return redirect(url_for('tenders.view_tender', tender_id=tender_id) + '#notes')

@tenders_bp.route('/tender/notes/<int:note_id>/delete', methods=['POST'])
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
            return redirect(url_for('tenders.view_tender', tender_id=tender_id))
        
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
    
    return redirect(url_for('tenders.view_tender', tender_id=tender_id) + '#notes')