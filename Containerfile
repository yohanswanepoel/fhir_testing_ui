# Build stage
FROM fedora:latest as builder

# Install build dependencies
RUN dnf update -y && \
    dnf install -y python3-pip python3-devel gcc && \
    dnf clean all

# Create and set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir -U pip setuptools wheel && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM fedora:latest

# Install runtime dependencies only
RUN dnf update -y && \
    dnf install -y python3 && \
    dnf clean all

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create user with ID 1001 for OpenShift compatibility
RUN useradd -m -r -u 1001 flaskuser

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Set ownership to user 1001
RUN chown -R 1001:0 /app && \
    chmod -R g+rwX /app && \
    chown -R 1001:0 /opt/venv && \
    chmod -R g+rwX /opt/venv

# Switch to user 1001
USER 1001

# Make sure we use the virtualenv
ENV PATH="/opt/venv/bin:$PATH"

# Expose port (adjust if needed)
EXPOSE 5500

# Command to run the application
CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0"]
