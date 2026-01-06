# FROM python:3.11-slim-bookworm AS builder

# WORKDIR /usr/src/app

# ENV PYTHONUNBUFFERED=1
# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# RUN apt-get update && \
#     apt-get install -y --no-install-recommends gcc libmagic-dev file ffmpeg && \
#     rm -rf /var/lib/apt/lists/*

# # RUN apt-get update && \
# #     apt-get install -y --no-install-recommends gcc && \
# #     apt-get clean && \
# #     rm -rf /var/lib/apt/lists/*

# RUN pip install --upgrade pip
# COPY . /usr/src/app/

# COPY ./requirements.txt .
# RUN pip wheel --no-cache-dir --no-deps --wheel-dir /usr/src/app/wheels -r requirements.txt

# FROM python:3.11-slim-bookworm AS final

# WORKDIR /app

# RUN apt-get update && \
#     apt-get install -y --no-install-recommends libmagic1 file ffmpeg

# COPY --from=builder /usr/src/app/wheels /wheels
# COPY --from=builder /usr/src/app/requirements.txt .

# RUN pip install --upgrade pip
# RUN pip install --no-cache /wheels/*

# COPY . /app

# RUN chmod +x deployment/start.sh

# --- Stage 1: Builder ---
# Use the official uv image which comes with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /usr/src/app

# Enable bytecode compilation and optimize for Docker
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install system dependencies needed for building (e.g., gcc for psycopg2 if not binary)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libmagic-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy only dependency files first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies (no dev tools, no root project installation)
RUN uv sync --frozen --no-dev --no-install-project


# --- Stage 2: Final ---
FROM python:3.13-slim-bookworm AS final

WORKDIR /app

# Install runtime-only system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends libmagic1 file ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder
COPY --from=builder /usr/src/app/.venv /app/.venv

# Copy your application code
COPY . /app

# Ensure the start script is executable
RUN chmod +x deployment/start.sh

# Environment variables to use the venv automatically
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the start script
CMD ["deployment/start.sh"]
