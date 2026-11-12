FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    NUXIVA_PORT=8443

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY server/requirements.txt server/requirements.txt
RUN pip install -r server/requirements.txt
RUN pip check \
    && python -c "import fastapi, uvicorn, pydantic_settings, sqlalchemy; from cryptography.fernet import Fernet; key = Fernet.generate_key(); cipher = Fernet(key); assert cipher.decrypt(cipher.encrypt(b'nuxiva-build-check')) == b'nuxiva-build-check'"

COPY server ./server

ARG NUXIVA_SRC_HASH=dev
LABEL org.nuxiva.src=$NUXIVA_SRC_HASH

EXPOSE 8443
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=4 \
    CMD curl -fsS "http://127.0.0.1:${NUXIVA_PORT}/health" || exit 1

CMD ["python", "-m", "server.cmd.main"]
