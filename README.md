# Simple Scheduler

A Python-based web application for scheduling and managing Python scripts with a modern dark-themed UI and secure authentication.

## Features

- Schedule Python scripts using cron expressions
- Modern, responsive dark-themed UI
- Real-time task monitoring
- Detailed task history and statistics
- Test run capability
- Script output logging
- Secure authentication system

## Requirements

- Python 3.11
- SQLite3

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd simple_scheduler
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   - Copy the example environment file: `cp .env.example .env`
   - Edit the `.env` file to set your username, password, and secret key

## Usage

1. Place your Python scripts in the `scripts` directory.

2. Start the application:
```bash
python run.py
```

3. Open your web browser and navigate to `http://localhost:5000`

4. Log in with the credentials you set in the `.env` file

## Directory Structure

```
simple_scheduler/
├── app/
│   ├── static/
│   ├── templates/
│   ├── models/
│   ├── routes/
│   └── __init__.py
├── scripts/
├── logs/
├── .env.example      # Example environment variables
├── .env              # Your environment variables (not tracked by git)
├── requirements.txt
├── run.py
└── README.md
```

## Task Configuration

Tasks can be configured with the following parameters:

- Name: A unique identifier for the task
- Description: Optional description of what the task does
- Script: Select from available scripts in the scripts directory
- Schedule: Cron expression (e.g., "0 0 * * *" for daily at midnight)
- Start Time: Optional start time for the task
- End Time: Optional end time for the task
- Extra Arguments: Additional command-line arguments to pass to the script

## Script Requirements

Scripts should:
1. Accept a datetime string as the first positional argument (provided automatically)
2. Handle any additional arguments specified in the task configuration
3. Return exit code 0 for success, non-zero for failure

## Authentication

The application uses a simple username and password authentication system. Credentials are stored in the `.env` file.

### Environment Variables

- `ADMIN_USERNAME`: Username for logging in (default: admin)
- `ADMIN_PASSWORD`: Password for logging in
- `SECRET_KEY`: Secret key for session encryption

You can generate a secure secret key with:
```bash
python -c "import secrets; print(secrets.token_hex(24))"
```

If environment variables are not set, the application will use default values (admin/password) but will display a warning.
