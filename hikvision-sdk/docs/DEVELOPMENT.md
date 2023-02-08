# Development guide (for x86/64 only)

The current setup only works for x86/x64 system, and has been tested on a Linux OS.
After having cloned the repository, run the following commands from the `hikvision-sdk` directory.

- Install the required packages
```bash
pip install -r requirements.txt
```

- Export the required environment variables to configure the software (see `config.py`)
```bash
export IP=192.168.0.100
export USER=admin
export PASSWORD=admin
```

- Run/Debug the application
```bash
python hik.py
```

- If using VSCode, there is a run configuration already provided.
First create a `development.env` file with your own values, then run the application using the integrated VSCode debugger.
```bash
cp development.env.example development.env
```