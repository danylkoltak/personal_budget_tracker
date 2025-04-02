# Use official Python image as a base
FROM python:3.12.6

# Set the working directory inside the container
WORKDIR /app

# Copy only requirements first for better Docker caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Default command to run FastAPI using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]