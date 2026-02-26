# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies if required
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Run stage
FROM python:3.11-slim

WORKDIR /app

# Create a non-root user
RUN addgroup --system appgroup && adduser --system --group appuser

# Install dependencies from wheels
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Copy application code and set ownership
COPY --chown=appuser:appgroup . .

# Switch to non-root user
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
