#!/bin/bash
# Database Backup Script for Stripe Dashboard
# Optimized for Dell Linux Server deployment

set -euo pipefail

# Configuration
BACKUP_DIR="/backups"
DATA_DIR="/data"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_FILE="production.db"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$BACKUP_DIR/backup.log"
}

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR/database"
mkdir -p "$BACKUP_DIR/csv_data"

log "Starting backup process..."

# Check if source database exists
if [ ! -f "$DATA_DIR/$DB_FILE" ]; then
    log "WARNING: Database file $DATA_DIR/$DB_FILE not found"
    exit 0
fi

# Create database backup with SQLite vacuum
log "Creating database backup..."
BACKUP_FILE="$BACKUP_DIR/database/stripe_dashboard_${TIMESTAMP}.db"

# Use SQLite to create a clean backup
sqlite3 "$DATA_DIR/$DB_FILE" "VACUUM INTO '$BACKUP_FILE'"

if [ $? -eq 0 ]; then
    log "Database backup created: $BACKUP_FILE"
    
    # Compress the backup
    gzip "$BACKUP_FILE"
    log "Database backup compressed: ${BACKUP_FILE}.gz"
else
    log "ERROR: Failed to create database backup"
    exit 1
fi

# Create CSV data backup if directory exists
if [ -d "/app/csv_data" ]; then
    log "Creating CSV data backup..."
    CSV_BACKUP="$BACKUP_DIR/csv_data/csv_data_${TIMESTAMP}.tar.gz"
    tar -czf "$CSV_BACKUP" -C /app csv_data/
    
    if [ $? -eq 0 ]; then
        log "CSV data backup created: $CSV_BACKUP"
    else
        log "WARNING: Failed to create CSV data backup"
    fi
fi

# Clean up old backups
log "Cleaning up old backups (retention: $RETENTION_DAYS days)..."

# Remove old database backups
find "$BACKUP_DIR/database" -name "*.db.gz" -type f -mtime +$RETENTION_DAYS -delete
DELETED_DB=$(find "$BACKUP_DIR/database" -name "*.db.gz" -type f -mtime +$RETENTION_DAYS | wc -l)

# Remove old CSV backups
find "$BACKUP_DIR/csv_data" -name "*.tar.gz" -type f -mtime +$RETENTION_DAYS -delete
DELETED_CSV=$(find "$BACKUP_DIR/csv_data" -name "*.tar.gz" -type f -mtime +$RETENTION_DAYS | wc -l)

log "Cleanup completed. Deleted $DELETED_DB old database backups and $DELETED_CSV old CSV backups"

# Calculate backup sizes
DB_BACKUP_SIZE=$(du -sh "$BACKUP_DIR/database/${BACKUP_FILE##*/}.gz" 2>/dev/null | cut -f1 || echo "unknown")
TOTAL_BACKUP_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1 || echo "unknown")

log "Backup process completed successfully"
log "Current backup size: $DB_BACKUP_SIZE"
log "Total backup directory size: $TOTAL_BACKUP_SIZE"

# Create backup report
cat > "$BACKUP_DIR/latest_backup_report.txt" << EOF
Stripe Dashboard Backup Report
Generated: $(date)

Latest Backup:
- Database: ${BACKUP_FILE##*/}.gz ($DB_BACKUP_SIZE)
- CSV Data: csv_data_${TIMESTAMP}.tar.gz
- Status: SUCCESS

Retention Policy: $RETENTION_DAYS days
Total Backup Size: $TOTAL_BACKUP_SIZE

Backup Location: $BACKUP_DIR
EOF

log "Backup report created: $BACKUP_DIR/latest_backup_report.txt"

exit 0