# Running the addon locally with Docker

Run the following from the `hikvision-sdk` folder:

- build the image, specifying the base image, based on your architecture (see `build.yaml` for references).
For instance:
```bash
docker build --build-arg=BUILD_FROM=library/python:3.10.8-slim --build-arg=BUILD_ARCH=amd64 -t hikvision-sdk .
```

- Run a container from the built image (remember to set the required environment variables!)
```bash
docker run --name hikvision -e IP=192.168.0.250 hikvision-sdk
```