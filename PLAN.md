## Plan: Redis-Monitor Farm Metadata Comparison Tool

**TL;DR:** Build a modular Python monitoring script that compares farm metadata between old database and new Redis APIs. The tool will fetch data for multiple farms, generate JWT tokens from a config file, compare responses using DeepDiff, and output results to console and JSON. It will consist of separate modules for token generation, API communication, comparison logic, and configuration management.

**Steps**

1. **Set up project structure and dependencies**
   - Create `requirements.txt` with dependencies: `pyjwt`, `requests`, `deepdiff`, `python-dotenv`
   - Create modular directory: `src/` folder with separate modules
   - Create `.env.example` file documenting required configuration variables

2. **Create configuration module** (`src/config.py`)
   - Load environment variables from `.env` file using python-dotenv
   - Define JWT secret, API endpoints, farm IDs list
   - Include default token payload values (userId, deviceId, role, organization, etc.)

3. **Create authentication module** (`src/auth.py`)
   - Implement `generate_token(farm_id)` function using PyJWT library
   - Use HS256 algorithm with secret from config
   - Handle 1-year token expiration from config
   - Return JWT token string

4. **Create API client module** (`src/api_client.py`)
   - Implement `fetch_old_api(farm_id, token)` calling `https://prodgateway.nitara.co.in/cm/GetFarmMetaDataNew`
   - Implement `fetch_new_api(farm_id, token)` calling `https://prodgateway.nitara.co.in/meta-data-api/farm-meta-data`
   - Add error handling and request timeout management
   - Return parsed JSON responses

5. **Create comparison module** (`src/comparison.py`)
   - Implement `compare_responses(old_response, new_response)` using DeepDiff
   - Return structured difference object with summary (identical, values_changed, items_added, items_removed, etc.)

6. **Create output/reporting module** (`src/reporter.py`)
   - Implement formatted console output (showing API endpoints, farm ID, comparison summary)
   - Implement JSON export of all results with timestamps
   - Generate report structure: metadata, individual farm comparisons, summary statistics

7. **Create main orchestration script** (`redis_monitor.py` or `main.py`)
   - Load configuration and farm IDs list
   - Loop through each farm ID from config
   - Call token generation → API fetch (both) → comparison → report
   - Aggregate results
   - Write combined JSON report to `results/` directory
   - Print summary to console with differences highlighted

8. **Create `.gitignore`**
   - Ignore `.env`, `__pycache__/`, `.pytest_cache/`, `results/` directory, `*.pyc`

9. **Create README.md**
   - Document setup (pip install -r requirements.txt, create .env)
   - Document configuration variables needed
   - Explain how to run the script
   - Show example output format

**Verification**
- Run script with test farm ID from TASK.md: `python redis_monitor.py`
- Verify both API calls execute successfully
- Check that comparison output in console shows clear diff summary
- Verify `results/` directory contains JSON file with full details
- Test with `.env` file present and missing (should fail appropriately)

**Decisions**
- **Modular approach:** Separate `auth.py`, `api_client.py`, `comparison.py`, `reporter.py` for maintainability
- **Configuration:** Use `.env` file (via python-dotenv) for secrets and farm IDs list for batch processing
- **Output:** Both console summary and JSON detailed report to enable quick feedback and full audit trail
- **Batch support:** Farm IDs loaded from `.env` or config file, enabling single command to monitor multiple farms
