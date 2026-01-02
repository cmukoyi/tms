#!/usr/bin/env python3
"""
Test workflow permissions for company users
"""

from models import db, User
from app import app
from services.permissions_service import PermissionsService

def test_user_permissions():
    """Test that company users have workflow permissions"""
    
    with app.app_context():
        print("=" * 60)
        print("Testing Workflow Permissions")
        print("=" * 60)
        
        # Test with a company user
        test_user = User.query.filter_by(username='Carlos').first()
        
        if not test_user:
            print("❌ Test user 'Carlos' not found")
            return
        
        print(f"\nTesting permissions for: {test_user.username}")
        print(f"Company ID: {test_user.company_id}")
        print(f"User ID: {test_user.id}")
        
        # Test each permission
        permissions_to_check = [
            'view_all_tenders',
            'approve_tenders',
            'assign_tenders',
            'manage_roles',
            'view_users',
            'create_tenders',
            'edit_tenders',
            'delete_tenders'
        ]
        
        print("\n" + "=" * 60)
        print("Permission Check Results:")
        print("=" * 60)
        
        for perm in permissions_to_check:
            has_perm = PermissionsService.user_has_permission(
                user_id=test_user.id,
                permission_name=perm,
                company_id=test_user.company_id
            )
            status = "✅" if has_perm else "❌"
            print(f"{status} {perm}: {has_perm}")
        
        # Get all user permissions
        print("\n" + "=" * 60)
        print("All User Permissions:")
        print("=" * 60)
        all_perms = PermissionsService.get_user_permissions(
            user_id=test_user.id,
            company_id=test_user.company_id
        )
        print(f"Total permissions: {len(all_perms)}")
        for perm in all_perms:
            print(f"  - {perm.name} ({perm.display_name})")
        
        # Get user roles
        print("\n" + "=" * 60)
        print("User Roles:")
        print("=" * 60)
        roles = PermissionsService.get_user_roles(
            user_id=test_user.id,
            company_id=test_user.company_id
        )
        print(f"Total roles: {len(roles)}")
        for role in roles:
            print(f"  - {role.display_name} ({role.name})")
            print(f"    System Role: {role.is_system_role}")
        
        print("\n" + "=" * 60)
        if len(all_perms) >= 5:
            print("✅ User has sufficient permissions for Workflow menu!")
            print("   The Workflow menu should be visible in the UI.")
        else:
            print("❌ User does not have enough permissions")
        print("=" * 60)

if __name__ == '__main__':
    test_user_permissions()
