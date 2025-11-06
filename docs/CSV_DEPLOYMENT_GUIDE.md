# CSV Data Integration - Deployment Guide

## Overview
This guide documents the fixes implemented for CSV data integration issues in production deployment. The stripe-dashboard application now has robust CSV functionality that works in both development and production environments.

## Issues Fixed

### 1. Hard-coded File Paths
**Problem**: CSV service used hard-coded paths like `/Users/wongivan/stripe-dashboard/new_csv`
**Solution**: Implemented flexible path resolution that works across environments

### 2. Missing CSV Directory Structure  
**Problem**: Expected `new_csv` directory didn't exist, data was in `july25/`
**Solution**: Added multi-location path detection and fallback mechanisms

### 3. CSV Format Compatibility
**Problem**: Expected "Itemised_balance_change_from_activity_*.csv" format but had "unified_payments_*.csv" 
**Solution**: Added support for multiple CSV formats with automatic detection

### 4. Poor Error Handling
**Problem**: Missing files caused application crashes
**Solution**: Implemented graceful error handling and fallback mechanisms

### 5. Container/Deployment Path Issues
**Problem**: No adaptation for Docker containers or different server environments
**Solution**: Added environment variable support and deployment-friendly configurations

## New Features Added

### 1. Robust Path Resolution
The CSV service now tries multiple locations in order of preference:
```
1. Environment variable: CSV_DATA_PATH
2. Current working directory: july25/, new_csv/, csv_data/
3. App root relative paths  
4. Docker container paths: /app/july25, /app/new_csv
5. Fallback development paths
```

### 2. Multiple CSV Format Support
- **Unified Payments Format**: `*unified_payments_*.csv` (current format)
- **Balance Change Format**: `Itemised_balance_change_from_activity_*.csv` (legacy)
- **Generic CSV Format**: Fallback parser for any CSV with transaction data

### 3. Health Monitoring
- New endpoint: `/analytics/api/csv-health`
- Returns CSV directory status, file count, and transaction totals
- Proper error reporting for deployment monitoring

### 4. CSV Export Functionality
- New endpoint: `/analytics/api/csv-export`
- Supports filtered exports with query parameters
- Generates downloadable CSV files with proper headers

### 5. Enhanced Error Handling
- Graceful degradation when CSV files are missing
- Detailed logging for debugging production issues
- Continues processing even when individual files fail

## Environment Configuration

### Environment Variables
```bash
# CSV data directory path (optional)
CSV_DATA_PATH=/path/to/csv/files

# Database configuration
DATABASE_URL=sqlite:///instance/payments.db

# Flask configuration
FLASK_ENV=production
SECRET_KEY=your-secret-key
```

### Docker Configuration
The Dockerfile now includes:
```dockerfile
# Create CSV directories
RUN mkdir -p instance csv_data july25 && chmod 755 instance csv_data july25

# Create backward compatibility symlink
RUN ln -sf july25 new_csv

# Set CSV data path
ENV CSV_DATA_PATH=/app/july25
```

## API Endpoints

### Health Check
```
GET /analytics/api/csv-health

Response:
{
  "status": "healthy",
  "csv_directory": "/app/july25",
  "csv_files_found": 3,
  "total_transactions": 115,
  "csv_files": ["cgge_unified_payments_20250731.csv", ...],
  "timestamp": "2025-08-08T10:04:01.541049"
}
```

### CSV Export
```
GET /analytics/api/csv-export?company=1&status=succeeded

Response: Downloadable CSV file
Content-Type: text/csv
Content-Disposition: attachment; filename="transactions_export_YYYYMMDD_HHMMSS.csv"
```

## Testing

### Local Testing
```bash
# Test CSV service directly
python -c "
from app.services.csv_transaction_service import CSVTransactionService
service = CSVTransactionService()
print(service.get_health_status())
"

# Test with Flask app
python -c "
from app import create_app
app = create_app()
with app.app_context():
    from app.services.csv_transaction_service import CSVTransactionService
    service = CSVTransactionService()
    transactions = service.get_all_transactions()
    print(f'Found {len(transactions)} transactions')
"
```

### Production Health Check
```bash
# Check CSV functionality in production
curl https://your-domain.com/analytics/api/csv-health

# Export transactions
curl -O https://your-domain.com/analytics/api/csv-export
```

## Deployment Checklist

### 1. Verify CSV Files
- [ ] CSV files exist in accessible location
- [ ] Files have correct permissions (readable by application)
- [ ] File format is supported (unified_payments or balance_change)

### 2. Environment Setup
- [ ] Set CSV_DATA_PATH if using custom location
- [ ] Verify database connectivity
- [ ] Set proper Flask environment variables

### 3. Container Deployment
- [ ] CSV files copied to container during build
- [ ] Proper directory permissions set
- [ ] Environment variables configured

### 4. Health Verification
- [ ] `/analytics/api/csv-health` returns healthy status
- [ ] Transaction count matches expected values
- [ ] CSV export functionality works

### 5. Error Monitoring
- [ ] Application logs show CSV service initialization
- [ ] No file permission errors in logs
- [ ] Health check endpoint monitored

## Troubleshooting

### Common Issues

**Issue**: "No CSV files found"
**Solution**: 
1. Check CSV_DATA_PATH environment variable
2. Verify files exist and are readable
3. Check file naming patterns match expected formats

**Issue**: "Permission denied reading CSV file"
**Solution**:
1. Fix file permissions: `chmod 644 *.csv`
2. Fix directory permissions: `chmod 755 csv_directory`
3. Ensure application user can read files

**Issue**: "Error parsing CSV row"
**Solution**:
1. Check CSV file format and headers
2. Look for encoding issues (ensure UTF-8)
3. Check for malformed rows in CSV files

**Issue**: "CSV directory not found"
**Solution**:
1. Set CSV_DATA_PATH environment variable
2. Create directory structure if missing
3. Copy CSV files to expected location

## Performance Considerations

### CSV File Size
- Large CSV files are processed in memory
- Consider chunked processing for files > 100MB
- Monitor memory usage during CSV operations

### Caching
- Transaction data is loaded fresh each request
- Consider implementing caching for better performance
- Use Redis or similar for production caching

### File Access
- CSV files are read-only operations
- Multiple concurrent reads are safe
- Consider file locking if writes are needed

## Security Considerations

### File Access
- CSV files should not be web-accessible
- Place outside document root
- Use proper file permissions (644 for files, 755 for directories)

### Data Privacy
- CSV files may contain sensitive customer data
- Ensure proper access controls
- Consider encryption for sensitive fields

### Input Validation
- All CSV data is validated during parsing
- Malformed rows are skipped gracefully
- SQL injection protection in place

## Backup and Recovery

### CSV Data Backup
```bash
# Backup CSV files
tar -czf csv_backup_$(date +%Y%m%d).tar.gz july25/

# Restore CSV files  
tar -xzf csv_backup_YYYYMMDD.tar.gz
```

### Database Integration
- CSV data can be imported to database via import scripts
- Database provides persistent storage and better performance
- CSV files serve as backup/archive data source

## Monitoring and Alerts

### Health Monitoring
Monitor the `/analytics/api/csv-health` endpoint:
- Should return 200 status code
- Should show "healthy" status
- Should report expected transaction counts

### Log Monitoring
Watch for these log messages:
- "Found CSV directory: /path/to/csv"
- "Found N CSV files in directory"
- "Retrieved N transactions from N CSV files"

### Error Alerts
Alert on these conditions:
- CSV health check returns error status
- Zero transactions found when data expected
- File permission errors in logs
- CSV parsing errors exceeding threshold

---

*This deployment guide ensures robust CSV functionality across all deployment environments.*