# Running the addon as a standalone container

This program can run as a standalone Docker container, for all the Home Assistant installations without an add-on store available (e.g. _Home Assistant container_).

## Manually building and running
To manually build and run the container, run the following from the `hikvision-doorbell` folder:

- Build the image, specifying your architecture.
For instance:
```bash
docker build --build-arg=BUILD_ARCH=amd64 -t hikvision-doorbell .
```

- Run a container from the built image (remember to set the required environment variables, see `default_config.yaml`)
```bash
docker run hikvision-doorbell
```

## Docker Compose

An example `docker-compose.yml` is provided showing how to setup the required build args and the environment variables sourced from a `.env` file.

- Create a `development.env` file with your own configuration values
    ```bash
    cp development.env.example development.env
    ```
    
- Start the container:
    ```bash
    docker-compose up doorbell
    ```

## Configuration
If no configuration is provided, the container uses the values from the `default_config.yaml` file present in this repository.

The application uses [Goodconf](https://github.com/lincolnloop/goodconf) to manage its configuration.
The configuration values are read from the environment variables or from a JSON/YAML file.
If a custom configuration file is provided, you can define the env variable `CONFIG_FILE_PATH` pointing to its location.

You can override a single configuration option via its corresponding environment variable. For instance by setting the env variable `SYSTEM__LOG_LEVEL=DEBUG`.