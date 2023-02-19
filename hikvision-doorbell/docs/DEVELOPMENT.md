# Development guide

The current setup only works for x86/x64 system due to the HikVision SDK native libraries used, and has been tested on a Linux OS (Linux Mint).

## Requirements

- Python 3.8
- (optional) A fresh [virtualenv](https://docs.python.org/3/library/venv.html) for this project

## Instructions
After having cloned the repository, run the following commands from the `hikvision-doorbell` directory.

- Install the required packages
```bash
pip install -r requirements.txt
```

- Export the required environment variables to configure the software (see `development.env.example` for reference)
```bash
export DOORBELLS='[{"name":"outdoor", "ip": "192.168.0.1", "username": "user", "password": "password"}]'
export HOME_ASSISTANT__URL=http://localhost:8123
export HOME_ASSISTANT__TOKEN=<secret_token>
```

- Launch the application
```bash
python src/main.py
```

## VSCode
If using VSCode, there is a run configuration already provided.
First create a `development.env` file with your own values
```bash
cp development.env.example development.env
```

- If using VSCode, there is a run configuration already provided.
First create a `development.env` file with your own values, then run the application using the integrated VSCode debugger.
```bash
cp development.env.example development.env
```
Run the application using the integrated VSCode runner (under `Run and Debug`).

## Testing the addon locally (VSCode devcontainer)
For more information see the official HA [guide](https://developers.home-assistant.io/docs/add-ons/testing).

Inside the _devcontainer_ use the task `Start Home Assistant` to bootstrap the HA supervisor, who will then proceed to locally install HA.

The local instance is accessible under `http://localhost:7123/`.

The addon should be visible in the add-on store.
