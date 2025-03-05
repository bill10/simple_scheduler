# Simple Scheduler

A Python-based web application for scheduling and managing Python scripts with a modern dark-themed UI.

## Features

- Schedule Python scripts using cron expressions
- Modern, responsive dark-themed UI
- Real-time task monitoring
- Detailed task history and statistics
- Test run capability
- Script output logging

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

## Usage

1. Place your Python scripts in the `scripts` directory.

2. Start the application:
```bash
python run.py
```

3. Open your web browser and navigate to `http://localhost:5000`

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
