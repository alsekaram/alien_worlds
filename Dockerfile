FROM python:3.13-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy your application files
COPY . /app/

# Install dependencies
RUN uv pip install --system .

# Command to run the application
CMD ["python", "src/alienworlds/main.py"]