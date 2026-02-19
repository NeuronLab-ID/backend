# Stage 1: Builder - Install all ML packages
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install ML packages using pre-built wheels
RUN pip install --no-cache-dir \
    numpy \
    scipy \
    pandas \
    scikit-learn \
    matplotlib

# Install PyTorch CPU-only version
RUN pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu

# Stage 2: Runtime - Slim image with only runtime dependencies
FROM python:3.11-slim

# Install runtime dependencies (libgomp1 needed for torch)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy installed scripts from builder
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy runner script
COPY runner.py /app/runner.py
WORKDIR /app

# Run as non-root user for security
USER nobody

# Set environment variables for matplotlib and Python
ENV MPLCONFIGDIR=/tmp
ENV HOME=/tmp
ENV PYTHONDONTWRITEBYTECODE=1

# Default command
CMD ["python", "runner.py"]
