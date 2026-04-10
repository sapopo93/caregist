FROM python:3.12-slim

WORKDIR /app

# Install API dependencies from requirements file
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY api/ api/

EXPOSE 8000

# Host sets $PORT; default to 8000 locally
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips="*"
