FROM python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a

# Patch packages past the pinned base image's CVEs: util-linux/libuuid
# (CVE-2026-53612/53613/53614/76642/78408), and krb5-libs, zlib and musl
# (HIGH findings with fixed versions reported by Trivy on 11 Nov 2026)
RUN apk add --no-cache --upgrade libuuid krb5-libs zlib musl musl-utils

WORKDIR /app

# Install API dependencies from requirements file
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY api/ api/

EXPOSE 8000

# Host sets $PORT; default to 8000 locally
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips=${FORWARDED_ALLOW_IPS:-127.0.0.1}"]
