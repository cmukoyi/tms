# Create services/billing_service.py

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import and_, or_, extract
from models import db, Company, CompanyModule, ModuleDefinition, CompanyModulePricing, MonthlyBill, BillLineItem, User
import calendar

class BillingService:
    """Service for handling billing operations"""
    
    @staticmethod
    def set_custom_pricing(company_id, module_id, custom_price, created_by, notes=None, effective_date=None):
        """Set custom pricing for a company module"""
        try:
            if effective_date is None:
                effective_date = datetime.utcnow()
            
            # Deactivate existing custom pricing
            existing_pricing = CompanyModulePricing.query.filter_by(
                company_id=company_id,
                module_id=module_id,
                is_active=True
            ).all()
            
            for pricing in existing_pricing:
                pricing.is_active = False
            
            # Create new custom pricing
            new_pricing = CompanyModulePricing(
                company_id=company_id,
                module_id=module_id,
                custom_price=Decimal(str(custom_price)),
                effective_date=effective_date,
                created_by=created_by,
                notes=notes,
                is_active=True
            )
            
            db.session.add(new_pricing)
            db.session.commit()
            
            return True, "Custom pricing set successfully"
        
        except Exception as e:
            db.session.rollback()
            return False, f"Error setting custom pricing: {str(e)}"
    
    @staticmethod
    def remove_custom_pricing(company_id, module_id):
        """Remove custom pricing for a company module"""
        try:
            custom_pricing = CompanyModulePricing.query.filter_by(
                company_id=company_id,
                module_id=module_id,
                is_active=True
            ).all()
            
            for pricing in custom_pricing:
                pricing.is_active = False
            
            db.session.commit()
            return True, "Custom pricing removed successfully"
        
        except Exception as e:
            db.session.rollback()
            return False, f"Error removing custom pricing: {str(e)}"
    
    @staticmethod
    def get_company_pricing(company_id):
        """Get all pricing information for a company"""
        try:
            # Get all enabled modules for the company
            enabled_modules = db.session.query(CompanyModule, ModuleDefinition).join(ModuleDefinition).filter(
                CompanyModule.company_id == company_id,
                CompanyModule.is_enabled == True
            ).all()
            
            pricing_data = []
            
            for company_module, module_def in enabled_modules:
                # Check for custom pricing
                custom_pricing = CompanyModulePricing.query.filter_by(
                    company_id=company_id,
                    module_id=module_def.id,
                    is_active=True
                ).order_by(CompanyModulePricing.effective_date.desc()).first()
                
                effective_price = custom_pricing.custom_price if custom_pricing else module_def.monthly_price
                
                pricing_data.append({
                    'company_module': company_module,
                    'module_definition': module_def,
                    'default_price': float(module_def.monthly_price) if module_def.monthly_price else 0.0,
                    'custom_price': float(custom_pricing.custom_price) if custom_pricing else None,
                    'effective_price': float(effective_price) if effective_price else 0.0,
                    'has_custom_pricing': custom_pricing is not None,
                    'custom_pricing_notes': custom_pricing.notes if custom_pricing else None,
                    'custom_pricing_effective_date': custom_pricing.effective_date if custom_pricing else None
                })
            
            return pricing_data
        
        except Exception as e:
            print(f"Error getting company pricing: {str(e)}")
            return []
    
    @staticmethod
    def calculate_monthly_total(company_id, year=None, month=None):
        """Calculate total monthly bill for a company"""
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month
        
        pricing_data = BillingService.get_company_pricing(company_id)
        total = sum(item['effective_price'] for item in pricing_data)
        
        return {
            'company_id': company_id,
            'year': year,
            'month': month,
            'total_amount': total,
            'currency': 'ZAR',
            'line_items': pricing_data
        }
    
    @staticmethod
    def generate_monthly_bill(company_id, year, month, generated_by, notes=None):
        """Generate a monthly bill for a company"""
        try:
            # Check if bill already exists
            existing_bill = MonthlyBill.query.filter_by(
                company_id=company_id,
                bill_year=year,
                bill_month=month
            ).first()
            
            if existing_bill:
                return False, "Bill already exists for this period"
            
            # Get pricing data
            billing_data = BillingService.calculate_monthly_total(company_id, year, month)
            
            if not billing_data['line_items']:
                return False, "No enabled modules found for billing"
            
            # Create bill
            bill = MonthlyBill(
                company_id=company_id,
                bill_year=year,
                bill_month=month,
                total_amount=Decimal(str(billing_data['total_amount'])),
                currency=billing_data['currency'],
                generated_by=generated_by,
                notes=notes,
                status='draft'
            )
            
            db.session.add(bill)
            db.session.flush()  # Get the bill ID
            
            # Create line items
            for item in billing_data['line_items']:
                line_item = BillLineItem(
                    bill_id=bill.id,
                    module_id=item['module_definition'].id,
                    module_name=item['module_definition'].module_name,
                    module_display_name=item['module_definition'].display_name,
                    unit_price=Decimal(str(item['effective_price'])),
                    quantity=1,
                    line_total=Decimal(str(item['effective_price'])),
                    is_custom_price=item['has_custom_pricing'],
                    pricing_notes=item['custom_pricing_notes']
                )
                db.session.add(line_item)
            
            db.session.commit()
            return True, f"Bill generated successfully for {calendar.month_name[month]} {year}"
        
        except Exception as e:
            db.session.rollback()
            return False, f"Error generating bill: {str(e)}"
    
    @staticmethod
    def get_bills_with_filters(company_id=None, start_date=None, end_date=None, status=None):
        """Get bills with optional filters"""
        try:
            query = MonthlyBill.query
            
            if company_id:
                query = query.filter(MonthlyBill.company_id == company_id)
            
            if start_date:
                query = query.filter(MonthlyBill.bill_date >= start_date)
            
            if end_date:
                query = query.filter(MonthlyBill.bill_date <= end_date)
            
            if status:
                query = query.filter(MonthlyBill.status == status)
            
            bills = query.order_by(MonthlyBill.bill_date.desc()).all()
            return [bill.to_dict() for bill in bills]
        
        except Exception as e:
            print(f"Error getting bills: {str(e)}")
            return []
    
    @staticmethod
    def get_billing_summary():
        """Get billing summary for all companies"""
        try:
            # Get all companies with enabled modules
            companies_with_modules = db.session.query(
                Company.id,
                Company.name,
                db.func.count(CompanyModule.id).label('module_count'),
                db.func.sum(ModuleDefinition.monthly_price).label('default_total')
            ).join(CompanyModule).join(ModuleDefinition).filter(
                CompanyModule.is_enabled == True
            ).group_by(Company.id, Company.name).all()
            
            summary = []
            for company_id, company_name, module_count, default_total in companies_with_modules:
                # Get actual pricing (including custom pricing)
                pricing_data = BillingService.get_company_pricing(company_id)
                actual_total = sum(item['effective_price'] for item in pricing_data)
                
                # Get latest bill
                latest_bill = MonthlyBill.query.filter_by(company_id=company_id).order_by(
                    MonthlyBill.bill_date.desc()
                ).first()
                
                summary.append({
                    'company_id': company_id,
                    'company_name': company_name,
                    'module_count': module_count,
                    'default_total': float(default_total) if default_total else 0.0,
                    'actual_total': actual_total,
                    'has_custom_pricing': actual_total != (float(default_total) if default_total else 0.0),
                    'latest_bill_date': latest_bill.bill_date if latest_bill else None,
                    'latest_bill_status': latest_bill.status if latest_bill else None
                })
            
            return summary
        
        except Exception as e:
            print(f"Error getting billing summary: {str(e)}")
            return []
    
    @staticmethod
    def update_bill_status(bill_id, new_status, updated_by):
        """Update bill status"""
        try:
            bill = MonthlyBill.query.get(bill_id)
            if not bill:
                return False, "Bill not found"
            
            bill.status = new_status
            db.session.commit()
            
            return True, f"Bill status updated to {new_status}"
        
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating bill status: {str(e)}"
    
    @staticmethod
    def delete_bill(bill_id):
        """Delete a bill and its line items"""
        try:
            bill = MonthlyBill.query.get(bill_id)
            if not bill:
                return False, "Bill not found"
            
            # Line items will be deleted automatically due to cascade
            db.session.delete(bill)
            db.session.commit()
            
            return True, "Bill deleted successfully"
        
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting bill: {str(e)}"