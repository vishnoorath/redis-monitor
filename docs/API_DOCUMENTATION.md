# Flask REST API - Redis Monitor

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements-updated.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Run the Flask Server
```bash
python app.py
```

The API will be available at `http://localhost:5000`

## API Documentation

### Base URL
```
http://localhost:5000
```

### Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/docs` | API documentation |
| POST | `/api/compare` | Compare multiple farms |
| GET | `/api/monitor/<farm_id>` | Monitor single farm (GET) |
| POST | `/api/monitor` | Monitor single farm (POST) |
| GET | `/api/config` | Get API configuration |

---

## Endpoint Details

### 1. Health Check
**Endpoint:** `GET /health`

Check if the API server is running and healthy.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "Redis Monitor API",
  "timestamp": "2026-03-02T10:30:45.123456"
}
```

---

### 2. Compare Multiple Farms
**Endpoint:** `POST /api/compare`

Compare farm metadata between old and new APIs for multiple farms in a single request.

**Request:**
```json
{
  "farmIds": [
    "13f9ef67-19b0-4e3d-bec5-6dd15247492c",
    "farm-id-2",
    "farm-id-3"
  ],
  "generateReport": true
}
```

**Parameters:**
- `farmIds` (required, array): List of farm IDs to compare
- `generateReport` (optional, boolean): Generate JSON and HTML reports (default: false)

**Response (200 OK):**
```json
{
  "status": "success",
  "summary": {
    "total": 3,
    "identical": 2,
    "different": 1,
    "errors": 0
  },
  "results": [
    {
      "farm_id": "13f9ef67-19b0-4e3d-bec5-6dd15247492c",
      "status": "success",
      "old_api": {
        "id": 1,
        "name": "Farm 1",
        "status": "active"
      },
      "new_api": {
        "id": 1,
        "name": "Farm 1",
        "status": "active"
      },
      "comparison": {
        "identical": true,
        "has_differences": false,
        "differences": {},
        "summary": {
          "values_changed": 0,
          "items_added": 0,
          "items_removed": 0,
          "type_changes": 0,
          "repetition_changes": 0
        }
      },
      "timestamp": "2026-03-02T10:30:45.123456"
    }
  ],
  "reports": {
    "json": "results/comparison_report_20260302_103045.json",
    "html": "results/comparison_report_20260302_103045.html"
  },
  "timestamp": "2026-03-02T10:30:45.123456"
}
```

**Error Response (400 Bad Request):**
```json
{
  "status": "error",
  "message": "Missing required field: farmIds",
  "example": {
    "farmIds": ["farm-id-1", "farm-id-2"],
    "generateReport": true
  }
}
```

---

### 3. Monitor Single Farm (GET)
**Endpoint:** `GET /api/monitor/<farm_id>`

Monitor a single farm using URL parameter.

**URL Parameters:**
- `farm_id` (required): The farm ID to monitor

**Example:**
```
GET /api/monitor/13f9ef67-19b0-4e3d-bec5-6dd15247492c
```

**Response (200 OK):**
```json
{
  "farm_id": "13f9ef67-19b0-4e3d-bec5-6dd15247492c",
  "status": "success",
  "old_api": { ... },
  "new_api": { ... },
  "comparison": { ... },
  "timestamp": "2026-03-02T10:30:45.123456"
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "farm_id": "13f9ef67-19b0-4e3d-bec5-6dd15247492c",
  "status": "error",
  "error": "Error message details",
  "old_api": null,
  "new_api": null,
  "comparison": {
    "error": "Error message details",
    "has_differences": true
  },
  "timestamp": "2026-03-02T10:30:45.123456"
}
```

---

### 4. Monitor Single Farm (POST)
**Endpoint:** `POST /api/monitor`

Monitor a single farm using request body.

**Request:**
```json
{
  "farmId": "13f9ef67-19b0-4e3d-bec5-6dd15247492c"
}
```

**Parameters:**
- `farmId` (required, string): The farm ID to monitor

**Response (200 OK):**
Same as GET /api/monitor/<farm_id>

**Error Response (400 Bad Request):**
```json
{
  "status": "error",
  "message": "Missing required field: farmId"
}
```

---

### 5. Get Configuration
**Endpoint:** `GET /api/config`

Get current API configuration (public information only).

**Response (200 OK):**
```json
{
  "status": "success",
  "config": {
    "old_api_endpoint": "https://prodgateway.nitara.co.in/cm/GetFarmMetaDataNew",
    "new_api_endpoint": "https://prodgateway.nitara.co.in/meta-data-api/farm-meta-data",
    "request_timeout": 30,
    "output_directory": "results"
  }
}
```

---

### 6. API Documentation
**Endpoint:** `GET /api/docs`

Get this API documentation in JSON format.

**Response (200 OK):**
```json
{
  "service": "Redis Monitor API",
  "version": "1.0.0",
  "endpoints": { ... }
}
```

---

## Usage Examples

### Using cURL

**Compare multiple farms:**
```bash
curl -X POST http://localhost:5000/api/compare \
  -H "Content-Type: application/json" \
  -d '{
    "farmIds": [
      "13f9ef67-19b0-4e3d-bec5-6dd15247492c",
      "farm-id-2"
    ],
    "generateReport": true
  }'
```

**Monitor single farm (GET):**
```bash
curl -X GET http://localhost:5000/api/monitor/13f9ef67-19b0-4e3d-bec5-6dd15247492c
```

**Monitor single farm (POST):**
```bash
curl -X POST http://localhost:5000/api/monitor \
  -H "Content-Type: application/json" \
  -d '{
    "farmId": "13f9ef67-19b0-4e3d-bec5-6dd15247492c"
  }'
```

**Check health:**
```bash
curl -X GET http://localhost:5000/health
```

### Using Python Requests

```python
import requests
import json

BASE_URL = "http://localhost:5000"

# Compare multiple farms
response = requests.post(
    f"{BASE_URL}/api/compare",
    json={
        "farmIds": [
            "13f9ef67-19b0-4e3d-bec5-6dd15247492c",
            "farm-id-2"
        ],
        "generateReport": True
    }
)

result = response.json()
print(json.dumps(result, indent=2))

# Check summary
print(f"Total farms: {result['summary']['total']}")
print(f"Identical: {result['summary']['identical']}")
print(f"Different: {result['summary']['different']}")
print(f"Errors: {result['summary']['errors']}")

# If reports were generated
if 'reports' in result:
    print(f"JSON Report: {result['reports']['json']}")
    print(f"HTML Report: {result['reports']['html']}")
```

### Using JavaScript/Fetch

```javascript
const BASE_URL = "http://localhost:5000";

async function compareMultipleFarms(farmIds) {
  try {
    const response = await fetch(`${BASE_URL}/api/compare`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        farmIds: farmIds,
        generateReport: true
      })
    });

    const data = await response.json();
    
    console.log('Comparison Results:');
    console.log(`Total: ${data.summary.total}`);
    console.log(`Identical: ${data.summary.identical}`);
    console.log(`Different: ${data.summary.different}`);
    console.log(`Errors: ${data.summary.errors}`);
    
    return data;
  } catch (error) {
    console.error('Error:', error);
  }
}

// Usage
compareMultipleFarms([
  "13f9ef67-19b0-4e3d-bec5-6dd15247492c",
  "farm-id-2"
]);
```

---

## Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request (missing/invalid parameters) |
| 404 | Endpoint not found |
| 405 | Method not allowed |
| 500 | Internal server error |

---

## Error Handling

All endpoints return a JSON response with a `status` field:
- `"status": "success"` - Operation succeeded
- `"status": "error"` - Operation failed

### Example Error Response:
```json
{
  "status": "error",
  "message": "Descriptive error message"
}
```

---

## Performance Considerations

1. **Batch Processing**: The `/api/compare` endpoint processes farms sequentially, one at a time
2. **Timeouts**: Each API request has a `REQUEST_TIMEOUT` configured (default: 30 seconds)
3. **Report Generation**: Generating JSON and HTML reports is optional to reduce response time
4. **Farm IDs Limit**: No hard limit on the number of farms, but processing time scales linearly

---

## Deployment

### Production Deployment
For production, use a production WSGI server instead of Flask's development server:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker Deployment
See a Dockerfile would be added here for containerization.

### Environment Variables
Configure via `.env` file:
```
JWT_SECRET=your-secret-key
OLD_API_ENDPOINT=https://api.example.com/old
NEW_API_ENDPOINT=https://api.example.com/new
REQUEST_TIMEOUT=30
OUTPUT_DIR=results
```

---

## Monitoring & Logging

Monitor the following:
- API response times
- Error rates
- Report generation success
- API endpoint availability

---

## Support

For issues or questions:
1. Check `/api/docs` for endpoint documentation
2. Review error messages in the response
3. Check server logs for detailed errors
4. Verify `.env` configuration is correct
