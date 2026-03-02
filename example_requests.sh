#!/bin/bash
# Example cURL commands for Redis Monitor API

# Configuration
API_BASE_URL="http://localhost:5000"

echo "========================================"
echo "Redis Monitor API - cURL Examples"
echo "========================================"
echo ""

# Example 1: Health Check
echo "1. Health Check"
echo "Command:"
echo "curl -X GET $API_BASE_URL/health"
echo ""
echo "Response:"
curl -X GET "$API_BASE_URL/health" | jq '.'
echo ""
echo ""

# Example 2: Get Configuration
echo "2. Get Configuration"
echo "Command:"
echo "curl -X GET $API_BASE_URL/api/config"
echo ""
echo "Response:"
curl -X GET "$API_BASE_URL/api/config" | jq '.'
echo ""
echo ""

# Example 3: Get API Documentation
echo "3. Get API Documentation"
echo "Command:"
echo "curl -X GET $API_BASE_URL/api/docs"
echo ""
echo "Response (truncated):"
curl -X GET "$API_BASE_URL/api/docs" | jq '.' | head -50
echo ""
echo ""

# Example 4: Monitor Single Farm (GET)
echo "4. Monitor Single Farm (GET)"
FARM_ID="13f9ef67-19b0-4e3d-bec5-6dd15247492c"
echo "Command:"
echo "curl -X GET $API_BASE_URL/api/monitor/$FARM_ID"
echo ""
echo "Response:"
curl -X GET "$API_BASE_URL/api/monitor/$FARM_ID" | jq '.'
echo ""
echo ""

# Example 5: Monitor Single Farm (POST)
echo "5. Monitor Single Farm (POST)"
echo "Command:"
echo "curl -X POST $API_BASE_URL/api/monitor \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"farmId\": \"$FARM_ID\"}'"
echo ""
echo "Response:"
curl -X POST "$API_BASE_URL/api/monitor" \
  -H "Content-Type: application/json" \
  -d "{\"farmId\": \"$FARM_ID\"}" | jq '.'
echo ""
echo ""

# Example 6: Compare Single Farm
echo "6. Compare Single Farm (via /api/compare)"
echo "Command:"
echo "curl -X POST $API_BASE_URL/api/compare \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"farmIds\": [\"$FARM_ID\"], \"generateReport\": false}'"
echo ""
echo "Response:"
curl -X POST "$API_BASE_URL/api/compare" \
  -H "Content-Type: application/json" \
  -d "{\"farmIds\": [\"$FARM_ID\"], \"generateReport\": false}" | jq '.'
echo ""
echo ""

# Example 7: Compare Multiple Farms
echo "7. Compare Multiple Farms"
echo "Command:"
echo "curl -X POST $API_BASE_URL/api/compare \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"farmIds\": [\"farm-id-1\", \"farm-id-2\", \"farm-id-3\"], \"generateReport\": true}'"
echo ""
echo "Response (summary only):"
curl -X POST "$API_BASE_URL/api/compare" \
  -H "Content-Type: application/json" \
  -d "{\"farmIds\": [\"farm-id-1\", \"farm-id-2\", \"farm-id-3\"], \"generateReport\": true}" | jq '.summary'
echo ""
echo ""

# Example 8: Error - Missing Field
echo "8. Error Handling - Missing Required Field"
echo "Command:"
echo "curl -X POST $API_BASE_URL/api/compare \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{}'"
echo ""
echo "Response:"
curl -X POST "$API_BASE_URL/api/compare" \
  -H "Content-Type: application/json" \
  -d "{}" | jq '.'
echo ""
echo ""

# Example 9: Error - Invalid Farm IDs
echo "9. Error Handling - Empty Farm IDs Array"
echo "Command:"
echo "curl -X POST $API_BASE_URL/api/compare \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"farmIds\": []}'"
echo ""
echo "Response:"
curl -X POST "$API_BASE_URL/api/compare" \
  -H "Content-Type: application/json" \
  -d "{\"farmIds\": []}" | jq '.'
echo ""
echo ""

# Example 10: 404 Not Found
echo "10. Error Handling - 404 Not Found"
echo "Command:"
echo "curl -X GET $API_BASE_URL/api/nonexistent"
echo ""
echo "Response:"
curl -X GET "$API_BASE_URL/api/nonexistent" | jq '.'
echo ""
echo ""

echo "========================================"
echo "Examples completed!"
echo "========================================"
