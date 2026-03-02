# Redis Monitor - Quick Start Guide

Get up and running with the Redis Monitor web UI in **5 minutes**.

---

## Prerequisites

- Python 3.8 or higher
- Flask 3.0.0
- `requests` library for HTTP
- `PyJWT` for token generation
- `deepdiff` for comparison

---

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**What gets installed:**
- Flask 3.0.0 - Web framework
- Werkzeug 3.0.0 - WSGI utilities
- PyJWT - JWT token generation
- requests - HTTP requests
- deepdiff - Deep comparison
- python-dotenv - Environment variables

---

## 2. Configure Environment

Create a `.env` file with your API credentials:

```bash
# Copy the example
cp .env.example .env

# Then edit .env with your values
```

**Required values in .env:**
```env
# JWT Configuration
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_TOKEN_EXPIRY=3600

# API Endpoints
OLD_API_BASE=http://api.internal:8080/api/farms
NEW_API_BASE=http://redis-api.internal:8080/api/farms

# API Credentials
API_USERNAME=your-username
API_PASSWORD=your-password

# Application Settings
API_TIMEOUT=30
DEBUG=False
```

---

## 3. Start the Application

```bash
python app.py
```

You should see:
```
 * Running on http://127.0.0.1:5000
 * Web UI Available: http://127.0.0.1:5000
 * API Docs: http://127.0.0.1:5000/api/docs
```

---

## 4. Access the Web UI

Open your browser and go to:
```
http://localhost:5000
```

You'll see the Redis Monitor dashboard with:
- Input form for farm IDs
- Quick reference guide
- Getting started instructions

---

## 5. Run Your First Comparison

### Via Web UI (Easiest)

1. **Enter a farm ID** in the textarea
2. **Click "Compare Farms"**
3. **View results** inline in the browser

Example farm ID:
```
13f9ef67-19b0-4e3d-bec5-6dd15247492c
```

### Via REST API (Advanced)

```bash
curl -X POST http://localhost:5000/api/compare \
  -H "Content-Type: application/json" \
  -d '{
    "farmIds": ["13f9ef67-19b0-4e3d-bec5-6dd15247492c"],
    "generateReport": true
  }'
```

---

## Common Tasks

### Check Server Health

```bash
curl http://localhost:5000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Generate Reports Programmatically

Check the `/api/compare` endpoint:
```bash
curl -X POST http://localhost:5000/api/compare \
  -H "Content-Type: application/json" \
  -d '{
    "farmIds": ["farm-1", "farm-2", "farm-3"],
    "generateReport": true
  }'
```

### View API Documentation

Visit: `http://localhost:5000/api/docs`

Shows all available endpoints with examples.

---

## File Structure

```
redis-monitor/
├── app.py                    # Main Flask application
├── redis_monitor.py          # Original CLI tool (optional)
├── requirements.txt          # Python dependencies
├── .env.example             # Configuration template
├── .env                     # Your configuration (local only)
│
├── src/                     # Python modules
│   ├── config.py           # Configuration loading
│   ├── auth.py             # JWT token generation
│   ├── api_client.py       # API requests
│   ├── comparison.py       # DeepDiff comparison
│   ├── reporter.py         # JSON/console reports
│   └── html_reporter.py    # HTML report generation
│
├── templates/              # Jinja2 templates for web UI
│   ├── base.html          # Base layout
│   ├── index.html         # Dashboard page
│   └── report.html        # Results display
│
├── static/                # Static assets
│   ├── css/               # Stylesheets (future)
│   └── js/                # JavaScript (future)
│
├── results/               # Generated reports
│   ├── comparison_report_TIMESTAMP.json
│   └── comparison_report_TIMESTAMP.html
│
└── documentation/         # Guides and references
```

---

## Web UI Features

### Dashboard (`/`)
- ✅ Beautiful input form
- ✅ Farm ID textarea (supports multiple formats)
- ✅ Optional report generation checkbox
- ✅ Quick reference and getting started

### Comparison Results (`/compare`)
- ✅ Summary statistics (identical, different, errors)
- ✅ Color-coded status indicators
- ✅ Expandable sections for details
- ✅ Raw JSON response viewer
- ✅ Pretty-printed differences

### REST API Endpoints
- `GET /` - Web dashboard
- `GET /health` - Server health check
- `POST /api/compare` - Batch farm comparison
- `GET /api/monitor/<farm_id>` - Single farm via URL
- `POST /api/monitor` - Single farm via JSON body
- `GET /api/config` - Configuration info
- `GET /api/docs` - API documentation

---

## Input Formats

The web UI supports multiple ways to enter farm IDs:

### One per line
```
farm-id-1
farm-id-2
farm-id-3
```

### Comma-separated
```
farm-id-1, farm-id-2, farm-id-3
```

### Mixed
```
farm-id-1, farm-id-2
farm-id-3
farm-id-4, farm-id-5
```

All formats work the same way!

---

## Understanding Results

### Summary Cards
Shows 4 key metrics:
- 🟢 **Identical** - Farms with matching responses
- 🟡 **Different** - Farms with differences found
- 🔴 **Errors** - Farms with API failures
- ⚪ **Total** - Total farms processed

### Color Meanings
- 🟢 **Green** - Success, identical, matches
- 🟡 **Orange** - Warning, different, changes
- 🔴 **Red** - Error, failure, missing
- ⚪ **Gray** - Neutral, informational

### Expandable Sections
Click any "Details" or "Responses" button to see:
- **Values Changed** - What fields differ and their values
- **Items Added** - New items in the new API
- **Items Removed** - Items missing in the new API
- **Type Changes** - When data types changed
- **Raw Responses** - Complete JSON from both APIs

---

## Generating Reports

### Without Files (Default)
- Comparison happens instantly
- Results displayed in browser
- No files saved to disk

### With File Reports
1. **Check "Generate Reports"** checkbox
2. **Click "Compare Farms"**
3. Files saved to `results/` directory:
   - `comparison_report_TIMESTAMP.json` - Machine-readable
   - `comparison_report_TIMESTAMP.html` - Shareable report

---

## Troubleshooting

### Port Already in Use

```bash
# If port 5000 is busy, edit app.py:
# Change: app.run(debug=False)
# To:     app.run(debug=False, port=5001)
```

### Module Import Error

```bash
# Make sure you're in the right directory
cd path/to/redis-monitor

# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### Environment Variables Not Loading

```bash
# Verify .env file exists
ls -la .env

# Make sure values are set
cat .env | grep JWT_SECRET

# Check Python can read it
python -c "from src.config import Config; print(Config.JWT_SECRET)"
```

### API Connection Failed

```bash
# Verify endpoints in .env are correct
cat .env | grep API_BASE

# Test connectivity
curl -v http://api.internal:8080/api/farms

# Check timeout setting
cat .env | grep API_TIMEOUT
```

---

## Next Steps

### 1. Explore the Web UI
- Visit http://localhost:5000
- Try comparing a single farm
- Review the results display

### 2. Read Full Documentation
- [WEB_UI_GUIDE.md](WEB_UI_GUIDE.md) - Complete UI documentation
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - REST API reference
- [FLASK_APP_GUIDE.md](FLASK_APP_GUIDE.md) - Setup and deployment

### 3. Try Advanced Features
- Generate file-based reports
- Use the REST API programmatically
- Compare large batches of farms
- Schedule periodic monitoring

### 4. Integration & Deployment
- Integrate with other systems via API
- Schedule monitoring with cron or CI/CD
- Deploy to production with Gunicorn
- Add custom authentication

---

## Key Commands

```bash
# Start the server
python app.py

# Test via curl
curl http://localhost:5000/health

# Check API endpoints
curl http://localhost:5000/api/docs

# View configuration
cat .env

# Run original CLI tool (if needed)
python redis_monitor.py

# Install dependencies
pip install -r requirements.txt

# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Tips & Tricks

### ✅ Do This
- Start with single farm to test setup
- Check `/health` endpoint to verify server
- Use web UI for occasional checks
- Export reports for documentation
- Archive important results
- Test API endpoints with curl/Postman

### ❌ Don't Do This
- Don't expose `.env` file publicly
- Don't commit `.env` to version control
- Don't ignore API errors
- Don't rely only on browser history
- Don't share raw API credentials
- Don't run with `debug=True` in production

---

## Performance

### Speed Expectations
- **Per Farm**: 1-5 seconds
- **5 Farms**: 5-25 seconds
- **50 Farms**: 50-250 seconds
- **Batch of 100**: 100-500 seconds

Factors affecting speed:
- Network latency to APIs
- API response time
- Server processing power
- JSON complexity

### Optimization Tips
- Don't generate files for speed
- Avoid very large batches (>50 at once)
- Use API endpoints for automation
- Cache results if monitoring same farms

---

## Support & Help

### Getting Help
1. **Check Dashboard** - Has "How It Works" section
2. **Read Guides** - Start with this file
3. **View API Docs** - Visit `/api/docs` in browser
4. **Check Logs** - Server console shows errors
5. **Inspect Browser** - Press F12 for dev tools

### Documentation Files
- `README.md` - Project overview
- `QUICK_START.md` - This file
- `WEB_UI_GUIDE.md` - UI reference
- `API_DOCUMENTATION.md` - API endpoints
- `FLASK_APP_GUIDE.md` - Setup details

---

## Summary

**Redis Monitor Web UI** provides an easy, visual way to compare farm metadata:

✅ **5-minute setup** - Install, configure, run  
✅ **Beautiful UI** - No technical knowledge needed  
✅ **Instant results** - No file downloads  
✅ **Optional exports** - Save reports when needed  
✅ **REST API** - Programmatic access available  
✅ **Easy to deploy** - Works on any server  

**Ready to start?**
```bash
python app.py
# Then open http://localhost:5000
```

Happy monitoring! 🚀
