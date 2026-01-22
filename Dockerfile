# Use an official Python runtime as a parent image
FROM python:3.14-slim

WORKDIR /app

COPY . /app

# Install build dependencies
# ifcopenshell and other packages might need system libraries depending on the exact version/wheels available
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir .

# Create directory for data persistence if not using volumes
RUN mkdir -p data/uploads data/processed

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py", "serve", "--host", "0.0.0.0", "--port", "8000"]

# docker build -t ifc-splitter .
# docker run -p 8000:8000 ifc-splitter
# http://localhost:8000/docs