# Use official Python runtime
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ backend/
# Copy data for ingestion (optional, if you want to ingest on startup)
COPY data/ data/
# Copy frontend (served by Flask)
COPY frontend/ frontend/

# Expose port
EXPOSE 5000

# Set environment variable to point Flask to the right place if needed
# But our app.py expects relative ../frontend which works if we run from /app

# Run the application
CMD ["python", "backend/app.py"]
