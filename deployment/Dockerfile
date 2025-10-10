FROM python:3.11-slim-bookworm AS builder

WORKDIR /usr/src/app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libmagic-dev file && \
    rm -rf /var/lib/apt/lists/*

# RUN apt-get update && \
#     apt-get install -y --no-install-recommends gcc && \
#     apt-get clean && \
#     rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
COPY . /usr/src/app/

COPY ./requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /usr/src/app/wheels -r requirements.txt

FROM python:3.11-slim-bookworm AS final

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends libmagic1 file

COPY --from=builder /usr/src/app/wheels /wheels
COPY --from=builder /usr/src/app/requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache /wheels/*

COPY . /app

RUN chmod +x deployment/start.sh
