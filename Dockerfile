FROM python:3.12-slim

WORKDIR /app

# Install API dependencies
RUN pip install --no-cache-dir fastapi uvicorn[standard] asyncpg pydantic-settings stripe email-validator

COPY api/ api/

EXPOSE 8000

# Railway sets $PORT; default to 8000 for Docker Compose
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
