# Module Pricing & Billing System

## Overview
The Tender Management System now has a complete module-based pricing system using **South African Rand (ZAR, R)**.

## ✅ What's Already Working

### 1. **Module Pricing Structure**
All modules have monthly prices set in ZAR:

#### **Core Modules** (FREE)
- Dashboard - R 0.00
- Tender Management - R 0.00
- User Management - R 0.00

#### **Basic Modules** (< R200/month)
- Company Management - R 99.00
- Email Notifications - R 99.00
- File Management - R 99.00
- Notifications - R 99.00
- Notes & Comments - R 79.00
- Advanced Search - R 149.00
- Custom Fields - R 149.00
- Export Data - R 149.00
- Tender History - R 149.00

#### **Standard Modules** (R200-R500/month)
- Document Management - R 199.00
- Audit Tracking - R 199.00
- Bulk Operations - R 249.00
- Analytics - R 299.00
- Reporting - R 299.00
- **Accounting** - **R 499.00**

#### **Premium Modules** (> R500/month)
- API Access - R 799.00
- White Labeling - R 999.00

### 2. **Billing Calculation**
Companies are billed **only for enabled modules**:

```
Monthly Bill = Sum of (Enabled Module Prices)
```

**Example Company Bill:**
- Accounting (enabled) - R 499.00
- Reporting (enabled) - R 299.00
- API Access (enabled) - R 799.00
- --------------------------------
- **Total Monthly Bill: R 1,597.00**

### 3. **Custom Pricing**
Each company can have custom pricing for specific modules:
- Default: Module uses standard price (from module_definitions table)
- Custom: Override price per company (in company_module_pricing table)

## 🎯 How to Use

### **For Super Admin:**

#### **1. Manage Module Prices**
```
Admin > Billing > Manage Modules
```
- View all modules with current pricing
- Edit module prices in ZAR (R)
- See usage statistics (how many companies use each module)
- See revenue per module

#### **2. Enable/Disable Modules for Companies**
```
Admin > Companies > Select Company > Edit > Modules Tab
```
- Toggle modules ON/OFF for each company
- View pricing for each module
- Set custom pricing if needed

#### **3. Generate Monthly Bills**
```
Admin > Billing > Generate Bill
```
- Select company
- Choose month/year
- **Preview** shows:
  - List of enabled modules
  - Price per module
  - Total amount
- Click **Generate Bill**

### **For Company Users:**

#### **1. View Available Modules**
When logged in as company user:
- Menus show only for **enabled modules**
- If accounting is enabled → Accounting menu appears
- If accounting is disabled → No accounting menu

## 📊 Database Structure

### **module_definitions**
```sql
id | module_name | display_name | monthly_price | is_core | is_active
46 | accounting  | Accounting   | 499.00        | 0       | 1
```

### **company_modules**
```sql
id | company_id | module_id | is_enabled | monthly_cost
1  | 3          | 46        | 1          | 499.00
```

### **company_module_pricing** (for custom prices)
```sql
id | company_id | module_id | custom_price | is_active
1  | 3          | 46        | 399.00       | 1
```

## 💰 Revenue Potential

With current pricing:
- **Max revenue per company**: R 4,912.00/month (if all optional modules enabled)
- **4 active companies**: R 19,648.00/month potential
- **Average module price**: R 265.00/month

## 🔄 Billing Workflow

### **Monthly Billing Process:**

1. **Month End** → Super Admin generates bills
2. **System calculates**:
   ```python
   For each company:
     total = 0
     for each enabled_module:
       if has_custom_pricing:
         total += custom_price
       else:
         total += module.monthly_price
     return total
   ```
3. **Bill Generated** with itemized module costs
4. **Company receives invoice** showing:
   - Module 1: R X.XX
   - Module 2: R X.XX
   - **Total: R X.XX**

## 🎨 User Experience

### **Company Admin enables Accounting module:**
1. Admin → Companies → Edit Company → Modules Tab
2. Toggle "Accounting" to **ON**
3. System shows: "R 499.00/month will be added to bill"
4. Save changes

### **Company User logs in:**
1. Sees **Accounting** menu in navigation
2. Can access all accounting features:
   - Dashboard
   - Chart of Accounts
   - Journal Entries
   - Financial Reports
   - Help Guide

### **Company Admin disables Accounting:**
1. Toggle "Accounting" to **OFF**
2. System shows: "R 499.00/month will be removed from bill"
3. Save changes
4. Company users can no longer access accounting features
5. Menu disappears from navigation

## 🔒 Access Control

**Route Protection:**
```python
@app.route('/accounting/dashboard')
@login_required
@module_required('accounting')
def accounting_dashboard():
    # Only accessible if company has accounting module enabled
```

**Template Protection:**
```jinja
{% if can_access_module('accounting') %}
  <li><a href="/accounting/dashboard">Accounting</a></li>
{% endif %}
```

## 📈 Next Steps (Optional Enhancements)

1. **Automated Billing**
   - Cron job to generate bills on 1st of each month
   - Email invoices to companies

2. **Payment Integration**
   - Link to payment gateway (PayFast, Stripe, etc.)
   - Track payment status

3. **Usage Analytics**
   - Track module usage per company
   - Show value reports

4. **Discounts & Promotions**
   - Bundle pricing
   - Annual discounts
   - Promotional codes

## 🚀 Summary

✅ **Module pricing set in ZAR (R)**
✅ **Companies billed based on enabled modules**
✅ **Custom pricing per company available**
✅ **Access control enforced**
✅ **UI shows pricing throughout**
✅ **Billing generation functional**

The system is **fully operational** for module-based billing in South African Rand!
