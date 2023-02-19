# Running the addon with Docker

To manually build and run the container, run the following from the `hikvision-doorbell` folder:

- Build the image, specifying your architecture.
For instance:
```bash
docker build --build-arg=BUILD_ARCH=amd64 -t hikvision-doorbell .
```

- Run a container from the built image (remember to set the required environment variables)
```bash
docker run hikvision-doorbell
```

## Docker Compose

An example `docker-compose.yml` is provided showing how to setup the required build args and the environment variables.