FROM python:3.10.8-slim AS builder

ARG BUILD_ARCH
WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libffi-dev \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt


# Build final image
FROM python:3.10.8-slim

ARG BUILD_ARCH
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi7 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY lib-${BUILD_ARCH} /app/lib-${BUILD_ARCH}

COPY src/ /app/
COPY default_config.yaml /app/

ENV PYTHONFAULTHANDLER=true
ENV LD_LIBRARY_PATH=/app/lib-${BUILD_ARCH}
ENV PYTHONUNBUFFERED=1

ENTRYPOINT [ "python3"]
CMD ["/app/main.py" ]