# Multi-stage Dockerfile for ArXiv AutoSumm
# Optimized for size and build time

# Stage 1: Base Python image with minimal dependencies
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-xetex \
    pandoc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Development dependencies
FROM base as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python packages
COPY requirements.txt pyproject.toml ./
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt || pip install arxiv typer pydantic requests tiktoken

# Stage 3: Runtime image
FROM base as runtime

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN groupadd -r autosumm && useradd -r -g autosumm autosumm

# Create directories
RUN mkdir -p /app /data/cache /data/output /data/config && \
    chown -R autosumm:autosumm /app /data

# Switch to non-root user
USER autosumm
WORKDIR /app

# Copy application code
COPY --chown=autosumm:autosumm autosumm/ ./autosumm/
COPY --chown=autosumm:autosumm prompts/ ./prompts/
COPY --chown=autosumm:autosumm config.yaml ./
COPY --chown=autosumm:autosumm autosumm.sh ./

# Make scripts executable
RUN chmod +x autosumm.sh

# Copy entrypoint
COPY --chown=autosumm:autosumm docker/entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh

# Environment variables
ENV ARXIV_AUTOSUMM_CONFIG="/data/config/config.yaml" \
    ARXIV_AUTOSUMM_CACHE_DIR="/data/cache" \
    ARXIV_AUTOSUMM_OUTPUT_DIR="/data/output"

# Expose volume mounts
VOLUME ["/data/config", "/data/cache", "/data/output"]

# Default command
ENTRYPOINT ["./entrypoint.sh"]
CMD ["run"]