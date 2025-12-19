FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r demo_service/requirements.txt
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn","demo_service.app:app","--host","0.0.0.0","--port","8001"]
