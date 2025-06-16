# zanzibar-model

Contains the BEST-Z nitrogen load workflows in the `BEST-Z` folder.

## Installation

### Local Installation

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### Docker Deployment

For easy deployment using Docker:

```bash
# Development mode
docker-compose up --build

# Production mode
docker-compose -f docker-compose.prod.yml up --build -d
```

See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) for detailed deployment instructions.

## Running the Dashboard

### Local Development
```bash
python run_dashboard.py
```

### Docker
The dashboard will be available at:
- Development: http://localhost:8501
- Production: http://localhost

## 📁 Custom Data Upload

The dashboard now supports uploading your own data files! You can:

- **Upload custom census data** (CSV format)
- **Upload sanitation efficiency data** (CSV format) 
- **Upload ward boundary files** (GeoJSON format)

### Quick Start with Custom Data

1. Open the dashboard
2. Select "Upload Custom Data" in the sidebar
3. Upload your three required files
4. The dashboard will validate and process your data automatically

### Data Format Requirements

See [DATA_UPLOAD_GUIDE.md](DATA_UPLOAD_GUIDE.md) for detailed information about:
- Required file formats and columns
- Data validation requirements
- Template files for download
- Troubleshooting common issues

### Template Files

Download template files directly from the dashboard:
1. Select "Upload Custom Data" 
2. Expand "📋 Required Data Formats"
3. Click "📥 Download Template Files"
