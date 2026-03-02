# Flask App Implementation Summary

## Overview

A complete REST API Flask application has been created for the Redis Monitor project. This allows users to query farm metadata comparisons via HTTP POST requests instead of running CLI commands.

---

## What Was Created

### 1. Flask Application (`app.py`)
The main Flask REST API with the following endpoints:

**Health & Documentation:**
- `GET /health` - Health check
- `GET /api/docs` - API documentation

**Single Farm Monitoring:**
- `GET /api/monitor/<farm_id>` - Monitor via URL parameter
- `POST /api/monitor` - Monitor via JSON body

**Multiple Farm Comparison:**
- `POST /api/compare` - Compare multiple farms in one request

**Configuration:**
- `GET /api/config` - Get API configuration

### 2. HTML Report Generator (`src/html_reporter.py`)
Generates beautiful, interactive HTML reports with:
- Color-coded diff highlighting
  - 🟢 Green for additions
  - 🔴 Red for removals  
  - 🟡 Orange for value changes
  - 🔵 Blue for identical responses
- Expandable sections for detailed diffs
- Raw JSON response viewers
- Summary statistics
- Responsive design (desktop & mobile)

### 3. Updated Reporter (`src/reporter.py`)
Enhanced to support both JSON and HTML report generation:
- `generate_json_report()` - JSON report
- `generate_html_report()` - HTML report
- `generate_reports()` - Both reports in one call

### 4. Documentation

**API_DOCUMENTATION.md:**
- Complete endpoint reference
- Request/response examples
- cURL, Python, and JavaScript usage
- Error handling guide
- Performance considerations

**FLASK_APP_GUIDE.md:**
- Installation & setup instructions
- Running development server
- Production deployment (Gunicorn, Docker, Nginx)
- Troubleshooting guide
- Performance optimization tips

**example_requests.py:**
- 10 test cases covering all endpoints
- Color-coded output
- Error handling demonstrations
- Summary report with pass/fail status

**example_requests.sh:**
- Bash/cURL examples for all endpoints
- JSON output pretty-printing
- Ready to use on macOS/Linux

### 5. Updated Dependencies (`requirements-updated.txt`)
Added Flask support:
```
PyJWT==2.8.1
requests==2.31.0
deepdiff==6.1.1
python-dotenv==1.0.0
Flask==3.0.0
Werkzeug==3.0.0
```

---

## Key Features

### RESTful API Design
- Standard HTTP methods (GET, POST)
- Consistent JSON request/response format
- Proper HTTP status codes
- Comprehensive error handling
- CORS-ready (can be extended)

### Batch Processing
- Compare multiple farms in a single request
- Sequential processing (one farm at a time)
- Aggregated results with summary statistics

### Flexible Report Generation
- Optional JSON reports
- Optional HTML reports with diff styling
- Both generated simultaneously if requested
- Reports saved to `results/` directory

### Error Handling
- Validates required fields
- Handles API connection failures gracefully
- Returns informative error messages
- Proper HTTP status codes (400, 404, 500)

### Configuration Management
- All settings via `.env` file
- JWT token generation with configurable payload
- Configurable API endpoints and timeouts

---

## Usage

### Option 1: CLI (Original)
```bash
python redis_monitor.py
```
- Uses farm IDs from `.env` FARM_IDS variable
- Generates JSON and HTML reports
- Prints summary to console

### Option 2: REST API (New)
```bash
# Start server
python app.py

# In another terminal, make requests
curl -X POST http://localhost:5000/api/compare \
  -H "Content-Type: application/json" \
  -d '{"farmIds": ["farm-id-1", "farm-id-2"], "generateReport": true}'
```

### Option 3: Example Tests
```bash
# Run all test cases
python example_requests.py
```

---

## API Request Examples

### Single Farm (via /api/compare)
```json
{
  "farmIds": ["13f9ef67-19b0-4e3d-bec5-6dd15247492c"],
  "generateReport": false
}
```

### Multiple Farms
```json
{
  "farmIds": [
    "farm-id-1",
    "farm-id-2",
    "farm-id-3"
  ],
  "generateReport": true
}
```

### GET Endpoint
```
GET /api/monitor/13f9ef67-19b0-4e3d-bec5-6dd15247492c
```

---

## Response Structure

### Success Response
```json
{
  "status": "success",
  "summary": {
    "total": 2,
    "identical": 1,
    "different": 1,
    "errors": 0
  },
  "results": [
    {
      "farm_id": "...",
      "status": "success",
      "old_api": { ... },
      "new_api": { ... },
      "comparison": {
        "identical": false,
        "has_differences": true,
        "differences": { ... },
        "summary": { ... }
      },
      "timestamp": "2026-03-02T10:30:45.123456"
    }
  ],
  "reports": {
    "json": "results/comparison_report_20260302_103045.json",
    "html": "results/comparison_report_20260302_103045.html"
  }
}
```

### Error Response
```json
{
  "status": "error",
  "message": "Descriptive error message"
}
```

---

## Project Structure

```
redis-monitor/
├── app.py                          # Flask REST API
├── redis_monitor.py                # CLI script (original)
├── example_requests.py             # 10 test cases
├── example_requests.sh             # cURL examples
├── requirements-updated.txt        # Include Flask deps
├── API_DOCUMENTATION.md            # API reference
├── FLASK_APP_GUIDE.md              # Setup & deployment
├── FLASK_IMPLEMENTATION.md         # This file
├── src/
│   ├── config.py                  # Configuration loader
│   ├── auth.py                    # JWT generation
│   ├── api_client.py              # API client
│   ├── comparison.py              # Response comparison
│   ├── reporter.py                # JSON/console reporting
│   ├── html_reporter.py           # HTML report generation
│   └── __init__.py                # Package init
├── results/                        # Generated reports
└── .env                           # Configuration (secure)
```

---

## Installation & Running

```bash
# 1. Install dependencies
pip install -r requirements-updated.txt

# 2. Configure environment
cp .env.example .env
# Edit .env as needed

# 3. Run Flask server
python app.py

# API will be available at: http://localhost:5000
```

---

## Endpoints Quick Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Health check |
| GET | `/api/docs` | Documentation |
| POST | `/api/compare` | Compare multiple farms |
| GET | `/api/monitor/{id}` | Monitor single farm |
| POST | `/api/monitor` | Monitor single farm (POST) |
| GET | `/api/config` | Get configuration |

---

## Report Generation

### HTML Report Features
- ✓ Summary statistics with colored cards
- ✓ Status messages (success/warning/error)
- ✓ Expandable farm sections
- ✓ Color-coded differences
  - Green: Items added
  - Red: Items removed
  - Orange: Values changed
  - Blue: Identical
- ✓ Raw API response viewers
- ✓ Responsive design
- ✓ Interactive collapsible sections

### Report Files
- `comparison_report_{timestamp}.json` - Machine-readable report
- `comparison_report_{timestamp}.html` - Human-readable report with styling

---

## Process Flow

```
Client Request
    ↓
Flask Endpoint Handler
    ↓
Extract farm IDs from request body
    ↓
For each farm ID:
    ├─ Generate JWT token
    ├─ Fetch from OLD API
    ├─ Fetch from NEW API
    ├─ Compare responses
    └─ Store result
    ↓
Aggregate results & calculate summary
    ↓
[Optional] Generate JSON report
    ↓
[Optional] Generate HTML report
    ↓
Return JSON response to client
```

---

## Configuration

Key environment variables in `.env`:

```env
# API Endpoints
OLD_API_ENDPOINT=https://prodgateway.nitara.co.in/cm/GetFarmMetaDataNew
NEW_API_ENDPOINT=https://prodgateway.nitara.co.in/meta-data-api/farm-meta-data

# JWT Configuration
JWT_SECRET=12345678123456781234567812345678
TOKEN_EXPIRY_MINUTES=1440

# Request Configuration
REQUEST_TIMEOUT=30

# Output
OUTPUT_DIR=results
VERBOSE=False
```

---

## Next Steps / Recommendations

### Enhancement Ideas
1. **Add authentication** - JWT/API key validation
2. **Add rate limiting** - Prevent API abuse
3. **Add CORS support** - For cross-origin requests
4. **Add caching** - Cache responses for repeated requests
5. **Add webhooks** - Notify on comparison completion
6. **Add database** - Store historical comparison results
7. **Add scheduling** - Periodic automatic monitoring
8. **Add frontend UI** - Dashboard for results

### Deployment Recommendations
1. Use Gunicorn for production
2. Put behind Nginx reverse proxy
3. Use HTTPS/SSL certificates
4. Set proper environment variables
5. Monitor logs and API health
6. Set up database for history
7. Configure firewall rules

---

## Maintenance

### Regular Tasks
- Monitor API logs
- Check report generation
- Verify API endpoints are accessible
- Test error handling
- Update dependencies quarterly

### Troubleshooting
See `FLASK_APP_GUIDE.md` for common issues and solutions.

---

## Summary

The Flask app provides a modern REST API interface for the Redis Monitor project, enabling:
- ✅ HTTP/REST API access
- ✅ Batch farm comparison (multiple farms in one request)
- ✅ Sequential farm processing
- ✅ Beautiful HTML reports with diff styling
- ✅ JSON reports for data processing
- ✅ Easy integration with other systems
- ✅ Comprehensive documentation
- ✅ Example test cases
- ✅ Error handling & validation
- ✅ Production-ready code

The implementation maintains all original functionality while adding flexible API access patterns suitable for modern web architectures.
