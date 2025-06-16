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
