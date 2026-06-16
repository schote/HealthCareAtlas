FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/dagster/app

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY pipeline/ pipeline/
RUN pip install --no-cache-dir -e .

# Dagster workspace config
COPY workspace.yaml /opt/dagster/workspace.yaml

# Dagster home directory for run storage, event log, schedule state
RUN mkdir -p /opt/dagster/dagster_home
COPY dagster.yaml /opt/dagster/dagster_home/dagster.yaml

ENV DAGSTER_HOME=/opt/dagster/dagster_home
ENV PYTHONPATH=/opt/dagster/app

EXPOSE 3000
