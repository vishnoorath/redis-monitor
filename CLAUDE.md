# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Redis Monitor is a farm metadata comparison and SQL replication monitoring tool. It compares responses between an old database-backed API and a new Redis-based API, and monitors SQL Server replication consistency across multiple servers.

## Features

- **Web Dashboard**: Interactive UI for monitoring and manual comparison
- **Dual API Comparison**: Fetch and compare farm metadata from old and new APIs simultaneously
- **SQL Replication Monitor**: Monitor table row counts across primary and secondary SQL Server instances
- **Dynamic Configuration**: Manage all settings (servers, frequencies, notifications) via a built-in Settings UI
- **SQLite Settings Storage**: Persistent application configuration stored in a local SQLite database
- **REST API**: Full-featured API for health checks, comparisons, and settings management
- **JWT Authentication**: Automatic token generation for secure API access
- **Interactive Reports**: Beautifully formatted HTML reports with color-coded differences
- **OpenAPI/Swagger**: Built-in API documentation and interactive testing UI

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
# Copy example configuration (for initial setup)
cp .env.example .env

# Edit .env with your basic settings if needed
# Most configurations can now be managed via the Web UI
```

## Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the Flask web server (default: localhost:5000)
python app.py

# Run the CLI monitor (uses FARM_IDS from .env)
python redis_monitor.py
```

### Docker
```bash
# Build and run with docker-compose
docker-compose up --build

# Run container in background
docker-compose up -d
```

### Configuration
Settings are stored in `settings.db` (SQLite) and can be managed via:
- Web UI at `/settings`
- REST API at `/api/settings`

## Architecture

### Entry Points
- **app.py**: Flask web server with REST API and web UI (port 5000)
- **redis_monitor.py**: CLI script for batch farm comparison

### Core Modules (src/)
- **config.py**: Environment configuration via .env (API endpoints, JWT settings)
- **auth.py**: JWT token generation for API authentication
- **api_client.py**: Fetches farm metadata from both old and new APIs
- **comparison.py**: DeepDiff-based JSON comparison of API responses
- **settings_db.py**: SQLite-based settings persistence
- **replication_monitor.py**: SQL Server replication monitoring (row count comparison)
- **html_reporter.py / reporter.py**: Report generation

### Dual-Monitor Design
1. **Farm Metadata Comparison**: Compares farm data from:
   - Old API: `OLD_API_ENDPOINT` (DB-backed)
   - New API: `NEW_API_ENDPOINT` (Redis-backed)

2. **SQL Replication Monitor**: Compares table row counts across multiple SQL Server instances, with one primary server (marked `isPrimary: true`).

### Web UI Routes
| Route | Purpose |
|-------|---------|
| `/` | Dashboard with farm comparison form, recently updated farms, Redis/SQL status links |
| `/settings` | Configuration management (refresh frequency, emails, servers, ignore tables) |
| `/sql-status` | Replication status with visual row count comparison |
| `/redis-status` | Redis Cache Status page |
| `/apidocs/` | Swagger API documentation |

### Key API Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | System health check |
| `/api/compare` | POST | Compare multiple farms by ID |
| `/api/monitor/{farm_id}` | GET | Monitor single farm |
| `/api/monitor` | POST | Monitor single farm (POST variant) |
| `/api/replication/table-counts` | GET | Get replication status |
| `/api/settings` | GET/POST/DELETE | Manage settings |
| `/api/config` | GET | Get static API configuration |

## Configuration

### Environment Variables (.env)
- `JWT_SECRET`: Secret key for token generation
- `OLD_API_ENDPOINT` / `NEW_API_ENDPOINT`: API URLs to compare
- `FARM_IDS`: Comma-separated list for CLI monitoring
- SQL Server credentials for replication monitoring

### Settings Database (settings.db)
Stored as `key-value` pairs with type hints (STRING, JSON, INT, BOOL):
- `SERVERS`: JSON array of SQL Server configurations
- `IGNORE_TABLES_FOR_MONITORING`: Tables excluded from row count checks
- `REFRESH_FREQUENCY`: UI polling interval (seconds)
- `NOTIFIED_EMAILS`: Alert recipients

## Database Schema

Settings table (`ApplicationSettings`):
```sql
CREATE TABLE ApplicationSettings (
    key VARCHAR PRIMARY KEY,
    value NVARCHAR,
    valueType VARCHAR
)
```

SQL Server connection uses ODBC Driver 18 with `TrustServerCertificate=yes`.

## Dependencies

- **Flask / Flasgger**: Web framework and Swagger documentation
- **pyodbc**: SQL Server connectivity
- **PyJWT**: JWT token handling
- **DeepDiff**: Advanced JSON comparison
- **SQLite3**: Local configuration storage