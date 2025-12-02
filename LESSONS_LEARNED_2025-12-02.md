# Stripe Dashboard - Lessons Learned (2025-12-02)

## Overview
This document summarizes the key improvements and fixes made to the Stripe Dashboard Monthly Statement Generator on December 2, 2025.

---

## 1. Monthly Statement Generator Enhancements

### 1.1 Sales Transaction Details Section
Added a "Sales Transaction Details" section after the monthly statement table, displaying:
- Customer Email
- User Name
- Site/Service
- Subscription Plan
- Active Date / Expiry Date
- Original Amount / Converted Amount
- Processing Fee
- Customer ID / Transaction ID

**Files Modified:**
- `app/services/complete_csv_service.py` - Added `sales_details` building logic
- `app/routes/analytics.py` - Added JavaScript to render sale cards

### 1.2 Date Parsing Fix
Fixed date parsing to handle multiple formats including HTTP date format.

**Problem:** Transactions with HTTP date format (`Sun, 02 Nov 2025 03:19:33 GMT`) were not being parsed correctly.

**Solution:** Added multi-format date parsing:
```python
if 'T' in tx_date:
    # ISO format with T: "2025-11-02T12:00:00Z"
    date_key = dt.fromisoformat(tx_date.replace('Z', '+00:00')).date()
elif tx_date[:4].isdigit():
    # ISO format: "2025-11-02"
    date_key = dt.strptime(tx_date[:10], '%Y-%m-%d').date()
elif ',' in tx_date:
    # HTTP date format: "Sun, 02 Nov 2025 03:19:33 GMT"
    date_key = dt.strptime(tx_date, '%a, %d %b %Y %H:%M:%S %Z').date()
```

---

## 2. Nginx Proxy URL Handling

### Problem
When Flask app is accessed through nginx at `/stripe/`, JavaScript API calls using absolute paths (e.g., `/analytics/api/...`) fail because they bypass the nginx proxy.

### Solution
Use dynamic base path detection in JavaScript:
```javascript
const basePath = window.location.pathname.split('/analytics/')[0];
const response = await fetch(`${basePath}/analytics/api/stripe-monthly-statement?...`);
```

**Affected Functions:**
- `generateStatement()` - Statement generation API
- `exportPDF()` - PDF export API
- `exportCSV()` - CSV export API

### URL Reference
| Access Method | URL |
|--------------|-----|
| Through nginx (port 80) | `http://server/stripe/analytics/monthly-statement` |
| Direct Flask (port 8081) | `http://server:8081/analytics/monthly-statement` |

---

## 3. API Response Format Compatibility

### Problem
The `displayStatement()` function expected old API response format but the new API uses nested structure.

### Old Format
```javascript
statement.year
statement.month
statement.opening_balance
```

### New Format
```javascript
statement.period.year
statement.period.month
statement.summary.opening_balance
```

### Solution
Handle both formats with fallback:
```javascript
const year = (statement.period && statement.period.year) || statement.year || new Date().getFullYear();
const month = (statement.period && statement.period.month) || statement.month || new Date().getMonth() + 1;
const openingBalance = (statement.summary && statement.summary.opening_balance !== undefined)
    ? statement.summary.opening_balance
    : (statement.opening_balance || 0);
```

---

## 4. CSV Upload with Company Selection

### Enhancement
Added company selector to CSV upload page that:
1. Allows users to select company (CGGE, KI, KT) before upload
2. Automatically prefixes uploaded files with company code
3. Saves files to disk for monthly statement generator
4. Handles database errors gracefully (file saving takes priority)

### File Naming Convention
| Company | Prefix |
|---------|--------|
| CGGE | `cgge_` |
| Krystal Institute | `ki_` |
| Krystal Technology | `kt_` |

### Required Stripe Report Files
For monthly statement generation, upload these files per company:
- `{company}_Balance_Summary_HKD_{date-range}.csv`
- `{company}_Itemised_balance_change_from_activity_HKD_{date-range}.csv`
- `{company}_Itemised_payouts_HKD_{date-range}.csv`
- `{company}_unified_payments_{period}.csv` (optional, for customer details)

### Robust Upload Handler
```python
# Save file to disk first (PRIORITY)
save_path = os.path.join(root_dir, filename)
with open(save_path, 'wb') as f:
    f.write(file_content)
files_saved += 1

# Try database import (optional - don't fail if unavailable)
try:
    # ... database operations ...
except Exception as db_err:
    logger.warning(f"Database import skipped: {db_err}")
    continue  # File is saved, skip database import
```

---

## 5. Navigation Fixes

### Problem
After CSV upload, redirect to `/` went to Django instead of Flask.

### Solution
Use relative URLs for navigation:
```javascript
// Redirect after upload
window.location.href = 'monthly-statement';

// Back link
<a href="monthly-statement">← Back to Monthly Statement</a>

// Form submission
fetch('csv-upload', { method: 'POST', body: formData });
```

---

## 6. Key Files Modified

| File | Changes |
|------|---------|
| `app/routes/analytics.py` | URL handling, displayStatement fix, CSV upload with company selector |
| `app/services/complete_csv_service.py` | Sales details, date parsing |
| `app/templates/analytics/csv_upload.html` | Company selector UI, relative URLs |

---

## 7. Docker Deployment

Always remember to copy updated files to Docker container:
```bash
docker cp /path/to/file stripe-dashboard_stripe-dashboard_1:/app/path/to/file
docker restart stripe-dashboard_stripe-dashboard_1
```

Check logs for issues:
```bash
docker logs --tail 50 stripe-dashboard_stripe-dashboard_1
```

List CSV files in container:
```bash
docker exec stripe-dashboard_stripe-dashboard_1 find /app -name "*.csv" -type f
```

---

## 8. Architecture Summary

```
                    ┌─────────────────┐
                    │   Nginx (80)    │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
    ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
    │ Django (8080) │ │ Flask (8081)  │ │ Other Apps    │
    │ /             │ │ /stripe/      │ │ /expenses/    │
    │ Main Platform │ │ Stripe Dash   │ │ /crm/ etc     │
    └───────────────┘ └───────────────┘ └───────────────┘
```

---

## 9. Troubleshooting Checklist

- [ ] Accessing correct URL with `/stripe/` prefix?
- [ ] Hard refresh (Ctrl+Shift+R) to clear cached JavaScript?
- [ ] CSV files prefixed with correct company code?
- [ ] Docker container restarted after file changes?
- [ ] Check Docker logs for errors?

---

*Document created: 2025-12-02*
