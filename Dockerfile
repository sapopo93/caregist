FROM python:3.12-slim

WORKDIR /app

# Install only API dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir fastapi uvicorn[standard] asyncpg pydantic-settings

COPY api/ api/

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
