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
# Use standard Docker Hub image instead of ghcr.io
FROM python:3.13-slim-bookworm AS builder

WORKDIR /usr/src/app

# Install uv using the official standalone installer
ADD https://astral.sh/uv/install.sh /install.sh
RUN chmod +x /install.sh && /install.sh && rm /install.sh

# Ensure uv is in the PATH for the builder stage
ENV PATH="/root/.local/bin:$PATH"
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libmagic-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency files and sync
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project


# --- Stage 2: Final ---
FROM python:3.13-slim-bookworm AS final

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends libmagic1 file ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Copy the venv from builder
COPY --from=builder /usr/src/app/.venv /app/.venv

# Copy your code
COPY . /app
RUN chmod +x deployment/start.sh

# Environment setup
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

CMD ["deployment/start.sh"]
