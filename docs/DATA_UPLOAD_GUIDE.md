# Data Upload Guide for BEST-Z Nitrogen Model Dashboard

This guide explains how to use the file upload feature to run the BEST-Z Nitrogen Model with your own custom data.

## 📁 Required Files

The dashboard requires three data files to run the nitrogen load model:

### 1. Census Data (CSV)
**File:** `census_data.csv`

Contains household-level demographic and sanitation data.

**Required Columns:**
- `ward_name`: Name of the administrative ward
- `TOILET`: Toilet type ID (integer 1-11, see toilet types below)
- `SEX`: Gender (1=Male, 2=Female)
- `AGE`: Age in years (integer)
- `H_INSTITUTION_TYPE`: Institution type (use single space ' ' for households)
- `reg_name`: Region name
- `H_DISTRICT_NAME`: District name
- `H_COUNCIL_NAME`: Council name
- `H_CONSTITUENCY_NAME`: Constituency name
- `H_DIVISION_NAME`: Division name

**Example:**
```csv
reg_name,H_DISTRICT_NAME,H_COUNCIL_NAME,H_CONSTITUENCY_NAME,H_DIVISION_NAME,ward_name,H_INSTITUTION_TYPE,TOILET,SEX,AGE
Central Region,Central District,Central Council,Central Constituency,Central Division,Ward A, ,1,1,25
Central Region,Central District,Central Council,Central Constituency,Central Division,Ward A, ,2,2,30
```

### 2. Sanitation Efficiency Data (CSV)
**File:** `sanitation_efficiency.csv`

Defines nitrogen removal efficiency for different toilet types.

**Required Columns:**
- `toilet_type_id`: Toilet type ID (string, must match TOILET values in census data)
- `toilet_type`: Human-readable toilet type name
- `system_category`: System category (septic_tank_sewer, septic_tank, pit_latrine, open_defecation)
- `nitrogen_removal_efficiency`: Nitrogen removal efficiency (decimal 0.0-1.0)

**Standard Toilet Types:**
1. Flush/pour flush to piped sewer system
2. Flush/pour flush to septic tank
3. Flush/pour flush to covered pit
4. Flush/pour flush to somewhere else (no containment)
5. Ventilated improved pit (VIP) latrine
6. Pit latrine with washable slab and lid
7. Pit latrine with washable slab without lid
8. Pit latrine with not-washable/soil slab
9. Pit latrine without slab/open pit
10. Bucket
11. No facility/bush/field/beach (open defecation)

**Example:**
```csv
toilet_type_id,toilet_type,system_category,nitrogen_removal_efficiency
1,Flush to sewer,septic_tank_sewer,0.0
2,Flush to septic tank,septic_tank,0.0
3,Flush to pit,septic_tank,0.0
```

### 3. Ward Boundaries (GeoJSON)
**File:** `ward_boundaries.geojson`

Contains geographic boundaries for administrative wards.

**Required Properties:**
- `ward_name`: Ward name (must match ward_name in census data)
- `geometry`: Polygon or MultiPolygon geometry

**Example:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "ward_name": "Ward A"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
      }
    }
  ]
}
```

## 🚀 How to Upload Data

1. **Open the Dashboard**
   - Navigate to the BEST-Z Dashboard in your browser
   - Look for the sidebar on the left

2. **Select Upload Mode**
   - In the "📁 Data Source" section, select "Upload Custom Data"

3. **Upload Files**
   - Click "Census Data (CSV)" and select your census file
   - Click "Sanitation Efficiency Data (CSV)" and select your efficiency file
   - Click "Ward Boundaries (GeoJSON)" and select your boundaries file

4. **Validation**
   - The dashboard will automatically validate your files
   - Green checkmarks indicate successful validation
   - Red error messages will show any issues that need fixing

5. **Run Analysis**
   - Once all files are validated, the dashboard will load your data
   - Use the scenario parameters to explore different nitrogen load scenarios

## 📥 Download Template Files

If you're unsure about the file format, you can download template files:

1. In the sidebar, expand "📋 Required Data Formats"
2. Click "📥 Download Template Files"
3. Download the three template files as examples
4. Modify these templates with your own data

## ✅ Data Validation

The dashboard performs automatic validation:

### Census Data Validation
- Checks for required columns
- Ensures TOILET values are valid (1-11)
- Verifies ward_name is present

### Sanitation Data Validation
- Checks for required columns
- Ensures toilet_type_id matches census TOILET values
- Validates efficiency values are between 0.0 and 1.0

### GeoJSON Validation
- Checks for geometry column
- Ensures ward_name property exists
- Validates GeoJSON structure

## 🔧 Troubleshooting

### Common Issues

**"Missing required columns" error:**
- Check that your CSV files have exactly the column names listed above
- Column names are case-sensitive

**"Ward name mismatch" error:**
- Ensure ward_name values in census data exactly match those in GeoJSON
- Check for extra spaces or different capitalization

**"Invalid toilet type" error:**
- TOILET values in census data must be integers 1-11
- Ensure toilet_type_id in sanitation data matches these values

**File upload fails:**
- Check file size (maximum 200MB per file)
- Ensure files are in correct format (CSV or GeoJSON)
- Try refreshing the page and uploading again

### File Size Limits

- Maximum file size: 200MB per file
- For large datasets, consider:
  - Compressing CSV files
  - Simplifying GeoJSON geometries
  - Splitting data into smaller regions

## 📊 Data Requirements

### Minimum Data Requirements
- At least 1 ward with population data
- At least 1 toilet type with efficiency data
- Geographic boundaries for all wards in census data

### Recommended Data Quality
- Complete demographic data (no missing ages/genders)
- Accurate toilet type classifications
- High-quality geographic boundaries
- Representative population sample

## 🌍 Coordinate Systems

**GeoJSON files should use:**
- Coordinate Reference System: WGS84 (EPSG:4326)
- Longitude/Latitude coordinates
- Valid polygon geometries

The dashboard will automatically handle coordinate transformations if needed.

## 💡 Tips for Best Results

1. **Data Consistency**
   - Use consistent ward naming across all files
   - Ensure toilet type IDs are standardized
   - Validate data quality before upload

2. **Geographic Accuracy**
   - Use high-quality boundary data
   - Ensure boundaries don't overlap inappropriately
   - Include all wards that appear in census data

3. **Population Representation**
   - Include representative sample of population
   - Ensure all age groups and genders are represented
   - Include variety of toilet types if present

4. **Testing**
   - Start with a small subset of data to test the process
   - Use template files to understand the format
   - Validate results against known expectations

## 📞 Support

If you encounter issues with data upload:

1. Check this guide for common solutions
2. Validate your data format against the templates
3. Ensure all required columns are present and correctly named
4. Check the dashboard's validation messages for specific errors

The dashboard provides detailed error messages to help you identify and fix data issues.