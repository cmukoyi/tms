#!/usr/bin/env python3
"""Create a test user for the application"""

from app import app, db
from models import User, CompanyRole, UserCompanyRole
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_test_user():
    with app.app_context():
        # Check if test user already exists
        existing_user = User.query.filter_by(email='testuser@example.com').first()
        if existing_user:
            print(f"❌ Test user already exists:")
            print(f"   Email: {existing_user.email}")
            print(f"   ID: {existing_user.id}")
            print(f"   Name: {existing_user.first_name} {existing_user.last_name}")
            return existing_user
        
        # Create new test user (regular employee, not admin)
        test_user = User(
            username='testuser',
            first_name='Test',
            last_name='User',
            email='testuser@example.com',
            password_hash=generate_password_hash('test123'),
            company_id=1,  # Assign to company 1
            role_id=2,  # Regular user role
            is_super_admin=False,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.session.add(test_user)
        db.session.flush()  # Get the user ID
        
        # Assign "Team Lead" role (moderate permissions)
        # Find the Team Lead role for company 1
        team_lead_role = CompanyRole.query.filter_by(
            company_id=1,
            name='Team Lead'
        ).first()
        
        if team_lead_role:
            user_role = UserCompanyRole(
                user_id=test_user.id,
                role_id=team_lead_role.id,
                assigned_by=1,  # Assigned by Carlos (user 1)
                assigned_at=datetime.utcnow()
            )
            db.session.add(user_role)
            print(f"✅ Assigned 'Team Lead' role to test user")
        else:
            print(f"⚠️  Team Lead role not found, creating user without role")
        
        db.session.commit()
        
        print("\n" + "="*60)
        print("✅ TEST USER CREATED SUCCESSFULLY")
        print("="*60)
        print(f"Name: {test_user.first_name} {test_user.last_name}")
        print(f"Email/Username: testuser@example.com")
        print(f"Password: test123")
        print(f"Company ID: {test_user.company_id}")
        print(f"User ID: {test_user.id}")
        print(f"Role: Team Lead (12 permissions)")
        print("="*60)
        print("\n🔐 Login at: http://localhost:5001")
        print("   Username: testuser@example.com")
        print("   Password: test123")
        print("="*60)
        
        return test_user

if __name__ == '__main__':
    create_test_user()
