# Tender Management System - Workflow & Permissions Guide

## 🎯 Overview

Your TMS now includes a comprehensive tender workflow system with granular role-based permissions, enabling complete control over who can do what in your company.

---

## 📊 System Architecture

### **Premium Modules Added (19 total)**
- **Revenue Potential**: R18,693/month per company
- **Annual Potential**: R897,264/year across 4 companies

#### Game-Changing AI Modules (R4,797/month)
1. **AI Tender Writing Assistant** (R1,499/month) - 70% faster bid writing
2. **Smart Document Intelligence** (R999/month) - Auto-extract requirements from PDFs
3. **Predictive Bid Success Scoring** (R1,299/month) - Know your win probability
4. **Competitive Intelligence Hub** (R1,999/month) - Track all competitors

#### High-Value Modules (R8,089/month)
5. **Collaborative Bid Workspace** (R599/month) - Real-time collaboration
6. **Tender Opportunity Scraper** (R799/month) - Never miss opportunities
7. **Win/Loss Analytics Dashboard** (R699/month) - Track performance
8. **Electronic Signature & Workflows** (R549/month) - Legal e-signatures
9. And 4 more premium features...

---

## 👥 Roles & Permissions System

### **6 Pre-Defined Roles**

#### 1. **Viewer** (3 permissions)
Read-only access to tenders and reports
- View Tenders
- View Reports
- View Analytics

#### 2. **Contributor** (6 permissions)
Can work on assigned tenders
- View Tenders
- Edit Tenders
- Upload Documents
- Add Comments
- Submit for Approval
- View Reports

#### 3. **Team Lead** (12 permissions)
Can view all tenders, assign work, and collaborate
- All Contributor permissions, plus:
- View All Company Tenders
- Create Tenders
- Assign Tenders
- Delete Documents
- Export Reports
- View Analytics

#### 4. **Approver** (6 permissions)
Can approve tender submissions
- View Tenders
- View All Company Tenders
- **Approve Tenders**
- Add Comments
- View Reports
- View Analytics

#### 5. **Manager** (15 permissions)
Can submit tenders and manage team
- All Team Lead permissions, plus:
- Approve Tenders
- **Submit Tenders** (final submission to client)
- View Users
- View Billing

#### 6. **Company Admin** (26 permissions)
Full access to everything
- All Manager permissions, plus:
- Create/Edit/Delete Users
- Manage Roles & Assign Roles
- Manage Modules
- Manage Company Settings
- Full Accounting Access

---

## 🔄 Tender Workflow Process

### **Workflow Statuses**
1. **Draft** - Tender created, initial stage
2. **In Progress** - Being worked on
3. **Pending Approval** - Submitted for review
4. **Approved** - Ready for final submission
5. **Rejected** - Needs revision
6. **Submitted** - Submitted to client

### **Workflow Steps**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. ADMIN CREATES & ASSIGNS TENDER                          │
│    Permission: create_tenders, assign_tenders              │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. CONTRIBUTOR WORKS ON TENDER                             │
│    - Upload documents (RFP, responses, supporting docs)    │
│    - Add comments and collaborate                          │
│    - Edit tender details                                   │
│    Permission: edit_tenders, upload_documents              │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. CONTRIBUTOR SUBMITS FOR APPROVAL                        │
│    Status: Draft/In Progress → Pending Approval            │
│    Permission: submit_for_approval                         │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. APPROVER REVIEWS TENDER                                 │
│    Option A: APPROVE ────────→ Status: Approved            │
│    Option B: REJECT  ────────→ Status: Rejected            │
│              (back to step 2)                              │
│    Permission: approve_tenders                             │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. MANAGER SUBMITS TO CLIENT                               │
│    Final submission - Status: Submitted                    │
│    Permission: submit_tenders                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗂️ Database Structure

### **9 New Tables Created**

1. **permissions** - 28 granular permissions across 5 categories
2. **company_roles** - Custom roles per company (24 roles created)
3. **role_permissions** - Links roles to permissions
4. **user_company_roles** - Links users to their roles
5. **tender_assignments** - Track who's assigned to which tender
6. **tender_workflows** - Track tender status and approvals (80 created)
7. **tender_documents** - Store tender documents with versioning
8. **tender_comments** - Collaboration & internal notes
9. **tender_activities** - Complete audit trail of all actions

---

## 🛠️ Permission Categories

### **Tenders** (12 permissions)
- view_tenders, create_tenders, edit_tenders, delete_tenders
- assign_tenders, submit_for_approval, approve_tenders, submit_tenders
- upload_documents, delete_documents, add_comments
- view_all_tenders (see all company tenders, not just assigned)

### **Users** (6 permissions)
- view_users, create_users, edit_users, delete_users
- manage_roles, assign_roles

### **Reports & Analytics** (3 permissions)
- view_reports, export_reports, view_analytics

### **Settings** (3 permissions)
- manage_modules, view_billing, manage_company_settings

### **Accounting** (4 permissions)
- view_accounting, create_journal_entries
- approve_journal_entries, view_financial_reports

---

## 📝 Usage Examples

### **Example 1: Assign Tender to Team Member**
```python
from services.tender_workflow_service import TenderWorkflowService

success, message = TenderWorkflowService.assign_tender(
    tender_id=123,
    assigned_to_id=5,  # User ID
    assigned_by_id=1,  # Admin ID
    due_date=datetime(2026, 2, 15),
    notes="Please complete financial section by Friday"
)
```

### **Example 2: Submit Tender for Approval**
```python
success, message = TenderWorkflowService.submit_for_approval(
    tender_id=123,
    user_id=5  # Contributor submitting
)
```

### **Example 3: Approve Tender**
```python
success, message = TenderWorkflowService.approve_tender(
    tender_id=123,
    user_id=2,  # Approver
    notes="Excellent work! Ready for submission."
)
```

### **Example 4: Check User Permission**
```python
from services.permissions_service import PermissionsService

can_approve = PermissionsService.user_has_permission(
    user_id=2,
    permission_name='approve_tenders',
    company_id=1
)
```

### **Example 5: Assign Role to User**
```python
from services.permissions_service import PermissionsService

success, message = PermissionsService.assign_role_to_user(
    user_id=5,
    role_id=3,  # Team Lead role
    assigned_by_id=1  # Admin assigning
)
```

---

## 🎨 UI Integration Points

### **Routes to Create**

1. **Tender Assignment**
   - Route: `/company/tender/<id>/assign`
   - Permission: `assign_tenders`
   - Shows list of company users to assign

2. **Submit for Approval**
   - Route: `/company/tender/<id>/submit-approval`
   - Permission: `submit_for_approval`
   - Confirmation dialog

3. **Approval Dashboard**
   - Route: `/company/approvals`
   - Permission: `approve_tenders`
   - Shows all pending approvals with approve/reject buttons

4. **Role Management**
   - Route: `/company/roles`
   - Permission: `manage_roles`
   - Create custom roles, assign permissions

5. **User Role Assignment**
   - Route: `/company/users/<id>/roles`
   - Permission: `assign_roles`
   - Assign/remove roles from users

6. **Tender Activity Log**
   - Route: `/company/tender/<id>/activity`
   - Permission: `view_tenders`
   - Complete audit trail

7. **Workflow Dashboard**
   - Route: `/company/workflow-stats`
   - Permission: `view_all_tenders`
   - Shows counts by status (draft, pending, approved, etc.)

---

## 🚀 Implementation Status

### ✅ Completed
- [x] 19 premium modules added to database
- [x] 28 permissions created
- [x] 6 default roles per company (24 total)
- [x] 9 database tables created
- [x] 80 existing tenders have workflows
- [x] PermissionsService complete
- [x] TenderWorkflowService complete
- [x] Database initialization scripts

### 📋 Next Steps (UI Implementation)
1. Create tender assignment interface
2. Create approval dashboard for approvers
3. Create role management interface for admins
4. Add workflow status badges to tender list
5. Create activity timeline component
6. Add document upload with workflow integration
7. Create permission-based menu system

---

## 💡 Key Benefits

### **For Company Admins**
- Full control over who can do what
- Audit trail of all tender activities
- Custom roles tailored to organization
- Track tender progress in real-time

### **For Team Members**
- Clear assignment and ownership
- Structured approval process
- Collaboration through comments
- Document version control

### **For Approvers**
- Centralized approval dashboard
- Review before submission
- Add approval notes
- Accept or reject with feedback

### **For the Business**
- Quality control through approvals
- Accountability through audit trail
- Scalable permission system
- Professional workflow management

---

## 📈 Revenue Model

### **Module Pricing Tiers**
- **Entry** (< R200): 11 modules = R1,469/month
- **Basic** (R200-R499): 12 modules = R4,338/month
- **Standard** (R500-R999): 11 modules = R8,089/month
- **Premium** (R1,000+): 3 modules = R4,797/month

### **Total Available**
- **Per Company**: R18,693/month (37 optional modules)
- **4 Companies**: R74,772/month
- **Annual**: R897,264/year

---

## 🔐 Security Features

1. **Permission-Based Access Control** - Every action checks permissions
2. **Audit Trail** - All activities logged with IP address
3. **Workflow Validation** - Can't skip steps (must approve before submit)
4. **Role Separation** - Clear separation of duties
5. **Company Isolation** - Users only see their company's data

---

## 📞 Support

For implementation assistance or questions:
- Check PermissionsService and TenderWorkflowService
- Review init_workflow_permissions.py for setup
- See add_premium_modules.py for module details
- All database tables are created and populated

---

**Status**: ✅ Backend Complete | 🔄 UI Pending | 🚀 Ready for Implementation
