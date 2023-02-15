# The build variables are populated by Home Assistant during the image build
ARG BUILD_FROM
FROM $BUILD_FROM

# Use this build argument to know for which platform we are building
ARG BUILD_ARCH

WORKDIR /app
RUN echo "Installing dependencies for ${BUILD_ARCH}"

# Check the architecture for which we are building, and use the appropriate packaging tool to install the dependencies
RUN if [ ${BUILD_ARCH} = "i386" ] || [ ${BUILD_ARCH} = "amd64" ]; then \
        # Debian based system
        apt-get update && apt-get install -y libffi-dev; \
    else \
        # openeuler OS
        yum -y install python-pip; \
    fi

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Hikvision SDK
COPY lib-${BUILD_ARCH} /app/lib-${BUILD_ARCH}

# Main application
COPY src/*.py /app/

ENTRYPOINT [ "python3", "/app/hik.py" ]
