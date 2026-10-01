FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Python dependencies before application code to improve build caching.
COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

# Copy only the runtime code and local data required by `python -m src.main`.
COPY src ./src
COPY data/knowledge_base.json data/sample_incidents.json data/historical_incidents.json ./data/

# Memory writes local files under data/memory at runtime.
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/data/memory \
    && chown -R appuser:appuser /app

USER appuser

CMD ["python", "-m", "src.main"]
