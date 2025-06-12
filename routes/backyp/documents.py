# routes/documents.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file
from utils.decorators import login_required
from services import AuthService
from models import db
from datetime import datetime

documents_bp = Blueprint('documents', __name__)

@documents_bp.route('/documents')
@login_required
def documents():
    """View and manage documents"""
    user = AuthService.get_user_by_id(session['user_id'])
    
    # Get documents for the current user's company
    company_id = user.company_id if user.company_id else None
    
    if not company_id:
        flash('No company associated with your account', 'error')
        return redirect(url_for('main.home'))
    
    # Get all documents for this company
    try:
        from models import Document
        documents = Document.query.filter_by(company_id=company_id).order_by(Document.created_at.desc()).all()
    except ImportError:
        # Document model doesn't exist yet, show empty list
        documents = []
        flash('Document management feature is not yet fully implemented', 'info')
    
    # Get document statistics
    total_documents = len(documents)
    recent_documents = len([d for d in documents if (datetime.now() - d.created_at).days <= 7]) if documents else 0
    
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

@documents_bp.route('/documents/upload', methods=['GET', 'POST'])
@login_required
def upload_document():
    """Upload a new document"""
    user = AuthService.get_user_by_id(session['user_id'])
    
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
                
                try:
                    from models import Document
                    # Create document record
                    document = Document(
                        title=title,
                        description=description,
                        filename=file.filename,
                        document_type=document_type,
                        file_size=len(file.read()),
                        company_id=user.company_id,
                        uploaded_by=user.id
                    )
                    
                    # Reset file pointer after reading size
                    file.seek(0)
                    
                    # Save file (you'll need to implement file storage)
                    # For now, we'll just save the record
                    db.session.add(document)
                    db.session.commit()
                    
                    flash(f'Document "{title}" uploaded successfully!', 'success')
                    return redirect(url_for('documents.documents'))
                except ImportError:
                    flash('Document model not implemented yet', 'error')
                    
        except Exception as e:
            db.session.rollback()
            flash(f'Error uploading document: {str(e)}', 'error')
    
    # GET request - show upload form
    document_types = ['Contract', 'Invoice', 'Report', 'Tender Document', 'Other']
    return render_template('upload_document.html', document_types=document_types)

@documents_bp.route('/documents/<int:document_id>/view')
@login_required
def view_document(document_id):
    """View document details"""
    user = AuthService.get_user_by_id(session['user_id'])
    
    try:
        from models import Document
        document = Document.query.filter_by(
            id=document_id, 
            company_id=user.company_id
        ).first_or_404()
        
        return render_template('view_document.html', document=document)
    except ImportError:
        flash('Document model not implemented yet', 'error')
        return redirect(url_for('documents.documents'))

@documents_bp.route('/documents/<int:document_id>/download')
@login_required
def download_document(document_id):
    """Download a document"""
    user = AuthService.get_user_by_id(session['user_id'])
    
    try:
        from models import Document
        document = Document.query.filter_by(
            id=document_id, 
            company_id=user.company_id
        ).first_or_404()
        
        # For now, just redirect back with a message
        # You'll need to implement actual file serving
        flash(f'Download feature for "{document.title}" coming soon', 'info')
        return redirect(url_for('documents.documents'))
    except ImportError:
        flash('Document model not implemented yet', 'error')
        return redirect(url_for('documents.documents'))

@documents_bp.route('/documents/<int:document_id>/delete', methods=['POST'])
@login_required
def delete_document(document_id):
    """Delete a document"""
    user = AuthService.get_user_by_id(session['user_id'])
    
    try:
        from models import Document
        document = Document.query.filter_by(
            id=document_id, 
            company_id=user.company_id
        ).first_or_404()
        
        # Check permissions (only uploader or admin can delete)
        if document.uploaded_by != user.id and not user.role.name in ['Company Admin', 'Super Admin']:
            flash('You do not have permission to delete this document', 'error')
            return redirect(url_for('documents.documents'))
        
        title = document.title
        db.session.delete(document)
        db.session.commit()
        
        flash(f'Document "{title}" deleted successfully', 'success')
        
    except ImportError:
        flash('Document model not implemented yet', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting document: {str(e)}', 'error')
    
    return redirect(url_for('documents.documents'))