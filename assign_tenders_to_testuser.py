#!/usr/bin/env python3
"""Assign 10 tenders to test user with mixed statuses"""

from app import app, db
from models import Tender, TenderAssignment, TenderStatus, User
from datetime import datetime, timedelta
import random

def assign_tenders():
    with app.app_context():
        # Get test user
        test_user = User.query.filter_by(email='testuser@example.com').first()
        if not test_user:
            print("❌ Test user not found!")
            return
        
        # Get company admin (Carlos) who will assign the tenders
        admin_user = User.query.filter_by(id=1).first()
        
        # Get available tenders from company 1
        available_tenders = Tender.query.filter_by(company_id=1).limit(10).all()
        
        if len(available_tenders) < 10:
            print(f"⚠️  Only {len(available_tenders)} tenders available in company 1")
        
        # Get different statuses
        statuses = {
            'draft': TenderStatus.query.filter_by(name='Draft').first(),
            'published': TenderStatus.query.filter_by(name='Published').first(),
            'under_review': TenderStatus.query.filter_by(name='Under Review').first(),
            'closed': TenderStatus.query.filter_by(name='Closed').first(),
            'awarded': TenderStatus.query.filter_by(name='Awarded').first(),
        }
        
        print("\n" + "="*60)
        print("ASSIGNING TENDERS TO TEST USER")
        print("="*60)
        
        assignments_created = 0
        for idx, tender in enumerate(available_tenders[:10]):
            # Check if already assigned
            existing = TenderAssignment.query.filter_by(
                tender_id=tender.id,
                assigned_to_id=test_user.id
            ).first()
            
            if existing:
                print(f"⏭️  Tender #{tender.id} already assigned - skipping")
                continue
            
            # Create assignment
            assignment = TenderAssignment(
                tender_id=tender.id,
                assigned_to_id=test_user.id,
                assigned_by_id=admin_user.id,
                assigned_at=datetime.utcnow(),
                due_date=datetime.utcnow() + timedelta(days=random.randint(5, 30)),
                notes=f"Test assignment {idx + 1}",
                is_active=True
            )
            db.session.add(assignment)
            
            # Set different statuses
            status_name = "Unknown"
            if idx < 3:
                # First 3: Draft
                if statuses['draft']:
                    tender.status_id = statuses['draft'].id
                    status_name = "Draft"
            elif idx < 6:
                # Next 3: Published
                if statuses['published']:
                    tender.status_id = statuses['published'].id
                    status_name = "Published"
            elif idx < 8:
                # Next 2: Under Review
                if statuses['under_review']:
                    tender.status_id = statuses['under_review'].id
                    status_name = "Under Review"
            else:
                # Last 2: Closed
                if statuses['closed']:
                    tender.status_id = statuses['closed'].id
                    status_name = "Closed"
            
            assignments_created += 1
            print(f"✅ Assigned Tender #{tender.id}: {tender.title[:40]}... [{status_name}]")
        
        db.session.commit()
        
        print("="*60)
        print(f"✅ Successfully created {assignments_created} assignments")
        print("="*60)
        print(f"\nTest User: {test_user.first_name} {test_user.last_name}")
        print(f"Email: {test_user.email}")
        print(f"Total Assigned Tenders: {assignments_created}")
        print("\nStatus Breakdown:")
        print("  - Draft: 3 tenders")
        print("  - Published: 3 tenders")
        print("  - Under Review: 2 tenders")
        print("  - Closed: 2 tenders")
        print("="*60)
        print("\n🔐 Login as testuser@example.com / test123 to view assigned tenders")
        print("="*60)

if __name__ == '__main__':
    assign_tenders()
