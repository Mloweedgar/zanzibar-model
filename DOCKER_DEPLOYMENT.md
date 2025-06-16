# Docker Deployment Guide for BEST-Z Nitrogen Model Dashboard

This guide explains how to deploy the BEST-Z Nitrogen Model Dashboard using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- **Memory Requirements:**
  - Minimum: 512MB RAM (low-memory configuration)
  - Recommended: 1GB RAM (standard production)
  - Optimal: 2GB+ RAM (heavy usage)

## Quick Start

### Development Deployment

1. **Build and run the application:**
   ```bash
   docker-compose up --build
   ```

2. **Access the dashboard:**
   Open your browser and navigate to `http://localhost:8501`

3. **Stop the application:**
   ```bash
   docker-compose down
   ```

### Production Deployment

1. **Standard production (1GB RAM):**
   ```bash
   docker-compose -f docker-compose.prod.yml up --build -d
   ```

2. **Low-memory deployment (512MB RAM):**
   ```bash
   docker-compose -f docker-compose.low-mem.yml up --build -d
   ```

3. **Access the dashboard:**
   - Standard production: `http://localhost` (port 80)
   - Low-memory: `http://localhost:8501`

4. **Stop the application:**
   ```bash
   # Standard production
   docker-compose -f docker-compose.prod.yml down
   
   # Low-memory
   docker-compose -f docker-compose.low-mem.yml down
   ```

## Configuration Options

### Environment Variables

The following environment variables can be customized:

- `STREAMLIT_SERVER_PORT`: Port for Streamlit server (default: 8501)
- `STREAMLIT_SERVER_ADDRESS`: Server address (default: 0.0.0.0)
- `STREAMLIT_SERVER_HEADLESS`: Run in headless mode (default: true)
- `STREAMLIT_BROWSER_GATHER_USAGE_STATS`: Disable usage stats (default: false)

### Volume Mounts

- `./BEST-Z/data_raw`: Raw data files (mounted as read-only)
- `./BEST-Z/outputs`: Generated output files (read-write)

### Port Mapping

- **Development**: `8501:8501` (access via http://localhost:8501)
- **Production**: `80:8501` (access via http://localhost)

## Monitoring and Health Checks

The container includes health checks that verify the Streamlit application is running properly:

- **Health check endpoint**: `http://localhost:8501/_stcore/health`
- **Check interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3

## Resource Limits

### Standard Production (docker-compose.prod.yml)
- **Memory limit**: 1GB
- **CPU limit**: 1.0 core
- **Memory reservation**: 256MB
- **CPU reservation**: 0.25 core

### Low-Memory Configuration (docker-compose.low-mem.yml)
- **Memory limit**: 512MB
- **CPU limit**: 0.5 core
- **Memory reservation**: 128MB
- **CPU reservation**: 0.1 core

## Memory Optimization

### Choosing the Right Configuration

**Use `docker-compose.low-mem.yml` if:**
- You have limited RAM (512MB - 1GB available)
- Running on a VPS or cloud instance with memory constraints
- Single user or light usage expected

**Use `docker-compose.prod.yml` if:**
- You have 1GB+ RAM available
- Multiple concurrent users expected
- Need faster data processing

### Memory Usage Estimates
- **Base Streamlit app**: ~100-150MB
- **Data loading (55MB CSV)**: ~200-300MB peak during load
- **Geopandas operations**: ~100-200MB additional
- **Total typical usage**: 400-650MB
- **Peak usage**: 600-800MB during heavy operations

## Troubleshooting

### Common Issues

1. **Port already in use:**
   ```bash
   # Check what's using the port
   lsof -i :8501
   # Or change the port in docker-compose.yml
   ```

2. **Permission issues with volumes:**
   ```bash
   # Ensure proper permissions on data directories
   chmod -R 755 BEST-Z/data_raw
   chmod -R 755 BEST-Z/outputs
   ```

3. **Container fails to start:**
   ```bash
   # Check container logs
   docker-compose logs best-z-dashboard
   ```

### Viewing Logs

```bash
# View real-time logs
docker-compose logs -f best-z-dashboard

# View logs for production deployment
docker-compose -f docker-compose.prod.yml logs -f best-z-dashboard
```

### Rebuilding the Image

```bash
# Force rebuild without cache
docker-compose build --no-cache

# Remove old images
docker image prune -f
```

## Development Mode

For development, you can mount the scripts directory to enable live code changes:

1. Uncomment the scripts volume mount in `docker-compose.yml`:
   ```yaml
   volumes:
     - ./BEST-Z/scripts:/app/BEST-Z/scripts:ro
   ```

2. Restart the container:
   ```bash
   docker-compose restart
   ```

## Security Considerations

- Data directory is mounted as read-only in production
- XSRF protection is enabled in production
- CORS is disabled in production
- Container runs with resource limits
- Health checks ensure service availability

## Backup and Data Management

### Backing up outputs:
```bash
# Create backup of outputs directory
tar -czf best-z-outputs-$(date +%Y%m%d).tar.gz BEST-Z/outputs/
```

### Updating data:
```bash
# Stop the container
docker-compose down

# Update data files in BEST-Z/data_raw/

# Restart the container
docker-compose up -d
```