#!/usr/bin/env python3
"""
Revamped Stripe Dashboard Server
Generates monthly statements consistent with Stripe's payout reconciliation reports
Uses dynamic data from CSV files with proper email addresses
"""

from flask import Flask, request, jsonify, render_template_string, Response
from datetime import datetime, timedelta
import sys
import os
import logging
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
import csv
from io import StringIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from io import BytesIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.services.complete_csv_service import CompleteCsvService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['DEBUG'] = False

# Initialize CSV service
csv_service = CompleteCsvService()

@app.route('/')
def home():
    """Main dashboard page"""
    logger.info("Homepage accessed")
    
    # Get available companies and months
    companies = csv_service.get_available_companies()
    months = csv_service.get_available_months()
    
    # Get the latest month's data for display
    if months:
        latest_year, latest_month = months[0]
        latest_data = {}
        
        for company in companies:
            reconciliation = csv_service.generate_payout_reconciliation(
                latest_year, latest_month, company['code']
            )
            if reconciliation:
                payout_rec = reconciliation['payout_reconciliation']
                latest_data[company['code']] = {
                    'name': company['name'],
                    'transactions': payout_rec['charges']['count'],
                    'gross': payout_rec['charges']['gross_amount'],
                    'fees': abs(payout_rec['charges']['fees']),
                    'net': payout_rec['total_paid_out']
                }
    else:
        latest_data = {}
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Stripe Dashboard - Revamped Version</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                background: #f8fafc; 
                margin: 0; 
                padding: 20px; 
            }}
            .container {{ 
                max-width: 1200px; 
                margin: 0 auto; 
            }}
            .header {{ 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; 
                padding: 40px; 
                text-align: center; 
                border-radius: 12px; 
                margin-bottom: 30px; 
            }}
            .badge {{ 
                background: rgba(255,255,255,0.2); 
                padding: 5px 15px; 
                border-radius: 20px; 
                font-size: 0.9rem; 
                margin-top: 10px; 
                display: inline-block; 
            }}
            .company-grid {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); 
                gap: 20px; 
                margin-bottom: 30px; 
            }}
            .company-card {{ 
                background: white; 
                padding: 25px; 
                border-radius: 12px; 
                box-shadow: 0 4px 12px rgba(0,0,0,0.1); 
            }}
            .company-header {{ 
                font-size: 1.2rem; 
                font-weight: bold; 
                margin-bottom: 15px; 
                color: #1e293b; 
                border-bottom: 2px solid #e5e7eb; 
                padding-bottom: 10px; 
            }}
            .metric {{ 
                display: flex; 
                justify-content: space-between; 
                padding: 8px 0; 
                border-bottom: 1px solid #f1f5f9; 
            }}
            .metric-label {{ 
                color: #64748b; 
            }}
            .metric-value {{ 
                font-weight: 600; 
                color: #1e293b; 
            }}
            .actions {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
                gap: 20px; 
                margin-top: 30px; 
            }}
            .action-card {{ 
                background: white; 
                padding: 30px; 
                border-radius: 12px; 
                text-align: center; 
                box-shadow: 0 4px 12px rgba(0,0,0,0.1); 
                transition: transform 0.2s; 
                cursor: pointer; 
            }}
            .action-card:hover {{ 
                transform: translateY(-2px); 
            }}
            .action-icon {{ 
                font-size: 2rem; 
                margin-bottom: 10px; 
            }}
            .action-title {{ 
                font-size: 1.1rem; 
                font-weight: bold; 
                margin-bottom: 8px; 
                color: #1e293b; 
            }}
            .action-desc {{ 
                color: #64748b; 
                font-size: 0.9rem; 
            }}
            .success {{ color: #10b981; }}
            .warning {{ color: #f59e0b; }}
            .info {{ color: #3b82f6; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Stripe Dashboard - Revamped</h1>
                <div class="badge">Dynamic CSV Data Processing</div>
                <p>Monthly Statements Consistent with Stripe Payout Reconciliation</p>
            </div>
            
            <div class="company-grid">
    '''
    
    # Add company cards with latest data
    for code, data in latest_data.items():
        fee_rate = (data['fees'] / data['gross'] * 100) if data['gross'] > 0 else 0
        html += f'''
                <div class="company-card">
                    <div class="company-header">{data['name']}</div>
                    <div class="metric">
                        <span class="metric-label">Latest Month:</span>
                        <span class="metric-value">{latest_month:02d}/{latest_year}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Transactions:</span>
                        <span class="metric-value">{data['transactions']}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Gross Amount:</span>
                        <span class="metric-value success">HK${data['gross']:,.2f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Processing Fees:</span>
                        <span class="metric-value warning">HK${data['fees']:,.2f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Net Amount:</span>
                        <span class="metric-value info">HK${data['net']:,.2f}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Fee Rate:</span>
                        <span class="metric-value">{fee_rate:.2f}%</span>
                    </div>
                </div>
        '''
    
    html += '''
            </div>
            
            <div class="actions">
                <a href="/monthly-statement" class="action-card" style="text-decoration: none; color: inherit;">
                    <div class="action-icon">📊</div>
                    <div class="action-title">Monthly Statement</div>
                    <div class="action-desc">Generate detailed monthly statements with individual transactions</div>
                </a>
                <a href="/payout-reconciliation" class="action-card" style="text-decoration: none; color: inherit;">
                    <div class="action-icon">💰</div>
                    <div class="action-title">Payout Reconciliation</div>
                    <div class="action-desc">Generate reports matching Stripe's payout reconciliation format</div>
                </a>
                <a href="/api/status" class="action-card" style="text-decoration: none; color: inherit;">
                    <div class="action-icon">🔌</div>
                    <div class="action-title">API Status</div>
                    <div class="action-desc">Check system status and data integrity</div>
                </a>
            </div>
        </div>
    </body>
    </html>
    '''
    
    return html

@app.route('/monthly-statement')
def monthly_statement_form():
    """Monthly statement generator form"""
    companies = csv_service.get_available_companies()
    months = csv_service.get_available_months()
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Monthly Statement Generator</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                margin: 20px; 
                background: #f8fafc; 
            }
            .container { 
                max-width: 800px; 
                margin: 0 auto; 
                background: white; 
                padding: 30px; 
                border-radius: 12px; 
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            .header { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; 
                padding: 20px; 
                border-radius: 8px; 
                margin-bottom: 30px; 
                text-align: center; 
            }
            .form-group { 
                margin-bottom: 20px; 
            }
            label { 
                display: block; 
                margin-bottom: 5px; 
                font-weight: bold; 
                color: #374151; 
            }
            select { 
                width: 100%; 
                padding: 12px; 
                border: 2px solid #e5e7eb; 
                border-radius: 8px; 
                font-size: 16px; 
                transition: border-color 0.2s; 
            }
            select:focus { 
                outline: none; 
                border-color: #667eea; 
            }
            .btn { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; 
                padding: 15px 30px; 
                border: none; 
                border-radius: 8px; 
                cursor: pointer; 
                font-size: 16px; 
                font-weight: 600; 
                transition: all 0.2s; 
                width: 100%;
            }
            .btn:hover { 
                transform: translateY(-1px); 
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
            }
            .back-link {
                display: inline-block;
                margin-top: 20px;
                color: #667eea;
                text-decoration: none;
            }
            .back-link:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>📊 Monthly Statement Generator</h2>
                <p>Generate detailed statements with individual transactions</p>
            </div>
            
            <form action="/generate-monthly-statement" method="GET">
                <div class="form-group">
                    <label for="company">Select Company:</label>
                    <select name="company" id="company" required>
                        <option value="">-- Select Company --</option>
    '''
    
    for company in companies:
        html += f'<option value="{company["code"]}">{company["name"]}</option>'
    
    html += '''
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="period">Select Month:</label>
                    <select name="period" id="period" required>
                        <option value="">-- Select Month --</option>
    '''
    
    for year, month in months:
        month_name = datetime(year, month, 1).strftime('%B %Y')
        html += f'<option value="{year}-{month:02d}">{month_name}</option>'
    
    html += '''
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="format">Output Format:</label>
                    <select name="format" id="format">
                        <option value="html">HTML (View in Browser)</option>
                        <option value="pdf">PDF (Download)</option>
                        <option value="csv">CSV (Download)</option>
                    </select>
                </div>
                
                <button type="submit" class="btn">Generate Statement</button>
            </form>
            
            <a href="/" class="back-link">← Back to Dashboard</a>
        </div>
    </body>
    </html>
    '''
    
    return html

@app.route('/generate-monthly-statement')
def generate_monthly_statement():
    """Generate monthly statement with individual transactions"""
    company = request.args.get('company', '')
    period = request.args.get('period', '')
    output_format = request.args.get('format', 'html')
    
    if not company or not period:
        return "Missing required parameters", 400
    
    try:
        year, month = period.split('-')
        year = int(year)
        month = int(month)
    except:
        return "Invalid period format", 400
    
    # Generate statement data
    statement = csv_service.generate_monthly_statement(year, month, company)
    
    if output_format == 'pdf':
        return generate_pdf_statement(statement, company)
    elif output_format == 'csv':
        return generate_csv_statement(statement, company)
    else:
        return generate_html_statement(statement, company)

def generate_html_statement(statement, company_code):
    """Generate HTML format monthly statement"""
    company_name = csv_service.company_names.get(company_code, 'Unknown')
    month_name = datetime(statement['year'], statement['month'], 1).strftime('%B %Y')
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>{company_name} - Monthly Statement {month_name}</title>
        <meta charset="UTF-8">
        <style>
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                margin: 20px; 
                background: #f8fafc; 
            }}
            .container {{ 
                max-width: 1400px; 
                margin: 0 auto; 
                background: white; 
                padding: 30px; 
                border-radius: 12px; 
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}
            .header {{ 
                border-bottom: 3px solid #667eea; 
                padding-bottom: 20px; 
                margin-bottom: 30px; 
            }}
            .company-name {{ 
                font-size: 2rem; 
                font-weight: bold; 
                color: #1e293b; 
            }}
            .statement-title {{ 
                font-size: 1.5rem; 
                color: #64748b; 
                margin-top: 10px; 
            }}
            .summary {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                gap: 20px; 
                margin-bottom: 30px; 
                padding: 20px; 
                background: #f8fafc; 
                border-radius: 8px; 
            }}
            .summary-item {{ 
                text-align: center; 
            }}
            .summary-label {{ 
                color: #64748b; 
                font-size: 0.9rem; 
                margin-bottom: 5px; 
            }}
            .summary-value {{ 
                font-size: 1.5rem; 
                font-weight: bold; 
                color: #1e293b; 
            }}
            table {{ 
                width: 100%; 
                border-collapse: collapse; 
                margin-top: 20px; 
            }}
            th {{ 
                background: #f8fafc; 
                padding: 12px; 
                text-align: left; 
                font-weight: 600; 
                color: #374151; 
                border-bottom: 2px solid #e5e7eb; 
            }}
            td {{ 
                padding: 10px 12px; 
                border-bottom: 1px solid #f1f5f9; 
            }}
            tr:hover {{ 
                background: #f8fafc; 
            }}
            .amount {{ 
                text-align: right; 
                font-family: 'Courier New', monospace; 
            }}
            .debit {{ 
                color: #059669; 
            }}
            .credit {{ 
                color: #dc2626; 
            }}
            .balance {{ 
                font-weight: 600; 
            }}
            .actions {{ 
                margin-top: 30px; 
                text-align: center; 
            }}
            .btn {{ 
                background: #667eea; 
                color: white; 
                padding: 12px 24px; 
                border: none; 
                border-radius: 8px; 
                cursor: pointer; 
                margin: 0 10px; 
                text-decoration: none; 
                display: inline-block; 
                font-weight: 600; 
            }}
            .btn:hover {{ 
                background: #5a67d8; 
            }}
            @media print {{
                .actions {{ display: none; }}
                body {{ background: white; }}
                .container {{ box-shadow: none; padding: 0; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="company-name">{company_name}</div>
                <div class="statement-title">Monthly Statement - {month_name}</div>
            </div>
            
            <div class="summary">
                <div class="summary-item">
                    <div class="summary-label">Opening Balance</div>
                    <div class="summary-value">HK${statement['opening_balance']:,.2f}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Total Debit</div>
                    <div class="summary-value debit">HK${statement['total_debit']:,.2f}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Total Credit</div>
                    <div class="summary-value credit">HK${statement['total_credit']:,.2f}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Closing Balance</div>
                    <div class="summary-value">HK${statement['closing_balance']:,.2f}</div>
                </div>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Nature</th>
                        <th>Party</th>
                        <th>Description</th>
                        <th class="amount">Debit (HKD)</th>
                        <th class="amount">Credit (HKD)</th>
                        <th class="amount">Balance (HKD)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>{statement['year']}-{statement['month']:02d}-01</td>
                        <td>Opening Balance</td>
                        <td>Brought Forward</td>
                        <td>Opening balance for {month_name}</td>
                        <td class="amount debit"></td>
                        <td class="amount credit"></td>
                        <td class="amount balance">HK${statement['opening_balance']:,.2f}</td>
                    </tr>
    '''
    
    # Add transaction rows
    for tx in statement['transactions']:
        date_str = tx['date'].strftime('%Y-%m-%d') if tx['date'] else ''
        party = tx.get('party', 'N/A')
        
        # Use email from party field (already extracted by CSV service)
        if '@' not in party and tx.get('raw_row'):
            # Try to get email from raw CSV row if not in party field
            email = tx['raw_row'].get('Customer Email', '').strip()
            if email:
                party = email
        
        debit_str = f"HK${tx['debit']:,.2f}" if tx['debit'] > 0 else ""
        credit_str = f"HK${tx['credit']:,.2f}" if tx['credit'] > 0 else ""
        
        html += f'''
                    <tr>
                        <td>{date_str}</td>
                        <td>{tx['nature']}</td>
                        <td>{party}</td>
                        <td>{tx['description'][:80]}...</td>
                        <td class="amount debit">{debit_str}</td>
                        <td class="amount credit">{credit_str}</td>
                        <td class="amount balance">HK${tx['balance']:,.2f}</td>
                    </tr>
        '''
    
    html += f'''
                    <tr style="font-weight: bold; background: #f8fafc;">
                        <td>{statement['year']}-{statement['month']:02d}-{csv_service._get_last_day_of_month(statement['year'], statement['month']):02d}</td>
                        <td>Closing Balance</td>
                        <td>Carry Forward</td>
                        <td>Closing balance for {month_name}</td>
                        <td class="amount debit"></td>
                        <td class="amount credit"></td>
                        <td class="amount balance">HK${statement['closing_balance']:,.2f}</td>
                    </tr>
                </tbody>
            </table>
            
            <div class="actions">
                <button class="btn" onclick="window.print()">Print Statement</button>
                <a href="/generate-monthly-statement?company={company_code}&period={statement['year']}-{statement['month']:02d}&format=pdf" class="btn">Download PDF</a>
                <a href="/generate-monthly-statement?company={company_code}&period={statement['year']}-{statement['month']:02d}&format=csv" class="btn">Download CSV</a>
                <a href="/monthly-statement" class="btn">New Statement</a>
                <a href="/" class="btn">Dashboard</a>
            </div>
        </div>
    </body>
    </html>
    '''
    
    return html

def generate_pdf_statement(statement, company_code):
    """Generate PDF format monthly statement"""
    company_name = csv_service.company_names.get(company_code, 'Unknown')
    month_name = datetime(statement['year'], statement['month'], 1).strftime('%B %Y')
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    # Title
    elements.append(Paragraph(company_name, title_style))
    elements.append(Paragraph(f"Monthly Statement - {month_name}", subtitle_style))
    elements.append(Spacer(1, 20))
    
    # Summary table
    summary_data = [
        ['Opening Balance:', f"HK${statement['opening_balance']:,.2f}"],
        ['Total Debit:', f"HK${statement['total_debit']:,.2f}"],
        ['Total Credit:', f"HK${statement['total_credit']:,.2f}"],
        ['Closing Balance:', f"HK${statement['closing_balance']:,.2f}"]
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#64748b')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1e293b')),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # Transaction table
    table_data = [['Date', 'Nature', 'Party', 'Debit', 'Credit', 'Balance']]
    
    # Add opening balance
    table_data.append([
        f"{statement['year']}-{statement['month']:02d}-01",
        'Opening Balance',
        'B/F',
        '',
        '',
        f"HK${statement['opening_balance']:,.2f}"
    ])
    
    # Add transactions
    for tx in statement['transactions']:
        date_str = tx['date'].strftime('%Y-%m-%d') if tx['date'] else ''
        party = tx.get('party', 'N/A')
        
        # Use email from party field
        if '@' not in party and tx.get('raw_row'):
            email = tx['raw_row'].get('Customer Email', '').strip()
            if email:
                party = email
        
        # Truncate party for PDF layout
        if len(party) > 30:
            party = party[:27] + '...'
        
        debit_str = f"HK${tx['debit']:,.2f}" if tx['debit'] > 0 else ""
        credit_str = f"HK${tx['credit']:,.2f}" if tx['credit'] > 0 else ""
        
        table_data.append([
            date_str,
            tx['nature'][:20],
            party,
            debit_str,
            credit_str,
            f"HK${tx['balance']:,.2f}"
        ])
    
    # Add closing balance
    table_data.append([
        f"{statement['year']}-{statement['month']:02d}-{csv_service._get_last_day_of_month(statement['year'], statement['month']):02d}",
        'Closing Balance',
        'C/F',
        '',
        '',
        f"HK${statement['closing_balance']:,.2f}"
    ])
    
    # Create table
    col_widths = [1.2*inch, 1.5*inch, 2*inch, 1*inch, 1*inch, 1.3*inch]
    transaction_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    # Apply table style
    transaction_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        
        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('ALIGN', (3, 0), (5, -1), 'RIGHT'),
        
        # Opening and closing balance rows
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f0fdf4')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0fdf4')),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    
    elements.append(transaction_table)
    
    # Build PDF
    doc.build(elements)
    
    buffer.seek(0)
    filename = f"{company_code.upper()}-MonthlyStatement_{statement['year']}_{statement['month']:02d}.pdf"
    
    return Response(
        buffer.read(),
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename={filename}'
        }
    )

def generate_csv_statement(statement, company_code):
    """Generate CSV format monthly statement"""
    csv_content = csv_service.export_monthly_statement_csv(statement)
    
    if not csv_content:
        return "Error generating CSV", 500
    
    filename = f"{company_code.upper()}-MonthlyStatement_{statement['year']}_{statement['month']:02d}.csv"
    
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename={filename}'
        }
    )

@app.route('/payout-reconciliation')
def payout_reconciliation_form():
    """Payout reconciliation form"""
    companies = csv_service.get_available_companies()
    months = csv_service.get_available_months()
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payout Reconciliation</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                margin: 20px; 
                background: #f8fafc; 
            }
            .container { 
                max-width: 800px; 
                margin: 0 auto; 
                background: white; 
                padding: 30px; 
                border-radius: 12px; 
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            .header { 
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                color: white; 
                padding: 20px; 
                border-radius: 8px; 
                margin-bottom: 30px; 
                text-align: center; 
            }
            .form-group { 
                margin-bottom: 20px; 
            }
            label { 
                display: block; 
                margin-bottom: 5px; 
                font-weight: bold; 
                color: #374151; 
            }
            select { 
                width: 100%; 
                padding: 12px; 
                border: 2px solid #e5e7eb; 
                border-radius: 8px; 
                font-size: 16px; 
                transition: border-color 0.2s; 
            }
            select:focus { 
                outline: none; 
                border-color: #10b981; 
            }
            .btn { 
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                color: white; 
                padding: 15px 30px; 
                border: none; 
                border-radius: 8px; 
                cursor: pointer; 
                font-size: 16px; 
                font-weight: 600; 
                transition: all 0.2s; 
                width: 100%;
            }
            .btn:hover { 
                transform: translateY(-1px); 
                box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
            }
            .info-box {
                background: #ecfdf5;
                border-left: 4px solid #10b981;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 4px;
            }
            .back-link {
                display: inline-block;
                margin-top: 20px;
                color: #10b981;
                text-decoration: none;
            }
            .back-link:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>💰 Payout Reconciliation</h2>
                <p>Generate reports matching Stripe's format</p>
            </div>
            
            <div class="info-box">
                <strong>Note:</strong> This report uses transfer dates to match Stripe's payout reconciliation format, 
                showing transactions that were paid out during the selected month.
            </div>
            
            <form action="/generate-payout-reconciliation" method="GET">
                <div class="form-group">
                    <label for="company">Select Company:</label>
                    <select name="company" id="company" required>
                        <option value="">-- Select Company --</option>
    '''
    
    for company in companies:
        html += f'<option value="{company["code"]}">{company["name"]}</option>'
    
    html += '''
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="period">Select Month:</label>
                    <select name="period" id="period" required>
                        <option value="">-- Select Month --</option>
    '''
    
    for year, month in months:
        month_name = datetime(year, month, 1).strftime('%B %Y')
        html += f'<option value="{year}-{month:02d}">{month_name}</option>'
    
    html += '''
                    </select>
                </div>
                
                <button type="submit" class="btn">Generate Reconciliation</button>
            </form>
            
            <a href="/" class="back-link">← Back to Dashboard</a>
        </div>
    </body>
    </html>
    '''
    
    return html

@app.route('/generate-payout-reconciliation')
def generate_payout_reconciliation():
    """Generate payout reconciliation report"""
    company = request.args.get('company', '')
    period = request.args.get('period', '')
    
    if not company or not period:
        return "Missing required parameters", 400
    
    try:
        year, month = period.split('-')
        year = int(year)
        month = int(month)
    except:
        return "Invalid period format", 400
    
    # Generate reconciliation data
    reconciliation = csv_service.generate_payout_reconciliation(year, month, company)
    company_name = csv_service.company_names.get(company, 'Unknown')
    month_name = datetime(year, month, 1).strftime('%B %Y')
    
    payout = reconciliation['payout_reconciliation']
    ending = reconciliation['ending_balance_reconciliation']
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payout Reconciliation - {company_name} {month_name}</title>
        <meta charset="UTF-8">
        <style>
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                margin: 20px; 
                background: #f8fafc; 
            }}
            .container {{ 
                max-width: 1200px; 
                margin: 0 auto; 
                background: white; 
                padding: 30px; 
                border-radius: 12px; 
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}
            .header {{ 
                border-bottom: 3px solid #10b981; 
                padding-bottom: 20px; 
                margin-bottom: 30px; 
            }}
            .company-name {{ 
                font-size: 2rem; 
                font-weight: bold; 
                color: #1e293b; 
            }}
            .report-title {{ 
                font-size: 1.5rem; 
                color: #64748b; 
                margin-top: 10px; 
            }}
            .section {{ 
                margin-bottom: 40px; 
            }}
            .section-title {{ 
                font-size: 1.2rem; 
                font-weight: bold; 
                color: #1e293b; 
                margin-bottom: 20px; 
                padding: 10px; 
                background: #f0fdf4; 
                border-left: 4px solid #10b981; 
            }}
            .reconciliation-table {{ 
                width: 100%; 
                border-collapse: collapse; 
            }}
            .reconciliation-table th {{ 
                background: #f8fafc; 
                padding: 12px; 
                text-align: left; 
                font-weight: 600; 
                color: #374151; 
                border-bottom: 2px solid #e5e7eb; 
            }}
            .reconciliation-table td {{ 
                padding: 10px 12px; 
                border-bottom: 1px solid #f1f5f9; 
            }}
            .amount {{ 
                text-align: right; 
                font-family: 'Courier New', monospace; 
            }}
            .total-row {{ 
                font-weight: bold; 
                background: #f0fdf4; 
            }}
            .actions {{ 
                margin-top: 30px; 
                text-align: center; 
            }}
            .btn {{ 
                background: #10b981; 
                color: white; 
                padding: 12px 24px; 
                border: none; 
                border-radius: 8px; 
                cursor: pointer; 
                margin: 0 10px; 
                text-decoration: none; 
                display: inline-block; 
                font-weight: 600; 
            }}
            .btn:hover {{ 
                background: #059669; 
            }}
            @media print {{
                .actions {{ display: none; }}
                body {{ background: white; }}
                .container {{ box-shadow: none; padding: 0; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="company-name">{company_name}</div>
                <div class="report-title">Payout Reconciliation - {month_name}</div>
            </div>
            
            <div class="section">
                <div class="section-title">Payout Reconciliation</div>
                <table class="reconciliation-table">
                    <thead>
                        <tr>
                            <th>Type</th>
                            <th>Count</th>
                            <th class="amount">Gross Amount (HKD)</th>
                            <th class="amount">Fees (HKD)</th>
                            <th class="amount">Net Amount (HKD)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Charges</td>
                            <td>{payout['charges']['count']}</td>
                            <td class="amount">HK${payout['charges']['gross_amount']:,.2f}</td>
                            <td class="amount">HK${abs(payout['charges']['fees']):,.2f}</td>
                            <td class="amount">HK${payout['charges']['gross_amount'] + payout['charges']['fees']:,.2f}</td>
                        </tr>
                        <tr>
                            <td>Refunds</td>
                            <td>{payout['refunds']['count']}</td>
                            <td class="amount">HK${payout['refunds']['gross_amount']:,.2f}</td>
                            <td class="amount">-</td>
                            <td class="amount">HK${payout['refunds']['gross_amount']:,.2f}</td>
                        </tr>
                        <tr>
                            <td>Payout Reversals</td>
                            <td>{payout['payout_reversals']['count']}</td>
                            <td class="amount">HK${payout['payout_reversals']['gross_amount']:,.2f}</td>
                            <td class="amount">-</td>
                            <td class="amount">HK${payout['payout_reversals']['gross_amount']:,.2f}</td>
                        </tr>
                        <tr class="total-row">
                            <td>Total Paid Out</td>
                            <td>{payout['charges']['count'] + payout['refunds']['count'] + payout['payout_reversals']['count']}</td>
                            <td class="amount">-</td>
                            <td class="amount">-</td>
                            <td class="amount">HK${payout['total_paid_out']:,.2f}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <div class="section-title">Ending Balance Reconciliation</div>
                <table class="reconciliation-table">
                    <thead>
                        <tr>
                            <th>Type</th>
                            <th>Count</th>
                            <th class="amount">Gross Amount (HKD)</th>
                            <th class="amount">Fees (HKD)</th>
                            <th class="amount">Net Amount (HKD)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Charges</td>
                            <td>{ending['charges']['count']}</td>
                            <td class="amount">HK${ending['charges']['gross_amount']:,.2f}</td>
                            <td class="amount">HK${abs(ending['charges']['fees']):,.2f}</td>
                            <td class="amount">HK${ending['charges']['gross_amount'] + ending['charges']['fees']:,.2f}</td>
                        </tr>
                        <tr>
                            <td>Payout Reversals</td>
                            <td>{ending['payout_reversals']['count']}</td>
                            <td class="amount">HK${ending['payout_reversals']['gross_amount']:,.2f}</td>
                            <td class="amount">-</td>
                            <td class="amount">HK${ending['payout_reversals']['gross_amount']:,.2f}</td>
                        </tr>
                        <tr class="total-row">
                            <td>Ending Balance</td>
                            <td>{ending['charges']['count'] + ending['payout_reversals']['count']}</td>
                            <td class="amount">-</td>
                            <td class="amount">-</td>
                            <td class="amount">HK${ending['ending_balance']:,.2f}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div class="actions">
                <button class="btn" onclick="window.print()">Print Report</button>
                <a href="/payout-reconciliation" class="btn">New Report</a>
                <a href="/" class="btn">Dashboard</a>
            </div>
        </div>
    </body>
    </html>
    '''
    
    return html

@app.route('/api/status')
def api_status():
    """API status endpoint"""
    logger.info("API status requested")
    
    companies = csv_service.get_available_companies()
    months = csv_service.get_available_months()
    
    # Get sample data for the latest month
    sample_data = {}
    if months:
        latest_year, latest_month = months[0]
        for company in companies:
            reconciliation = csv_service.generate_payout_reconciliation(
                latest_year, latest_month, company['code']
            )
            if reconciliation:
                payout = reconciliation['payout_reconciliation']
                sample_data[company['code']] = {
                    'name': company['name'],
                    'latest_month': f"{latest_year}-{latest_month:02d}",
                    'transactions': payout['charges']['count'],
                    'gross_amount': payout['charges']['gross_amount'],
                    'fees': abs(payout['charges']['fees']),
                    'net_amount': payout['total_paid_out']
                }
    
    return jsonify({
        'status': 'operational',
        'version': 'revamped',
        'timestamp': datetime.now().isoformat(),
        'data_source': 'CSV files (complete_csv directory)',
        'features': {
            'monthly_statement': 'operational',
            'payout_reconciliation': 'operational',
            'pdf_export': 'operational',
            'csv_export': 'operational',
            'email_extraction': 'operational'
        },
        'available_companies': [c['name'] for c in companies],
        'available_months': [f"{y}-{m:02d}" for y, m in months[:12]],  # Last 12 months
        'sample_data': sample_data,
        'improvements': [
            'Dynamic data processing from CSV files',
            'Email addresses used instead of self-explanatory text',
            'Consistent with Stripe payout reconciliation format',
            'No hardcoded datasets',
            'PDF export with proper formatting',
            'Individual transaction listing'
        ]
    })

if __name__ == '__main__':
    logger.info("Starting Revamped Stripe Dashboard Server...")
    logger.info("Using dynamic CSV data processing")
    logger.info("Access at: http://localhost:8081")
    
    try:
        # Check for required dependencies
        import pandas
        import reportlab
        logger.info("All required dependencies found")
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.error("Please install: pip install pandas reportlab")
        sys.exit(1)
    
    try:
        app.run(host='0.0.0.0', port=8081, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)