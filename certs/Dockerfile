FROM python:3.12-slim
WORKDIR /srv
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" cryptography httpx
COPY certs /srv/certs
ENV PYTHONPATH=/srv
ENV CERT_KEY_FILE=/keys/ed25519.seed
EXPOSE 8020
CMD ["uvicorn", "certs.service:app", "--host", "0.0.0.0", "--port", "8020"]
