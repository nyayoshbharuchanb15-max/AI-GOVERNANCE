FROM python:3.12-slim
WORKDIR /srv
COPY orchestrator/requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir -r /srv/requirements.txt
COPY store /srv/store
COPY graph /srv/graph
COPY events /srv/events
COPY certs /srv/certs
COPY engines /srv/engines
COPY orchestrator /srv/orchestrator
COPY schemas /srv/schemas
ENV PYTHONPATH=/srv
ENV CERT_KEY_FILE=/keys/ed25519.seed
EXPOSE 8010
CMD ["uvicorn", "orchestrator.main:app", "--host", "0.0.0.0", "--port", "8010"]
