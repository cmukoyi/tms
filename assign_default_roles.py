#!/usr/bin/env python3
"""
Assign default "Company Admin" role to existing company users
This allows them to access the workflow features
"""

from models import db, User, CompanyRole, UserCompanyRole
from app import app
from datetime import datetime

def assign_default_roles():
    """Assign Company Admin role to all existing company users"""
    
    with app.app_context():
        print("=" * 60)
        print("Assigning Default Workflow Roles to Company Users")
        print("=" * 60)
        
        # Get all company users (exclude super admins)
        company_users = User.query.filter(
            User.company_id.isnot(None),
            User.company_id > 0
        ).all()
        
        print(f"\nFound {len(company_users)} company users")
        
        assigned_count = 0
        skipped_count = 0
        
        for user in company_users:
            # Check if user already has a role
            existing_role = UserCompanyRole.query.filter_by(user_id=user.id).first()
            if existing_role:
                print(f"  ⏭️  {user.username} already has a role - skipping")
                skipped_count += 1
                continue
            
            # Find the "Company Admin" role for this user's company
            admin_role = CompanyRole.query.filter_by(
                company_id=user.company_id,
                name='company_admin',
                is_system_role=True
            ).first()
            
            if not admin_role:
                print(f"  ❌ No Company Admin role found for company {user.company_id}")
                continue
            
            # Assign the role
            user_role = UserCompanyRole(
                user_id=user.id,
                role_id=admin_role.id,
                assigned_at=datetime.utcnow(),
                assigned_by=user.id  # Self-assigned initially
            )
            
            db.session.add(user_role)
            assigned_count += 1
            print(f"  ✅ Assigned '{admin_role.display_name}' to {user.username} (Company: {user.company_id})")
        
        # Commit all assignments
        db.session.commit()
        
        print("\n" + "=" * 60)
        print(f"✅ Successfully assigned roles to {assigned_count} users")
        print(f"⏭️  Skipped {skipped_count} users (already have roles)")
        print("=" * 60)
        
        # Show summary
        print("\n📊 Current Role Assignments:")
        total_assignments = UserCompanyRole.query.count()
        print(f"   Total user-role assignments: {total_assignments}")
        
        # Show breakdown by company
        from sqlalchemy import func
        assignments_by_company = db.session.query(
            User.company_id,
            func.count(UserCompanyRole.id).label('count')
        ).join(UserCompanyRole, User.id == UserCompanyRole.user_id
        ).group_by(User.company_id).all()
        
        print("\n   By company:")
        for company_id, count in assignments_by_company:
            print(f"     Company {company_id}: {count} users with roles")
        
        print("\n🎉 Users can now access Workflow features in the UI!")
        print("   Look for the 'Workflow' menu in the navigation bar")

if __name__ == '__main__':
    assign_default_roles()
