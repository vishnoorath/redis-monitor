# Redis Monitor - Farm Metadata Comparison Tool

A Python monitoring script that compares farm metadata responses between **old database-backed API** and **new Redis-based API** to validate data consistency and monitor the migration.

## Features

- **Dual API Comparison**: Fetch farm metadata from both old database and new Redis APIs simultaneously
- **JWT Authentication**: Automatic token generation with configurable payload
- **Deep Comparison**: Uses DeepDiff library to identify all differences between responses
- **Batch Processing**: Monitor multiple farms in a single run
- **Comprehensive Reporting**: Console output + detailed JSON reports with timestamps
- **Error Handling**: Robust error handling with clear logging of API failures
- **Configurable**: All settings managed via `.env` file

## Installation

### 1. Clone or navigate to the project directory
```bash
cd redis-monitor
```

### 2. Create Python virtual environment (recommended)
```bash
python -m venv venv
source venv/Scripts/activate  # On Windows
# or
source venv/bin/activate  # On macOS/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your settings
# - Set JWT_SECRET (default is provided for testing)
# - Set farm IDs to monitor (comma-separated)
# - Adjust API endpoints if needed
```

## Configuration

Edit `.env` file to configure:

```env
# JWT Configuration
JWT_SECRET=12345678123456781234567812345678      # Token signing secret
TOKEN_EXPIRY_MINUTES=1440                        # Token validity (default: 24 hours)

# API Endpoints
OLD_API_ENDPOINT=https://prodgateway.nitara.co.in/cm/GetFarmMetaDataNew
NEW_API_ENDPOINT=https://prodgateway.nitara.co.in/meta-data-api/farm-meta-data

# Request Configuration
REQUEST_TIMEOUT=30                               # HTTP request timeout in seconds

# Farm IDs to Monitor (comma-separated)
FARM_IDS=13f9ef67-19b0-4e3d-bec5-6dd15247492c,other-farm-id-here

# JWT Payload Configuration
JWT_USER_ID=c512c47d-1237-49fc-9168-bab3a2bd8b57
JWT_DEVICE_ID=7e01d642-75d1-4831-b5a6-7466e64c5c32
JWT_LANGUAGE=EN
JWT_ROLE=VETERINARIAN, FARMER, NITARA FIELD ADMIN
# ... (other JWT fields)

# Output Configuration
OUTPUT_DIR=results                               # Directory for JSON reports
VERBOSE=False                                    # Enable verbose logging
```

## Usage

### Run the monitor
```bash
python redis_monitor.py
```

### Example Output

```
================================================================================
REDIS MONITOR - Farm Metadata Comparison Tool
================================================================================
Started at: 2026-03-02 10:30:45
================================================================================

→ Found 1 farm(s) to compare

[1/1] Processing Farm: 13f9ef67-19b0-4e3d-bec5-6dd15247492c
--------------------------------------------------------------------------------
→ Requesting OLD DB API: https://prodgateway.nitara.co.in/cm/GetFarmMetaDataNew
✓ OLD DB API response received (1250 bytes)
→ Requesting NEW REDIS API: https://prodgateway.nitara.co.in/meta-data-api/farm-meta-data
✓ NEW REDIS API response received (1250 bytes)

COMPARISON RESULT:
--------------------------------------------------------------------------------
✓ Responses are IDENTICAL - No differences found

================================================================================
SUMMARY
================================================================================
Total farms compared: 1
Identical responses: 1 ✓
Different responses: 0 ❌
Errors/Failures: 0 ⚠

✓ All farm metadata is synchronized! No discrepancies found.
================================================================================

✓ Full report saved to: results/comparison_report_20260302_103045.json
```

## Output

### Console Output
- Real-time status of API requests
- Comparison results per farm
- Summary statistics

### JSON Report (in `results/` directory)
```json
{
  "metadata": {
    "generated_at": "2026-03-02T10:30:45.123456",
    "test_run_id": "20260302_103045",
    "total_farms_compared": 1,
    "farms_identical": 1,
    "farms_with_differences": 0,
    "farms_with_errors": 0
  },
  "results": [
    {
      "farm_id": "13f9ef67-19b0-4e3d-bec5-6dd15247492c",
      "old_api": { ... },
      "new_api": { ... },
      "comparison": {
        "identical": true,
        "has_differences": false,
        "differences": {},
        "summary": { ... }
      },
      "timestamp": "2026-03-02T10:30:45.123456"
    }
  ]
}
```

### HTML Report (in `results/` directory)
A beautifully formatted interactive HTML report with:
- **Summary Cards**: Visual overview of results (identical, different, errors)
- **Color-Coded Diffs**: 
  - 🟢 Green for added items
  - 🔴 Red for removed items
  - 🟡 Orange for changed values
  - 🔵 Blue for identical responses
- **Expandable Sections**: Show/hide raw API responses and detailed differences
- **Responsive Design**: Works on desktop and mobile devices
- **Easy Navigation**: Click on any farm to expand detailed comparison results

#### Features:
- Interactive collapsible sections for each farm
- Detailed diff highlighting for changed values
- Side-by-side comparison of old vs new API responses
- Raw JSON responses for debugging
- Summary statistics at the top
- Generated timestamp and run ID

## Project Structure

```
redis-monitor/
├── redis_monitor.py          # Main orchestration script
├── requirements.txt          # Python dependencies
├── .env.example              # Configuration template
├── .gitignore               # Git ignore rules
├── TASK.md                  # Original task requirements
├── PLAN.md                  # Implementation plan
├── README.md                # This file
├── src/
│   ├── config.py            # Configuration management
│   ├── auth.py              # JWT token generation
│   ├── api_client.py        # API request handling
│   ├── comparison.py        # Response comparison logic
│   ├── reporter.py          # Console and JSON reporting
│   ├── html_reporter.py     # HTML report generation with diff styling
│   └── __init__.py          # Package initialization
└── results/                 # Generated JSON and HTML reports
```

## Exit Codes

- `0`: Success - All farms matched, no discrepancies
- `1`: Error - One or more API requests failed
- `2`: Differences found - Responses differ between APIs (review JSON report)

## Troubleshooting

### ModuleNotFoundError: No module named 'src'
Make sure you run the script from the project root directory:
```bash
cd redis-monitor
python redis_monitor.py
```

### Missing dependencies
Install all required packages:
```bash
pip install -r requirements.txt
```

### API Connection Errors
- Check your internet connection
- Verify API endpoints in `.env` are correct
- Check if the APIs are accessible and not down for maintenance
- Verify JWT secret is correct

### Token Generation Fails
- Ensure all JWT_* environment variables are set correctly
- Check that JWT_SECRET is a valid string

## Dependencies

- **PyJWT** - JWT token generation and handling
- **requests** - HTTP requests to APIs
- **deepdiff** - Deep comparison of JSON responses
- **python-dotenv** - Environment variable management

See `requirements.txt` for specific versions.

## License

Internal tool for farm metadata validation.

## Author

Created: March 2, 2026
