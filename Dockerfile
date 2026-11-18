# IntelDoc KG workbench: one self-contained image with the app, the published corpus and the partner call records.
# Build (locally):   docker build -t inteldoc:1.0 .
# Build (in Azure):  az acr build --registry <acr-name> --image inteldoc:1.0 .
# Run:               docker run --rm -p 8000:8000 inteldoc:1.0   then open http://127.0.0.1:8000
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends unzip && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

COPY . .
# Expand the world, verify and unpack the published corpus, generate and ingest the partner records.
# Everything the server needs is baked in; the running container makes no outbound requests.
RUN python -m scripts.demo world --seed 42 \
 && sha256sum -c artifacts/haiku-5000-results.zip.sha256 \
 && mkdir -p corpus && unzip -q artifacts/haiku-5000-results.zip -d corpus \
 && python -m scripts.demo cdr \
 && rm -rf artifacts .git \
 && useradd --system --home /app --shell /usr/sbin/nologin inteldoc \
 && chown -R inteldoc:inteldoc /app/corpus /app/world

USER inteldoc
ENV PORT=8000 HOST=0.0.0.0 PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import json,sys,urllib.request; sys.exit(0 if json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/health'))['status']=='ok' else 1)"
CMD ["python", "-m", "uvicorn", "inteldoc.app:app", "--host", "0.0.0.0", "--port", "8000"]
