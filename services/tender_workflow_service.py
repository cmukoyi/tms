"""
Tender Workflow Service
Handles tender assignments, approvals, and workflow management
"""

from models import (
    db, Tender, TenderAssignment, TenderWorkflow, TenderDocument,
    TenderComment, TenderActivity, User
)
from datetime import datetime
import json
from flask import session, request


class TenderWorkflowService:
    """Service for managing tender workflows"""
    
    @staticmethod
    def assign_tender(tender_id, assigned_to_id, assigned_by_id, due_date=None, notes=None):
        """
        Assign a tender to a user
        
        Args:
            tender_id: Tender ID
            assigned_to_id: User ID to assign to
            assigned_by_id: User ID who is assigning
            due_date: Optional due date
            notes: Optional notes
        
        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            # Check if tender exists
            tender = Tender.query.get(tender_id)
            if not tender:
                return (False, "Tender not found")
            
            # Check if user exists
            user = User.query.get(assigned_to_id)
            if not user:
                return (False, "User not found")
            
            # Create assignment
            assignment = TenderAssignment(
                tender_id=tender_id,
                assigned_to_id=assigned_to_id,
                assigned_by_id=assigned_by_id,
                due_date=due_date,
                notes=notes
            )
            
            db.session.add(assignment)
            
            # Log activity
            TenderWorkflowService.log_activity(
                tender_id=tender_id,
                user_id=assigned_by_id,
                activity_type='assigned',
                description=f"Assigned to {user.first_name} {user.last_name}",
                metadata=json.dumps({
                    'assigned_to_id': assigned_to_id,
                    'assigned_to_name': f"{user.first_name} {user.last_name}",
                    'due_date': due_date.isoformat() if due_date else None
                })
            )
            
            db.session.commit()
            
            return (True, "Tender assigned successfully")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error assigning tender: {e}")
            return (False, str(e))
    
    @staticmethod
    def get_user_assigned_tenders(user_id, include_inactive=False):
        """
        Get all tenders assigned to a user
        
        Args:
            user_id: User ID
            include_inactive: Whether to include inactive assignments
        
        Returns:
            List of Tender objects
        """
        try:
            query = db.session.query(Tender).join(TenderAssignment).filter(
                TenderAssignment.assigned_to_id == user_id
            )
            
            if not include_inactive:
                query = query.filter(TenderAssignment.is_active == True)
            
            return query.all()
            
        except Exception as e:
            print(f"Error getting assigned tenders: {e}")
            return []
    
    @staticmethod
    def submit_for_approval(tender_id, user_id):
        """
        Submit a tender for approval
        
        Args:
            tender_id: Tender ID
            user_id: User submitting
        
        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            # Get or create workflow
            workflow = TenderWorkflow.query.filter_by(tender_id=tender_id).first()
            
            if not workflow:
                workflow = TenderWorkflow(tender_id=tender_id)
                db.session.add(workflow)
            
            # Check if can submit
            if not workflow.can_submit_for_approval():
                return (False, f"Cannot submit tender with status '{workflow.status}' for approval")
            
            # Get current active assignment to find who assigned it
            current_assignment = TenderAssignment.query.filter_by(
                tender_id=tender_id,
                assigned_to_id=user_id,
                is_active=True
            ).order_by(TenderAssignment.assigned_at.desc()).first()
            
            print(f"Current assignment: {current_assignment}")
            
            # Deactivate current assignment (tender no longer sits with user)
            if current_assignment:
                current_assignment.is_active = False
                assigned_by_id = current_assignment.assigned_by_id
                
                print(f"Deactivating assignment {current_assignment.id}, reassigning to admin {assigned_by_id}")
                
                # Create new assignment back to the admin who assigned it
                new_assignment = TenderAssignment(
                    tender_id=tender_id,
                    assigned_to_id=assigned_by_id,  # Assign back to admin
                    assigned_by_id=user_id,  # User is now the one reassigning
                    notes="Submitted for approval - reassigned to admin for review"
                )
                db.session.add(new_assignment)
                print(f"Created new assignment to admin {assigned_by_id}")
            
            # Update workflow
            workflow.status = 'pending_approval'
            workflow.submitted_for_approval_at = datetime.utcnow()
            workflow.submitted_for_approval_by = user_id
            workflow.approved_rejected_at = None
            workflow.approved_rejected_by = None
            workflow.approval_notes = None
            
            # Log activity
            TenderWorkflowService.log_activity(
                tender_id=tender_id,
                user_id=user_id,
                activity_type='submitted_for_approval',
                description="Submitted for approval"
            )
            
            db.session.commit()
            
            return (True, "Tender submitted for approval and reassigned to admin")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error submitting for approval: {e}")
            return (False, str(e))
    
    @staticmethod
    def approve_tender(tender_id, user_id, notes=None):
        """
        Approve a tender
        
        Args:
            tender_id: Tender ID
            user_id: User approving
            notes: Optional approval notes
        
        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            workflow = TenderWorkflow.query.filter_by(tender_id=tender_id).first()
            
            if not workflow:
                return (False, "Workflow not found")
            
            if not workflow.can_approve():
                return (False, f"Cannot approve tender with status '{workflow.status}'")
            
            # Update workflow
            workflow.status = 'approved'
            workflow.approved_rejected_at = datetime.utcnow()
            workflow.approved_rejected_by = user_id
            workflow.approval_notes = notes
            
            # Log activity
            TenderWorkflowService.log_activity(
                tender_id=tender_id,
                user_id=user_id,
                activity_type='approved',
                description="Tender approved",
                metadata=json.dumps({'notes': notes}) if notes else None
            )
            
            db.session.commit()
            
            return (True, "Tender approved successfully")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error approving tender: {e}")
            return (False, str(e))
    
    @staticmethod
    def reject_tender(tender_id, user_id, notes=None):
        """
        Reject a tender and reassign it back to the user who submitted it
        
        Args:
            tender_id: Tender ID
            user_id: User rejecting (admin)
            notes: Optional rejection notes
        
        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            workflow = TenderWorkflow.query.filter_by(tender_id=tender_id).first()
            
            if not workflow:
                return (False, "Workflow not found")
            
            if not workflow.can_approve():
                return (False, f"Cannot reject tender with status '{workflow.status}'")
            
            # Get current active assignment (should be with admin)
            current_assignment = TenderAssignment.query.filter_by(
                tender_id=tender_id,
                is_active=True
            ).order_by(TenderAssignment.assigned_at.desc()).first()
            
            # Deactivate current assignment
            if current_assignment:
                current_assignment.is_active = False
                
                # Reassign back to the user who submitted for approval
                if workflow.submitted_for_approval_by:
                    new_assignment = TenderAssignment(
                        tender_id=tender_id,
                        assigned_to_id=workflow.submitted_for_approval_by,  # Back to original user
                        assigned_by_id=user_id,  # Admin is reassigning
                        notes=f"Rejected - {notes}" if notes else "Rejected - requires revisions"
                    )
                    db.session.add(new_assignment)
            
            # Update workflow
            workflow.status = 'rejected'
            workflow.approved_rejected_at = datetime.utcnow()
            workflow.approved_rejected_by = user_id
            workflow.approval_notes = notes
            
            # Log activity
            TenderWorkflowService.log_activity(
                tender_id=tender_id,
                user_id=user_id,
                activity_type='rejected',
                description="Tender rejected",
                metadata=json.dumps({'notes': notes}) if notes else None
            )
            
            db.session.commit()
            
            return (True, "Tender rejected and reassigned to user")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error rejecting tender: {e}")
            return (False, str(e))
    
    @staticmethod
    def submit_tender(tender_id, user_id):
        """
        Submit an approved tender to the client
        
        Args:
            tender_id: Tender ID
            user_id: User submitting
        
        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            workflow = TenderWorkflow.query.filter_by(tender_id=tender_id).first()
            
            if not workflow:
                return (False, "Workflow not found")
            
            if not workflow.can_submit():
                return (False, f"Cannot submit tender with status '{workflow.status}'. Must be approved first.")
            
            # Update workflow
            workflow.status = 'submitted'
            workflow.submitted_at = datetime.utcnow()
            workflow.submitted_by = user_id
            
            # Update tender status (if tender has a status field)
            tender = Tender.query.get(tender_id)
            if tender and hasattr(tender, 'status'):
                tender.status = 'submitted'
            
            # Log activity
            TenderWorkflowService.log_activity(
                tender_id=tender_id,
                user_id=user_id,
                activity_type='submitted',
                description="Tender submitted to client"
            )
            
            db.session.commit()
            
            return (True, "Tender submitted successfully")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error submitting tender: {e}")
            return (False, str(e))
    
    @staticmethod
    def add_comment(tender_id, user_id, comment, parent_comment_id=None, is_internal=True):
        """
        Add a comment to a tender
        
        Args:
            tender_id: Tender ID
            user_id: User adding comment
            comment: Comment text
            parent_comment_id: Optional parent comment for threading
            is_internal: Whether comment is internal or client-facing
        
        Returns:
            Tuple (success: bool, comment_obj: TenderComment or None, message: str)
        """
        try:
            tender_comment = TenderComment(
                tender_id=tender_id,
                user_id=user_id,
                comment=comment,
                parent_comment_id=parent_comment_id,
                is_internal=is_internal
            )
            
            db.session.add(tender_comment)
            
            # Log activity
            TenderWorkflowService.log_activity(
                tender_id=tender_id,
                user_id=user_id,
                activity_type='commented',
                description="Added a comment"
            )
            
            db.session.commit()
            
            return (True, tender_comment, "Comment added successfully")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error adding comment: {e}")
            return (False, None, str(e))
    
    @staticmethod
    def upload_document(tender_id, user_id, filename, file_path, document_type=None, 
                       file_size=None, mime_type=None, notes=None):
        """
        Upload a document for a tender
        
        Args:
            tender_id: Tender ID
            user_id: User uploading
            filename: Original filename
            file_path: Path where file is stored
            document_type: Type of document (rfp, response, supporting, etc.)
            file_size: File size in bytes
            mime_type: MIME type
            notes: Optional notes
        
        Returns:
            Tuple (success: bool, document: TenderDocument or None, message: str)
        """
        try:
            # Check for existing documents with same name and increment version
            existing_docs = TenderDocument.query.filter_by(
                tender_id=tender_id,
                filename=filename,
                is_active=True
            ).all()
            
            version = len(existing_docs) + 1 if existing_docs else 1
            
            document = TenderDocument(
                tender_id=tender_id,
                document_type=document_type,
                filename=filename,
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type,
                uploaded_by_id=user_id,
                version=version,
                notes=notes
            )
            
            db.session.add(document)
            
            # Log activity
            TenderWorkflowService.log_activity(
                tender_id=tender_id,
                user_id=user_id,
                activity_type='document_uploaded',
                description=f"Uploaded document: {filename}",
                metadata=json.dumps({
                    'filename': filename,
                    'document_type': document_type,
                    'version': version
                })
            )
            
            db.session.commit()
            
            return (True, document, "Document uploaded successfully")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error uploading document: {e}")
            return (False, None, str(e))
    
    @staticmethod
    def get_tender_workflow(tender_id):
        """
        Get workflow for a tender
        
        Args:
            tender_id: Tender ID
        
        Returns:
            TenderWorkflow object or None
        """
        try:
            workflow = TenderWorkflow.query.filter_by(tender_id=tender_id).first()
            
            # Create workflow if it doesn't exist
            if not workflow:
                workflow = TenderWorkflow(tender_id=tender_id, status='draft')
                db.session.add(workflow)
                db.session.commit()
            
            return workflow
            
        except Exception as e:
            print(f"Error getting workflow: {e}")
            return None
    
    @staticmethod
    def get_tender_activities(tender_id, limit=None):
        """
        Get activity log for a tender
        
        Args:
            tender_id: Tender ID
            limit: Optional limit on number of activities
        
        Returns:
            List of TenderActivity objects
        """
        try:
            query = TenderActivity.query.filter_by(tender_id=tender_id).order_by(
                TenderActivity.created_at.desc()
            )
            
            if limit:
                query = query.limit(limit)
            
            return query.all()
            
        except Exception as e:
            print(f"Error getting activities: {e}")
            return []
    
    @staticmethod
    def log_activity(tender_id, user_id, activity_type, description, metadata=None):
        """
        Log an activity for a tender
        
        Args:
            tender_id: Tender ID
            user_id: User performing action
            activity_type: Type of activity
            description: Activity description
            metadata: Optional JSON metadata
        """
        try:
            # Get IP address if available
            ip_address = None
            if request:
                ip_address = request.remote_addr
            
            activity = TenderActivity(
                tender_id=tender_id,
                user_id=user_id,
                activity_type=activity_type,
                description=description,
                activity_metadata=metadata,
                ip_address=ip_address
            )
            
            db.session.add(activity)
            # Note: Caller should commit
            
        except Exception as e:
            print(f"Error logging activity: {e}")
    
    @staticmethod
    def get_pending_approvals(company_id):
        """
        Get all tenders pending approval for a company
        
        Args:
            company_id: Company ID
        
        Returns:
            List of Tender objects
        """
        try:
            tenders = db.session.query(Tender).join(TenderWorkflow).filter(
                Tender.company_id == company_id,
                TenderWorkflow.status == 'pending_approval'
            ).all()
            
            return tenders
            
        except Exception as e:
            print(f"Error getting pending approvals: {e}")
            return []
    
    @staticmethod
    def get_workflow_statistics(company_id):
        """
        Get workflow statistics for a company
        
        Args:
            company_id: Company ID
        
        Returns:
            Dictionary with statistics
        """
        try:
            stats = {
                'draft': 0,
                'in_progress': 0,
                'pending_approval': 0,
                'approved': 0,
                'rejected': 0,
                'submitted': 0
            }
            
            # Count tenders by status
            from sqlalchemy import func
            
            results = db.session.query(
                TenderWorkflow.status,
                func.count(TenderWorkflow.id)
            ).join(Tender).filter(
                Tender.company_id == company_id
            ).group_by(TenderWorkflow.status).all()
            
            for status, count in results:
                if status in stats:
                    stats[status] = count
            
            # Add total
            stats['total'] = sum(stats.values())
            
            return stats
            
        except Exception as e:
            print(f"Error getting workflow statistics: {e}")
            return {
                'draft': 0,
                'in_progress': 0,
                'pending_approval': 0,
                'approved': 0,
                'rejected': 0,
                'submitted': 0,
                'total': 0
            }
