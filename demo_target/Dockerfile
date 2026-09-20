# Build from the repo root: docker build -f demo_target/Dockerfile demo_target
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . ./demo_target
EXPOSE 9200
CMD ["uvicorn", "demo_target.app:app", "--host", "0.0.0.0", "--port", "9200"]
