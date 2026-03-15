FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy source code and config
COPY pyproject.toml .
COPY src/ src/
COPY migrations/ migrations/
COPY alembic.ini .

# Install Python dependencies
RUN pip install --no-cache-dir .

EXPOSE 8000

# Run migrations then start the API
CMD ["sh", "-c", "alembic upgrade head && uvicorn lofty.main:app --host 0.0.0.0 --port 8000"]
