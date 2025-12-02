# Multi-stage Dockerfile for Data Platform
# Builds all pipelines with common libraries

FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openjdk-17-jre-headless \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Set Java home
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Create spark user and directories
RUN useradd -m -u 1000 spark && \
    mkdir -p /app /opt/spark && \
    chown -R spark:spark /app /opt/spark

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ========== Development Stage ==========
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-spark \
    black \
    mypy \
    flake8

# Copy all source code
COPY --chown=spark:spark . .

USER spark

# ========== Production Stage ==========
FROM base as production

# Copy only necessary files
COPY --chown=spark:spark common/ /app/common/
COPY --chown=spark:spark pipelines/ /app/pipelines/
COPY --chown=spark:spark setup.py /app/

# Install common library as package
RUN pip install --no-cache-dir -e .

# Download JMX Exporter for Prometheus metrics
USER root
RUN mkdir -p /prometheus && \
    curl -L https://repo1.maven.org/maven2/io/prometheus/jmx/jmx_prometheus_javaagent/0.17.0/jmx_prometheus_javaagent-0.17.0.jar \
    -o /prometheus/jmx_prometheus_javaagent-0.17.0.jar && \
    chown spark:spark /prometheus/jmx_prometheus_javaagent-0.17.0.jar

USER spark

# Set entrypoint
ENTRYPOINT ["python"]

# ========== Default target ==========
FROM production
