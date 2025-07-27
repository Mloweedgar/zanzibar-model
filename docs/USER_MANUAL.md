# BEST-Z Nitrogen Model - User Manual

## What This Tool Does

The BEST-Z Nitrogen Model calculates how much nitrogen pollution comes from household sanitation systems in Zanzibar. It helps you:

- **See which areas have the highest nitrogen pollution** from poor sanitation
- **Compare different scenarios** (current conditions vs. improved sanitation vs. population growth)
- **Identify priority areas** for sanitation improvements
- **Visualize results on interactive maps**

## Getting Started

### Access the Tool
**Open your web browser and go to:** http://51.20.7.134/

No installation required - the tool runs in your browser!

### Choose Your Data
When you open the tool, you can:
- **Use built-in Zanzibar data** (ready to use immediately), OR
- **Upload your own data files** (for other regions or updated data)

## How the Model Works

### The Calculation
The model calculates nitrogen load using this formula:
```
Nitrogen Load = Population × Daily Protein × 365 days × 0.16 × (1 - Removal Efficiency)
```

**Where:**
- **Population**: Number of people using each toilet type
- **Daily Protein**: 64 grams per person per day (fixed)
- **0.16**: Conversion factor from protein to nitrogen (fixed)
- **Removal Efficiency**: How much nitrogen the toilet system removes (0% to 100%)

### Toilet Types and Removal Rates
| Toilet Type | Nitrogen Removal |
|-------------|------------------|
| Flush to sewer | 0% (baseline) |
| Flush to septic tank | 0% (baseline) |
| Flush to pit | 0% (baseline) |
| VIP latrine | 0% (baseline) |
| Pit latrine (various types) | 0% (baseline) |
| No facility/open defecation | 0% (baseline) |

**Note:** The model uses 0% removal efficiency as baseline, but you can test "improved sanitation" scenarios with higher removal rates.

## Using Your Own Data

### Required Files (3 files total)

#### 1. Census Data (CSV file)
**Must include these columns:**
- `ward_name`: Name of the area
- `TOILET`: Toilet type (number 1-11)
- `SEX`: Gender (1=Male, 2=Female)  
- `AGE`: Age in years
- `reg_name`: Region name
- `H_DISTRICT_NAME`: District name
- `H_COUNCIL_NAME`: Council name
- `H_CONSTITUENCY_NAME`: Constituency name
- `H_DIVISION_NAME`: Division name
- `H_INSTITUTION_TYPE`: Use single space ' ' for households

#### 2. Sanitation Efficiency Data (CSV file)
**Must include these columns:**
- `toilet_type_id`: Toilet type number (1-11)
- `toilet_type`: Description of toilet type
- `system_category`: Category (septic_tank_sewer, septic_tank, pit_latrine, open_defecation)
- `nitrogen_removal_efficiency`: Removal rate (0.0 to 1.0)

#### 3. Ward Boundaries (GeoJSON file)
**Must include:**
- `ward_name`: Area name (matching census data)
- Geographic boundaries for mapping

### Upload Process
1. **Select "Upload Custom Data"** in the dashboard sidebar
2. **Upload all 3 files** using the file upload buttons
3. **Wait for validation** - the system will check your data
4. **Run the model** once validation passes

## Understanding Your Results

### Main Outputs

#### 1. Interactive Map
- **Red areas**: High nitrogen pollution
- **Yellow areas**: Medium nitrogen pollution  
- **Light areas**: Low nitrogen pollution
- **Click on areas** to see detailed numbers

#### 2. Data Tables
- **Ward totals**: Nitrogen load by administrative area
- **Population breakdown**: People by toilet type
- **Scenario comparisons**: Side-by-side results

#### 3. Downloadable Files
- **CSV files**: Raw data for further analysis
- **GeoJSON files**: Geographic data for GIS software
- **PNG maps**: Static images for reports

### Key Numbers to Look For

- **kg/year**: Total nitrogen load per area per year
- **kg/person/year**: Nitrogen load per person (for comparing areas of different sizes)
- **Hotspots**: Areas with highest total loads (priority for interventions)

## Scenarios You Can Test

### 1. Baseline 2022
- Current population and sanitation conditions
- Uses actual census data

### 2. Improved Removal
- Same population, but with 80% nitrogen removal efficiency
- Shows impact of upgrading sanitation systems

### 3. Population Growth 2030
- 20% population increase with current sanitation
- Shows future pollution if no improvements made

### 4. Custom Scenarios
- Upload your own data with different parameters
- Test specific improvement plans

## Troubleshooting

### File Upload Issues
**Problem**: "File validation failed"
**Solutions:**
- Check that column names match exactly (case-sensitive)
- Ensure ward names are identical across all files
- Use UTF-8 encoding for CSV files
- Remove empty rows and columns

**Problem**: "No data displayed"
**Solutions:**
- Verify toilet type numbers (1-11) in census data
- Check that efficiency data covers all toilet types
- Ensure ward boundaries contain all census areas

### Performance Issues
**Problem**: Dashboard runs slowly
**Solutions:**
- Use smaller datasets for testing
- Close other browser tabs
- Refresh the page if it becomes unresponsive
- Try again later if the server is busy

### Map Display Issues
**Problem**: Map doesn't show or looks wrong
**Solutions:**
- Check that GeoJSON file is valid
- Ensure coordinate system is WGS84 (EPSG:4326)
- Verify ward names match between files

## Getting Help

### Download Template Files
1. Go to http://51.20.7.134/
2. In the sidebar, select "Upload Custom Data"
3. Expand "Required Data Formats"
4. Click "Download Template Files"

### Common Questions

**Q: Can I use data from other countries?**
A: Yes, but you'll need census data in the required format and geographic boundaries.

**Q: How accurate are the results?**
A: Results are estimates based on input data quality. Use for relative comparisons between areas.

**Q: Can I change the protein consumption rate?**
A: Currently fixed at 64g/day. This is built into the model.

**Q: What if I don't have all the administrative levels?**
A: You can use the same name for multiple levels (e.g., use ward name for both district and council).

**Q: Is my data secure?**
A: Data uploaded to the tool is processed temporarily and not permanently stored on the server.

**Q: Can I save my results?**
A: Yes, you can download results as CSV files, GeoJSON files, or PNG maps directly from the tool.

---

**Need more help?** The tool includes built-in help sections and template downloads at http://51.20.7.134/