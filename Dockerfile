FROM python:3.11-slim

WORKDIR /app

# System deps (minimal; rely on manylinux wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Ensure package imports like `import app` resolve
ENV PYTHONPATH=/app \
    \
    # Defaults for fast first paint; override at runtime as needed
    STREAMLIT_SERVER_HEADLESS=true \
    FIO_MAX_POINTS=3000 \
    FIO_READ_NROWS=6000

EXPOSE 8501 8081

CMD ["streamlit", "run", "app/dashboard.py", "--server.port=8501", "--server.headless=true", "--server.address=0.0.0.0"]


