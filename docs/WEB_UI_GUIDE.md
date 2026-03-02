# Web UI Guide - Redis Monitor

## Overview

The Redis Monitor Flask app includes a beautiful web user interface that allows you to compare farm metadata without using the API directly. The entire report is rendered inline in the browser using Jinja2 templates.

---

## Quick Start

### 1. Start the Server
```bash
python app.py
```

### 2. Open in Browser
Navigate to: `http://localhost:5000`

You'll see the dashboard with a form to enter farm IDs.

---

## Features

### Dashboard
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Stats Overview**: Shows 4 key metrics (endpoints, farms, formats, coverage)
- **Input Form**: Easy-to-use textarea for entering farm IDs
- **Quick Reference**: Lists all 6 API endpoints
- **Process Flow**: Explains how the comparison works

### Comparison Form
- **Farm ID Input**
  - Enter one farm ID per line
  - Or use comma-separated values
  - Paste multiple IDs at once
- **Generate Reports Checkbox**
  - Optional: Generate JSON and HTML file reports
  - Uncheck to skip report generation for faster results
- **Clear Button**: Reset form to start over

### Report Display
- **Summary Statistics**
  - Color-coded cards showing results
  - Green for identical, orange for different, red for errors
- **Status Messages**
  - Success message if all synchronized
  - Warning message if differences found
  - Error message if API requests failed
- **Detailed Results**
  - Farm ID identification
  - API response status (success/failed)
  - Comparison results (identical/different/error)
  - Color-coded differences
- **Expandable Sections**
  - Click to show detailed differences
  - View raw JSON API responses
  - Copy-friendly formatting

### Color Coding
- 🟢 **Green** - Identical responses, successes
- 🟡 **Orange** - Different values, warnings
- 🔴 **Red** - Failures, missing items
- 🟦 **Gray** - Neutral information

---

## How to Use

### Step 1: Enter Farm IDs
In the dashboard form, enter farm IDs to compare:

**Option A: One per line**
```
13f9ef67-19b0-4e3d-bec5-6dd15247492c
farm-id-2
farm-id-3
```

**Option B: Comma-separated**
```
13f9ef67-19b0-4e3d-bec5-6dd15247492c, farm-id-2, farm-id-3
```

**Option C: Mixed**
```
13f9ef67-19b0-4e3d-bec5-6dd15247492c,farm-id-2
farm-id-3
```

### Step 2: Choose Report Option
- ✅ **Check "Generate Reports"** if you want JSON and HTML file exports
- ⬜ **Uncheck** for faster results without file generation

### Step 3: Click "Compare Farms"
The form validates your input and starts processing.

### Step 4: Review Results
The page displays:
1. **Summary cards** with statistics
2. **Status message** indicating overall result
3. **Detailed comparison** for each farm
4. **Expandable sections** for detailed diffs and raw responses

---

## Report Sections

### Summary Cards (Top of Report)
Shows 4 key metrics:
- Farms with identical responses ✓
- Farms with different responses ✗
- Farms with errors ⚠
- Total farms processed

### Status Message
Provides quick overview:
- ✓ **Success**: "All farm metadata is synchronized!"
- ⚠ **Warning**: "N farm(s) have differences..."
- ❌ **Error**: "N farm(s) failed API requests..."

### Farm Details
For each farm, shows:
1. **Farm ID** - Identification
2. **API Status** - Success/failure for each endpoint
3. **Comparison Result** - Identical or different
4. **Expandable Differences** - Click to see what changed
5. **Expandable Raw Data** - View complete API responses

### Detailed Differences
When responses differ, shows:
- **Values Changed**: What values differ and new vs old
- **Items Added**: New items in the new API
- **Items Removed**: Items missing in the new API
- **Type Changes**: Data types that changed

---

## Template Files

The web UI uses Jinja2 templates from the `templates/` directory:

### base.html
- Navigation bar
- Footer
- Common styling
- Shared HTML structure

### index.html
- Dashboard page
- Input form
- Quick reference
- Getting started guide

### report.html
- Comparison results display
- Summary statistics
- Farm-by-farm comparison details
- Expandable sections for details

---

## Browser Support

The web UI works on:
- ✅ Chrome/Chromium (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Edge (latest)
- ✅ Mobile browsers (responsive design)

---

## Tips & Tricks

### Large Numbers of Farms
- Enter up to 100s of farm IDs
- Processing is sequential (one at a time)
- Uncheck "Generate Reports" for faster results
- Use multiple comparison runs instead of one massive run

### Copy-Friendly Data
- Click on expandable sections to view raw JSON
- All diffs are formatted for easy reading
- Raw responses are pretty-printed with indentation

### Mobile Usage
- Dashboard is fully responsive
- Use landscape mode for better form input
- Results expand nicely on mobile devices
- Touch-friendly buttons and inputs

### Share Results
- Screenshots work well for sharing status
- Raw JSON can be exported via "Generate Reports"
- Each report has a unique timestamp for identification

---

## Common Workflows

### Workflow 1: Quick Check
1. Enter 1-2 farm IDs
2. Uncheck "Generate Reports"
3. Click "Compare Farms"
4. Review results in browser
5. Click "Compare Another Farm" to start over

### Workflow 2: Detailed Analysis
1. Enter 5-10 farm IDs
2. Check "Generate Reports"
3. Click "Compare Farms"
4. Review results in browser
5. Check `results/` folder for JSON and HTML files
6. Use JSON for programmatic processing
7. Share HTML report with team

### Workflow 3: Batch Monitoring
1. Enter all farm IDs at once
2. Check "Generate Reports"
3. Click "Compare Farms"
4. Save & share generated reports
5. Use for documentation/audit trail

---

## Report Export

When you check "Generate Reports", two files are created:

### JSON Report
- **Location**: `results/comparison_report_{timestamp}.json`
- **Use**: Machine-readable format for processing
- **Contains**: All raw data and comparisons
- **Accessible**: Via command line or file explorer

### HTML Report (Same as Displayed)
- **Location**: `results/comparison_report_{timestamp}.html`
- **Use**: Standalone report file
- **Contains**: All styling and formatting
- **Shareable**: Email the file to others

---

## Troubleshooting

### Form Not Submitting
- Ensure you've entered at least one farm ID
- Check that farm IDs are valid strings
- Try clearing browser cache
- Reload the page

### Slow Loading
- Large numbers of farms take longer to process
- Each farm requires 2 API calls
- Network latency affects speed
- Check if target APIs are responding slowly

### Results Not Displaying
- Check browser console for errors
- Verify server is running (`python app.py`)
- Check network tab for failed requests
- Try a single farm ID first

### Files Not Generated
- Check `results/` folder exists
- Verify write permissions on directory
- Try without "Generate Reports" first
- Check server logs for errors

---

## API Integration

The web UI uses the same backend as the REST API:
- Same comparison logic
- Same JWT token generation
- Same DeepDiff comparison
- Same error handling

You can use the web UI and REST API simultaneously:
```bash
# Terminal 1: Run web UI
python app.py

# Terminal 2: Make API calls
curl http://localhost:5000/api/compare ...
```

---

## Dashboard Stats

The dashboard shows 4 key metrics:

| Metric | Meaning |
|--------|---------|
| 6 | Number of REST API endpoints available |
| ∞ | Unlimited farms can be monitored |
| 2 | Report formats (JSON + HTML) |
| 100% | API coverage for monitoring |

---

## Next Steps

### Use Web UI for
- Quick spot checks
- Visual comparison review
- Team communication
- Documentation

### Use REST API for
- Automation & scheduling
- Integration with other systems
- Batch processing
- Programmatic access

### Combine Both
- Use web UI for exploration
- Export reports (JSON)
- Use API for automation
- Archive reports from files

---

## Support

### Getting Help
1. Check dashboard "How It Works" section
2. Visit `/api/docs` for API reference
3. Look at example farm IDs in UI
4. Check browser console for errors

### Common Questions

**Q: How long does comparison take?**
A: 1-5 seconds per farm, plus API response times

**Q: Can I compare 1000 farms?**
A: Yes, but will take proportional time. Consider batch runs.

**Q: Where are generated reports saved?**
A: In the `results/` directory

**Q: Can I delete old reports?**
A: Yes, manually delete from `results/` folder

**Q: Can multiple people use it at once?**
A: Yes, but each request is processed independently

---

## Features Comparison

| Feature | Web UI | REST API |
|---------|--------|----------|
| Visual Dashboard | ✅ | ❌ |
| Form Input | ✅ | ❌ |
| Inline Results | ✅ | ✅ |
| JSON Reports | ✅ | ✅ |
| HTML Reports | ✅ | ✅ |
| Programmatic Access | ❌ | ✅ |
| Automation | ❌ | ✅ |
| Scheduling | ❌ | ✅ |

---

## Best Practices

1. **Start with single farm** - Verify setup works
2. **Review results carefully** - Check for unexpected differences
3. **Export reports when needed** - Don't rely only on browser display
4. **Archive important results** - Keep reports for audit trail
5. **Use API for automation** - Schedule periodic monitoring
6. **Monitor both simultaneously** - UI for humans, API for machines

---

## Summary

The Redis Monitor web UI provides an intuitive, visual interface for comparing farm metadata. It combines the power of the Flask backend with a beautiful, responsive frontend that requires no technical knowledge to use.

**Key Points:**
- ✅ No API calls needed - just fill out a form
- ✅ Beautiful report rendering in browser
- ✅ Color-coded, easy-to-read results
- ✅ Optional file-based reports
- ✅ Works on all devices
- ✅ Perfect for both technical and non-technical users
