FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r demo_service/requirements.txt
ENV PYTHONUNBUFFERED=1
ENV PORT=8001
# Use the PORT env provided by Render at runtime (fall back to 8001)
CMD ["/bin/sh","-c","uvicorn demo_service.app:app --host 0.0.0.0 --port ${PORT:-8001}"]
