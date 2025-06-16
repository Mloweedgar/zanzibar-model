# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for geopandas and other geospatial libraries
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    libspatialindex-dev \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV GDAL_CONFIG=/usr/bin/gdal-config
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Create a non-root user with UID 1000 (usually maps to the host user)
RUN useradd -m -u 1000 appuser

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Ensure the app directory is owned by the new user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set Python path to include BEST-Z directory
ENV PYTHONPATH=/app/BEST-Z

# Expose Streamlit default port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run the dashboard
CMD ["python", "-m", "streamlit", "run", "BEST-Z/scripts/interactive_dashboard.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]