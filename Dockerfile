# Use official Python image
FROM python:3.11

# Set working directory
WORKDIR /app

# Copy files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Expose port for Gunicorn
EXPOSE 8000

# Start Gunicorn server with 4 workers
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]