# SOUL Cloud (suflet_ai.app): device gateway + relay + SOUL connector (MCP + OAuth) in one process.
# Build from ai/:   docker build -t soul-cloud .
# Run (dev):        docker run -p 8080:8080 -e SOUL_PUBLIC_HOST=... soul-cloud
# Secrets come from the platform's secret store as environment variables, never from this image.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SOUL_DATA_DIR=/data \
    SOUL_TRUST_PROXY=1 \
    PORT=8080

WORKDIR /app
COPY requirements.txt constraints.txt ./
RUN pip install -r requirements.txt -c constraints.txt

COPY suflet_ai ./suflet_ai
COPY tools ./tools
COPY tests ./tests
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh \
    && useradd --uid 10001 --user-group --no-create-home --shell /usr/sbin/nologin soul \
    && mkdir -p /data && chown soul:soul /data && chmod 0700 /data

EXPOSE 8080
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python", "-m", "suflet_ai.app", "serve"]
