# aiosimon-io

`aiosimon-io` is an asynchronous Python library for interacting with Simon iO smart home devices. It provides tools for OAuth2 authentication, managing installations, and controlling devices using asyncio.

## Table of Contents

- [aiosimon-io](#aiosimon-io)
  - [Table of Contents](#table-of-contents)
  - [Disclaimer](#disclaimer)
  - [Features](#features)
  - [Installation](#installation)
  - [Quick Start](#quick-start)
    - [Authentication](#authentication)
      - [Option 1: Custom Authentication](#option-1-custom-authentication)
      - [Option 2: Built-in Authentication](#option-2-built-in-authentication)
    - [Retrieve Current User](#retrieve-current-user)
    - [Manage Installations](#manage-installations)
      - [Retrieve All Installations](#retrieve-all-installations)
      - [Retrieve a Single Installation by ID](#retrieve-a-single-installation-by-id)
      - [About the `ttl` Parameter](#about-the-ttl-parameter)
    - [Manage Devices](#manage-devices)
      - [Retrieve All Devices in an Installation](#retrieve-all-devices-in-an-installation)
      - [Retrieve a Single Device by ID](#retrieve-a-single-device-by-id)
      - [Set Device State](#set-device-state)
      - [Adjust Device Level](#adjust-device-level)
      - [Retrieve Device Capabilities and Type](#retrieve-device-capabilities-and-type)
  - [Logging](#logging)
  - [Testing](#testing)
  - [Documentation](#documentation)
  - [Contributing](#contributing)
    - [Set Up a Development Environment](#set-up-a-development-environment)
    - [Run Tests and Validations](#run-tests-and-validations)
    - [Submitting Changes](#submitting-changes)
  - [License](#license)

## Disclaimer

This library is not officially endorsed by Simon S.A. It is an independent project and is not affiliated with the Simon iO platform.

## Features

- Asynchronous OAuth2 authentication with token refresh
- Retrieve user installations and associated devices
- Control device states (on/off, brightness, blinds, etc.)
- Extensible and well-structured async codebase

## Installation

Install the library using pip:

```bash
pip install aiosimon-io
```

## Quick Start

### Authentication

You can authenticate with the Simon iO API using one of the following approaches:

#### Option 1: Custom Authentication

Extend the `AbstractAuth` class to implement your own token management logic:

```python
import aiohttp
import asyncio
from aiosimon_io import AbstractAuth, SNS_BASE_URL

class CustomAuth(AbstractAuth):
    def __init__(self, session: aiohttp.ClientSession):
        super().__init__(session, SNS_BASE_URL)
        self.token = None

    async def async_get_access_token(self) -> str:
        # Implement your logic to retrieve or refresh the access token
        return self.token

# Usage
async with aiohttp.ClientSession() as session:
    auth_client: AbstractAuth = CustomAuth(session)
```

#### Option 2: Built-in Authentication

Use the `SimonAuth` class for automatic token management:

```python
from aiosimon_io import AbstractAuth, SimonAuth
import aiohttp

async with aiohttp.ClientSession() as session:
    auth_client: AbstractAuth = SimonAuth(
        client_id="your_client_id",
        client_secret="your_client_secret",
        username="your_username",
        password="your_password",
        session=session
    )
```

### Retrieve Current User

Retrieve information about the currently authenticated user:

```python
from aiosimon_io import User

user: User = await User.async_get_current_user(auth_client)
print(f"User: {user.name} {user.lastName}, Email: {user.email}")
```

### Manage Installations

#### Retrieve All Installations

Fetch all installations associated with the authenticated user:

```python
from aiosimon_io import Installation
from typing import List

installations: List[Installation] = await Installation.async_get_installations(auth_client, ttl=5)
for installation in installations:
    print(f"ID: {installation.id}, Name: {installation.name}")
```

#### Retrieve a Single Installation by ID

Fetch a specific installation by its ID:

```python
from aiosimon_io import Installation

installation_id = "your_installation_id"
installation: Installation = await Installation.async_get_installation(auth_client, installation_id, ttl=5)
print(f"Installation ID: {installation.id}, Name: {installation.name}")
```

#### About the `ttl` Parameter

The `ttl` parameter (optional, default: 5 seconds) specifies the time-to-live in seconds for cached data retrieved from the server or hub. It helps reduce repeated requests within a short period of time. If not provided, the default value of 5 seconds is used. You can set a custom `ttl` if you need to adjust the caching duration for specific use cases.

### Manage Devices

#### Retrieve All Devices in an Installation

Fetch all devices associated with a specific installation:

```python
from aiosimon_io import Device
from typing import Dict

devices: Dict[str, Device] = await installation.async_get_devices()
for device_id, device in devices.items():
    print(f"Device ID: {device_id}, Name: {device.name}")
```

#### Retrieve a Single Device by ID

Fetch a specific device by its ID:

```python
from aiosimon_io import Device

device_id = "your_device_id"
device: Device = await installation.async_get_device(device_id)
if device:
    print(f"Device ID: {device.id}, Name: {device.name}")
else:
    print("Device not found.")
```

#### Set Device State

Turn a device on or off:

```python
await device.async_set_state(True)  # Turn ON
await device.async_set_state(False)  # Turn OFF
```

#### Adjust Device Level

Set the brightness or blinds level of a device:

```python
await device.async_set_level(50)  # Set level to 50
```

#### Retrieve Device Capabilities and Type

Retrieve the capabilities and type of a device:

```python
device_type: str = device.get_device_type()
capabilities: List[str] = device.get_capabilities()

print(f"Device Type: {device_type}")
print(f"Capabilities: {capabilities}")
```

> **Note**: The `get_device_type()` method infers the device type based on the information provided by the manufacturer through the `get_type()` and `get_subtype()` methods. This mapping is handled internally by the `aiosimon-io` library. On the other hand, the `get_type()` and `get_subtype()` methods provide the device classification as defined by Simon iO.
>
> **Recommendation**: We recommend using the `get_device_type()` method as it simplifies the categorization of devices by abstracting the mapping logic and providing a consistent device type across different manufacturers.

## Logging

Enable logging to debug API interactions:

```python
import logging
from aiosimon_io import setup_logging

setup_logging(level=logging.ERROR)
```

## Testing

Run tests using `pytest`:

```bash
make test
````

or

```bash
pytest tests/
```

Check test coverage:

```bash
pytest --cov=aiosimon_io tests/
```

Generate an HTML coverage report:

```bash
make test-coverage
````

or

```bash
pytest --cov=aiosimon_io --cov-report=html tests/
```

## Documentation

Generate the documentation using Sphinx:

```bash
make docs
```

Open the generated `index.html` in the `docs/build/html` directory to view the documentation.

## Contributing

Contributions are welcome! If you'd like to contribute to the project, follow these steps to set up a development environment:

### Set Up a Development Environment

Run the following command to prepare a development environment:

```bash
make dev
```

This will:

1. Create a virtual environment in the project directory.
2. Install the project in editable mode along with all development dependencies (e.g., testing, linting, and documentation tools).

Once the environment is set up, activate it:

- On Linux/Mac:

  ```bash
  source venv/bin/activate
  ```

- On Windows:

  ```bash
  venv\Scripts\activate
  ```

### Run Tests and Validations

To ensure your changes meet the project's standards, run the following command:

```bash
make check
```

This command performs the following checks:

1. **Run Tests**: Executes all unit tests using `pytest`.
2. **Code Style Validation**:
   - **flake8**: Checks for Python syntax errors, undefined names, and style issues.
   - **black**: Ensures the code is formatted according to the Black code style.
   - **isort**: Validates that imports are sorted correctly.
3. **Static Type Checking**:
   - **mypy**: Performs strict type checking on the codebase.
4. **Validate `pyproject.toml`**:
   - **validate-pyproject**: Ensures the `pyproject.toml` file is valid and adheres to the TOML specification.

If any of these checks fail, the output will indicate the issues that need to be resolved.

### Submitting Changes

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and ensure all tests and validations pass.
4. Submit a pull request with a clear description of your changes.

## License

This project is licensed under the LGPL-3.0 License. See the [LICENSE](LICENSE) file for details.
