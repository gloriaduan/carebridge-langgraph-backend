FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application code
COPY . .

# Command to run the application
CMD uvicorn main:app_asgi --host 0.0.0.0 --port $PORT