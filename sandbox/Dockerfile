FROM python:3.11

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

# Create tmp directory with write permissions
RUN mkdir -p /tmp && chmod 777 /tmp

# Copy runner script
COPY runner.py /app/runner.py
WORKDIR /app

# Run as non-root user for security
USER nobody

# Set environment variables for matplotlib
ENV MPLCONFIGDIR=/tmp
ENV HOME=/tmp

# Default command
CMD ["python", "runner.py"]
