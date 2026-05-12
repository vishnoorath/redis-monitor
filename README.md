# Redis Monitor - Farm Metadata Comparison & Replication Tool

A comprehensive monitoring suite that compares farm metadata responses between **old database-backed API** and **new Redis-based API**, while also monitoring **SQL Server replication** consistency across multiple servers.

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

## Usage

### Run the Web UI & API Server
```bash
python app.py
```
The application will be available at:
- **Web Dashboard**: [http://localhost:5000/](http://localhost:5000/)
- **Settings**: [http://localhost:5000/settings](http://localhost:5000/settings)
- **API Documentation**: [http://localhost:5000/apidocs/](http://localhost:5000/apidocs/)

### Run the CLI Monitor
```bash
python redis_monitor.py
```

## Web UI Pages

### 1. Dashboard (`/`)
- Monitor recently updated farms from the SQL database
- Manually enter farm IDs for ad-hoc comparison
- Quick links to Redis and SQL status pages

### 2. SQL Replication Status (`/sql-status`)
- Visual comparison of table row counts across all configured SQL servers
- Highlights discrepancies between primary and secondary servers
- Automatic refresh support

### 3. Settings (`/settings`)
- **Refresh Frequency**: Configure how often the UI polls for updates
- **Notification Emails**: Set up email addresses for monitoring alerts
- **Database Servers**: Manage the list of SQL Server instances to monitor
- **Ignore Tables**: Specify tables to exclude from replication monitoring

## API Endpoints

### Monitoring & Comparison
- `GET /health`: System health check
- `POST /api/compare`: Compare multiple farms by ID
- `GET /api/monitor/{farm_id}`: Monitor a single farm
- `GET /api/replication/table-counts`: Get detailed replication status

### Configuration
- `GET /api/settings`: Retrieve all application settings
- `POST /api/settings`: Update a specific setting
- `DELETE /api/settings?key=X`: Delete a setting
- `GET /api/config`: Get static API configuration

## Configuration Storage (SQLite)

The application uses an `ApplicationSettings` table in `settings.db` to store configurations:
- **SERVERS**: JSON array of server configurations (IP, DB, credentials, isPrimary)
- **REFRESH_FREQUENCY**: Polling interval for UI updates
- **NOTIFIED_EMAILS**: Comma-separated list of alert recipients
- **IGNORE_TABLES_FOR_MONITORING**: Tables excluded from row count comparisons

## Project Structure

```
redis-monitor/
├── app.py                   # Flask Web Server & API
├── redis_monitor.py          # CLI Monitor script
├── settings.db              # SQLite settings database
├── requirements.txt          # Python dependencies
├── .env                     # Initial configuration
├── src/
│   ├── settings_db.py       # SQLite settings management
│   ├── sql.py               # SQL Server connectivity
│   ├── replication_monitor.py # Replication monitoring logic
│   ├── api_client.py        # Redis/Old API client
│   ├── auth.py              # JWT token generation
│   ├── comparison.py        # JSON comparison logic
│   ├── html_reporter.py     # HTML report generation
│   └── config.py            # Static configuration
├── templates/               # Flask HTML templates
├── static/                  # CSS/JS assets
└── sql/                     # Stored procedure definitions
```

## Dependencies

- **Flask / Flasgger**: Web framework and Swagger documentation
- **pyodbc**: SQL Server connectivity
- **PyJWT**: JWT token handling
- **DeepDiff**: Advanced JSON comparison
- **SQLite3**: Local configuration storage

## License

Internal tool for farm metadata validation and replication monitoring.
