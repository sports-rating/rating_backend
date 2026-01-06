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

# --- Stage 1: Build Stage ---
FROM python:3.13-slim-bookworm AS builder

# 1. Environment variables for uv
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# 2. Grab the uv binary (Faster than curl/install.sh)
COPY --from=ghcr.io/astral-sh/uv:0.5.2 /uv /uvx /bin/

WORKDIR /app

# 3. Install build-only system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy dependency files
COPY pyproject.toml uv.lock ./

# 5. Sync dependencies using Docker cache mount
# This ensures that re-builds are nearly instant if only code changes
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync \
      --frozen \
      --no-dev \
      --no-install-project


# --- Stage 2: Final Runtime Stage ---
FROM python:3.13-slim-bookworm AS final

WORKDIR /app

# 6. Install runtime-only system dependencies (ffmpeg for your bot)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    file \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 7. Copy the virtual environment and app code
COPY --from=builder /app/.venv /app/.venv
COPY . /app

# 8. Setup PATH so you can call 'python' and 'manage.py' directly
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

RUN chmod +x deployment/start.sh

CMD ["deployment/start.sh"]
