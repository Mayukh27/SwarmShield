# Build from the repo root:  docker build -f swarmshield/Dockerfile .
FROM python:3.12-slim
WORKDIR /app
COPY swarmshield/requirements-gateway.txt .
RUN pip install --no-cache-dir -r requirements-gateway.txt
COPY swarmshield ./swarmshield
ENV SWARMSHIELD_POLICY=/app/swarmshield/policies/controlled_target_policy.yaml
EXPOSE 8100
CMD ["uvicorn", "swarmshield.gateway:app", "--host", "0.0.0.0", "--port", "8100"]
