FROM python:3.11-slim

WORKDIR /app

# System deps for GDAL/geopandas
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev gdal-bin gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: run the full data pipeline
CMD ["python", "-m", "src.download_data"]
