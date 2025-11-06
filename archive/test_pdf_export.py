#!/usr/bin/env python3
"""
Test script to generate a sample PDF using our updated styling
"""

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from io import BytesIO

def create_test_pdf():
    """Create a test PDF with the new styling"""
    
    # Create PDF in memory
    buffer = BytesIO()
    
    # Create PDF document with landscape orientation for better table fit
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                          rightMargin=0.5*inch, leftMargin=0.5*inch,
                          topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.white,
        alignment=1,  # Center alignment
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.white,
        alignment=1,
        spaceAfter=12
    )
    
    # Build PDF content
    story = []
    
    # Header with blue background
    header_data = [[
        Paragraph("📄 Monthly Statement Generator", title_style),
    ], [
        Paragraph("Generate consolidated monthly statements with running balance", subtitle_style)
    ]]
    
    header_table = Table(header_data, colWidths=[8*inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.Color(91/255, 130/255, 243/255)),  # Blue background
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 20))
    
    # Summary information
    summary_data = [
        ['Company:', 'cgge'],
        ['Period:', 'July 2025'],
        ['Opening Balance:', 'HK$831.42'],
        ['Closing Balance:', 'HK$554.77'],
        ['Total Transactions:', '50']
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.Color(227/255, 242/255, 253/255)),  # Light blue
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.Color(13/255, 71/255, 161/255)),     # Dark blue
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 2, colors.Color(25/255, 118/255, 210/255)),      # Blue border
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    # Transaction table
    table_data = [['Date', 'Nature', 'Party', 'Debit', 'Credit', 'Balance', 'Ack', 'Description']]
    
    # Opening balance row
    table_data.append([
        "2025-07-01",
        "Opening Balance", 
        "Brought Forward",
        "",
        "",
        "HK$831.42",
        "Yes",
        "Opening balance for July 2025"
    ])
    
    # Sample transaction rows
    sample_transactions = [
        ["2025-07-02", "Gross Charge", "User 924", "HK$96.61", "", "HK$928.03", "No", "Gross"],
        ["2025-07-02", "Processing Fee", "Stripe", "HK$6.12", "", "HK$921.91", "No", "Processing fee for"],
        ["2025-07-03", "Payout", "STRIPE PAYOUT", "", "HK$831.42", "HK$90.49", "No", "STRIPE PAYOUT"],
        ["2025-07-05", "Gross Payment", "User 954", "HK$96.62", "", "HK$187.11", "No", "Gross"],
    ]
    
    for tx in sample_transactions:
        table_data.append(tx)
    
    # Subtotal row
    table_data.append([
        "SUBTOTAL",
        "",
        "",
        "HK$2360.13",
        "HK$2729.30",
        "",
        "",
        ""
    ])
    
    # Closing balance row
    table_data.append([
        "2025-07-31",
        "Closing Balance",
        "Carry Forward",
        "",
        "",
        "HK$554.77",
        "Yes",
        "Closing balance for July 2025"
    ])
    
    # Create table with appropriate column widths for landscape
    col_widths = [0.8*inch, 1*inch, 1.2*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.5*inch, 1.5*inch]
    table = Table(table_data, colWidths=col_widths)
    
    # Style the table to match PDF sample
    table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(245/255, 245/255, 245/255)),  # Light grey
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.Color(51/255, 51/255, 51/255)),       # Dark grey
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        
        # Opening balance row
        ('BACKGROUND', (0, 1), (-1, 1), colors.Color(240/255, 249/255, 255/255)),   # Light blue
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        
        # Data rows - white background
        ('BACKGROUND', (0, 2), (-1, -3), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.Color(153/255, 153/255, 153/255)),     # Grey borders
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        
        # Subtotal row with orange background
        ('BACKGROUND', (0, -2), (-1, -2), colors.Color(255/255, 243/255, 205/255)), # Light orange
        ('FONTNAME', (0, -2), (-1, -2), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, -2), (-1, -2), colors.Color(180/255, 83/255, 9/255)),     # Dark orange
        
        # Closing balance row
        ('BACKGROUND', (0, -1), (-1, -1), colors.Color(240/255, 249/255, 255/255)), # Light blue
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        
        # Align amounts to right
        ('ALIGN', (3, 1), (5, -1), 'RIGHT'),
        ('ALIGN', (6, 0), (6, -1), 'CENTER'),  # Acknowledged column center
        ('ALIGN', (0, 0), (2, -1), 'LEFT'),    # Date, Nature, Party left aligned
    ]))
    
    story.append(table)
    
    # Build PDF
    doc.build(story)
    
    # Get PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    # Save to file
    with open('/Users/wongivan/company_apps/stripe-dashboard/test_statement_styled.pdf', 'wb') as f:
        f.write(pdf_data)
    
    print("✅ Test PDF generated: test_statement_styled.pdf")

if __name__ == "__main__":
    create_test_pdf()