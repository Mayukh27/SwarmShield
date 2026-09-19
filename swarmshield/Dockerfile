FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn pyyaml httpx

COPY swarmshield ./swarmshield

EXPOSE 8000

CMD ["uvicorn", "swarmshield.gateway:app", "--host", "0.0.0.0", "--port", "8000"]