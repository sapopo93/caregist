FROM python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a

# Patch util-linux/libuuid past the pinned base image's CVE-2026-53612/53613/53614/76642/78408
RUN apk add --no-cache --upgrade libuuid

WORKDIR /app

# Install API dependencies from requirements file
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY api/ api/

EXPOSE 8000

# Host sets $PORT; default to 8000 locally
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips=${FORWARDED_ALLOW_IPS:-127.0.0.1}"]
