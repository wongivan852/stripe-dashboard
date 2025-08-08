FROM python:3.8-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p instance csv_data july25 && chmod 755 instance csv_data july25

# Create a symlink for backward compatibility
RUN ln -sf july25 new_csv

# Expose port
EXPOSE 8081

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite:///instance/payments.db
ENV CSV_DATA_PATH=/app/july25

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8081/ || exit 1

# Initialize database and run the application
CMD ["sh", "-c", "python init_db.py && python run.py"]
