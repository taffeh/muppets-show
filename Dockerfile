FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Cloud Run listens on 8080
EXPOSE 8080

# timeout-keep-alive must exceed the longest show run (~5 min) plus headroom
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080", \
     "--timeout-keep-alive", "600"]
