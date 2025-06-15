# utils/export_helpers.py
import io
import xlsxwriter
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from flask import make_response
from datetime import datetime

def export_tenders_pdf(tenders, title, user):
    """Export tenders to PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.black,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    story.append(Paragraph(title, title_style))
    
    # Company info
    if not user.is_super_admin:
        company_info = f"Company: {user.company.name}"
        story.append(Paragraph(company_info, styles['Normal']))
    
    # Export date
    export_date = f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    story.append(Paragraph(export_date, styles['Normal']))
    story.append(Spacer(1, 20))
    
    if not tenders:
        story.append(Paragraph("No tenders found for this report.", styles['Normal']))
    else:
        # Table headers
        headers = ['Reference', 'Title', 'Category', 'Status', 'Created Date', 'Deadline']
        data = [headers]
        
        # Table data
        for tender in tenders:
            row = [
                tender.reference_number,
                tender.title[:30] + '...' if len(tender.title) > 30 else tender.title,
                tender.category.name if tender.category else 'N/A',
                tender.status.name if tender.status else 'N/A',
                tender.created_at.strftime('%Y-%m-%d') if tender.created_at else 'N/A',
                tender.submission_deadline.strftime('%Y-%m-%d') if tender.submission_deadline else 'N/A'
            ]
            data.append(row)
        
        # Create table
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    
    doc.build(story)
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{title.replace(" ", "_")}.pdf"'
    return response

def export_tenders_excel(tenders, title, user):
    """Export tenders to Excel"""
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet(title[:31])  # Excel sheet name limit
    
    # Formats
    header_format = workbook.add_format({
        'bold': True,
        'font_color': 'white',
        'bg_color': '#366092',
        'border': 1
    })
    
    cell_format = workbook.add_format({
        'border': 1,
        'text_wrap': True
    })
    
    # Headers
    headers = ['Reference Number', 'Title', 'Category', 'Status', 'Company', 'Created Date', 'Deadline', 'Days Overdue']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
    
    # Data
    for row, tender in enumerate(tenders, 1):
        days_overdue = ''
        if tender.submission_deadline and tender.submission_deadline < datetime.utcnow():
            days_overdue = (datetime.utcnow() - tender.submission_deadline).days
        
        worksheet.write(row, 0, tender.reference_number, cell_format)
        worksheet.write(row, 1, tender.title, cell_format)
        worksheet.write(row, 2, tender.category.name if tender.category else 'N/A', cell_format)
        worksheet.write(row, 3, tender.status.name if tender.status else 'N/A', cell_format)
        worksheet.write(row, 4, tender.company.name if tender.company else 'N/A', cell_format)
        worksheet.write(row, 5, tender.created_at.strftime('%Y-%m-%d') if tender.created_at else 'N/A', cell_format)
        worksheet.write(row, 6, tender.submission_deadline.strftime('%Y-%m-%d') if tender.submission_deadline else 'N/A', cell_format)
        worksheet.write(row, 7, str(days_overdue) if days_overdue else 'N/A', cell_format)
    
    # Adjust column widths
    worksheet.set_column('A:A', 15)  # Reference
    worksheet.set_column('B:B', 30)  # Title
    worksheet.set_column('C:C', 15)  # Category
    worksheet.set_column('D:D', 12)  # Status
    worksheet.set_column('E:E', 20)  # Company
    worksheet.set_column('F:F', 12)  # Created
    worksheet.set_column('G:G', 12)  # Deadline
    worksheet.set_column('H:H', 12)  # Days Overdue
    
    workbook.close()
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename="{title.replace(" ", "_")}.xlsx"'
    return response

def export_tenders_by_category_pdf(categories, user):
    """Export tenders by category to PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.black,
        spaceAfter=30,
        alignment=1
    )
    story.append(Paragraph("Tenders by Category Report", title_style))
    
    # Company info
    if not user.is_super_admin:
        company_info = f"Company: {user.company.name}"
        story.append(Paragraph(company_info, styles['Normal']))
    
    # Export date
    export_date = f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    story.append(Paragraph(export_date, styles['Normal']))
    story.append(Spacer(1, 20))
    
    for category_name, tenders in categories.items():
        # Category header
        story.append(Paragraph(f"Category: {category_name} ({len(tenders)} tenders)", styles['Heading2']))
        
        # Table for this category
        headers = ['Reference', 'Title', 'Status', 'Created Date']
        data = [headers]
        
        for tender in tenders:
            row = [
                tender.reference_number,
                tender.title[:40] + '...' if len(tender.title) > 40 else tender.title,
                tender.status.name if tender.status else 'N/A',
                tender.created_at.strftime('%Y-%m-%d') if tender.created_at else 'N/A'
            ]
            data.append(row)
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 20))
    
    doc.build(story)
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename="Tenders_by_Category_Report.pdf"'
    return response

def export_tenders_by_category_excel(categories, user):
    """Export tenders by category to Excel"""
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    
    # Formats
    header_format = workbook.add_format({
        'bold': True,
        'font_color': 'white',
        'bg_color': '#366092',
        'border': 1
    })
    
    category_format = workbook.add_format({
        'bold': True,
        'font_color': 'white',
        'bg_color': '#5B9BD5',
        'border': 1
    })
    
    cell_format = workbook.add_format({
        'border': 1,
        'text_wrap': True
    })
    
    # Create a worksheet for each category
    for category_name, tenders in categories.items():
        # Clean sheet name (Excel limitations)
        sheet_name = category_name[:31].replace('/', '_').replace('\\', '_')
        worksheet = workbook.add_worksheet(sheet_name)
        
        # Category header
        worksheet.merge_range('A1:E1', f'Category: {category_name}', category_format)
        
        # Headers
        headers = ['Reference Number', 'Title', 'Status', 'Created Date', 'Deadline']
        for col, header in enumerate(headers):
            worksheet.write(2, col, header, header_format)
        
        # Data
        for row, tender in enumerate(tenders, 3):
            worksheet.write(row, 0, tender.reference_number, cell_format)
            worksheet.write(row, 1, tender.title, cell_format)
            worksheet.write(row, 2, tender.status.name if tender.status else 'N/A', cell_format)
            worksheet.write(row, 3, tender.created_at.strftime('%Y-%m-%d') if tender.created_at else 'N/A', cell_format)
            worksheet.write(row, 4, tender.submission_deadline.strftime('%Y-%m-%d') if tender.submission_deadline else 'N/A', cell_format)
        
        # Adjust column widths
        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 40)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 12)
        worksheet.set_column('E:E', 12)
    
    workbook.close()
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename="Tenders_by_Category_Report.xlsx"'
    return response