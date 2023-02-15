FROM python:3.10.8-slim

# The build arguments are populated by Home Assistant during the image build
# Use this build argument to know for which platform we are building
ARG BUILD_ARCH

WORKDIR /app
RUN echo "Building for ${BUILD_ARCH}"

# Install the required dependencies from the package manager
RUN apt-get update \
    && apt-get install -y libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Hikvision SDK
COPY lib-${BUILD_ARCH} /app/lib-${BUILD_ARCH}

# Main application
COPY src/ /app/

# Default configuration file
COPY default_config.yaml /app/

# Enable python module to get stacktraces from C native calls
ENV PYTHONFAULTHANDLER=true
# Required env variable to load Hikvision ssl and crypto libraries instead of system libraries
ENV LD_LIBRARY_PATH=/app/lib-${BUILD_ARCH}

ENTRYPOINT [ "python3"]

CMD ["/app/main.py" ]