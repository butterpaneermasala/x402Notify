FROM python:3.11-slim
WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y build-essential gcc libffi-dev && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . /app

# Install SDK and dev_service requirements
RUN pip install --no-cache-dir -e ./sdk/python
RUN if [ -f ./dev_service/requirements.txt ]; then pip install --no-cache-dir -r ./dev_service/requirements.txt; fi

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "dev_service.app:app", "--host", "0.0.0.0", "--port", "8001"]
