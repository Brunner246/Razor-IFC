FROM python:3.14-slim

WORKDIR /app

COPY . /app

# Install build dependencies
# ifcopenshell and other packages might need system libraries depending on the exact version/wheels available
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir .

# directory for data persistence when deployed on Render
RUN mkdir -p /data/uploads /data/processed

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV MAX_WORKERS=2
ENV JOB_TIMEOUT_SECONDS=300

CMD ["python", "main.py", "serve", "--host", "0.0.0.0", "--port", "8000"]

# docker build -t ifc-splitter .
# docker run -p 8000:8000 ifc-splitter
# http://localhost:8000/docs