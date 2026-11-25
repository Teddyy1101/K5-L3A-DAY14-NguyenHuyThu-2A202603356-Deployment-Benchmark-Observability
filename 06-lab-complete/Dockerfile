FROM python:3.11-slim AS builder

RUN python -m venv /opt/venv
WORKDIR /app
COPY requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000
WORKDIR /app

RUN groupadd --system agent && useradd --system --gid agent --no-create-home agent
COPY --from=builder /opt/venv /opt/venv
COPY --chown=agent:agent app ./app
COPY --chown=agent:agent utils ./utils
USER agent

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c 'import os, urllib.request; urllib.request.urlopen("http://127.0.0.1:" + os.environ["PORT"] + "/health", timeout=2).close()'

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\" --workers 2"]
