# Running the add-on as a standalone container

This program can run as a standalone Docker container, for all the Home Assistant installations without an add-on store available (e.g. _Home Assistant container_).

## Docker Compose

If you use Docker Compose, a sample `docker-compose.yml` file might look like the following:

```yaml
# docker-compose.yml
version: "3.8"

services:
  doorbell:
    image: ghcr.io/pergolafabio/hikvision-doorbell
    tty: true   # To receive commands on STDIN
    env:
        # JSON string with the list of doorbells
        DOORBELLS: '[{"name":"outdoor", "ip": "192.168.0.1", "port": 8000, "username": "user", "password": "password"}]'
        
        # Connection to the MQTT broker
        MQTT__HOST: <hostname_of_broker>
        # Optionals
        MQTT__PORT: 1883
        MQTT__USERNAME: <broker_username>
        MQTT__PASSWORD: <broker_password>
        
        # To help diagnose problems
        SYSTEM__LOG_LEVEL: DEBUG
        SYSTEM__SDK_LOG_LEVEL: DEBUG
```

### Local development

A [docker-compose.yml](../docker-compose.yml) is provided in this repo and is used for local development.
It shows how to setup the required build args and the environment variables sourced from a `.env` file.

To use it:

- Create a `development.env` file with your own configuration values
    ```bash
    cp development.env.example development.env
    ```
    
- Start on or more of the defined containers:
    ```bash
    docker-compose up doorbell mosquitto
    ```

## Manually building and running the container

To manually build and run the container, run the following from the `hikvision-doorbell` folder:

- Build the image, specifying your architecture.
For instance:
```bash
docker build --build-arg=BUILD_ARCH=amd64 -t hikvision-doorbell .
```

- Run a container from the built image (remember to set the required environment variables, see below for details)
```bash
docker run -e MQTT__HOST=mosquitto hikvision-doorbell
```


## Configuration
If no configuration is provided, the container uses the values from the `default_config.yaml` file present in this repository.

The application uses [Goodconf](https://github.com/lincolnloop/goodconf) to manage its configuration.
The configuration values are read from the environment variables or from a JSON/YAML file.
If a custom configuration file is available, you can define the env variable `CONFIG_FILE_PATH` pointing to its location.

You can override a single configuration option via its corresponding environment variable. For instance by exporting the env variable `SYSTEM__LOG_LEVEL=DEBUG`.