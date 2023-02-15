# Running the addon locally with Docker

There is a `docker-compose.yml` provided showing how to setup the required build args.

To manually build and run the container, run the following from the `hikvision-sdk` folder:

- Build the image, specifying your architecture.
For instance:
```bash
docker build --build-arg=BUILD_ARCH=amd64 -t hikvision-sdk .
```

- Run a container from the built image (set the required environment variables)
```bash
docker run -e IP=192.168.0.250 hikvision-sdk
```