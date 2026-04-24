FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir ultralytics paho-mqtt

COPY app /app/app
COPY models /app/models
COPY test-images /app/test-images

CMD ["python", "/app/app/run_publish_folder.py"]