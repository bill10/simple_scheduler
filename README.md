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

## Data Storage

The Simple Scheduler uses two separate SQLite databases to manage different aspects of the application:

### Main Application Database (`instance/scheduler.db`)

**Purpose**: Stores all business data and application state

**Tables**:
- **`task`**: Task definitions and configuration
  - Basic info: `id`, `name`, `description`, `script_path`, `cron_schedule`
  - Scheduling: `start_date`, `end_date`, `is_active`
  - Configuration: `extra_args`
  - Timestamps: `created_at`, `updated_at`
  - Backfill state: `backfill_*` columns for bulk operations

- **`task_run`**: Complete execution history
  - Run identity: `id`, `task_id` (foreign key)
  - Timing: `start_time`, `end_time`, `duration`
  - Status: `status` ('success', 'failure', 'running', 'pending')
  - Logging: `log_file` (path to detailed execution log)
  - Metadata: `created_at`

**Managed by**: Flask-SQLAlchemy ORM  
**Used for**: Web UI, API endpoints, run history, statistics, calendar color-coding

### APScheduler Job Store (`jobs.sqlite`)

**Purpose**: Stores APScheduler's internal scheduling data

**Tables**:
- **`apscheduler_jobs`**: Active scheduled jobs
  - Job identity: `id`
  - Scheduling: `next_run_time`
  - State: `job_state` (serialized job objects)

**Managed by**: APScheduler library  
**Used for**: Job scheduling engine, determining when tasks should run

### How They Work Together

1. **Task Creation**: User creates task → stored in `scheduler.db` → APScheduler job created in `jobs.sqlite`
2. **Task Execution**: APScheduler reads `jobs.sqlite` → executes job → results stored in `scheduler.db`
3. **Data Flow**: `scheduler.db` is the source of truth, `jobs.sqlite` is the active scheduling state

### Log Files

Detailed execution logs are stored as individual files in the `logs/` directory:
- Each task run generates a separate log file
- File paths are stored in the `task_run.log_file` column
- Contains complete stdout/stderr output from script execution

### Backup Considerations

- **Critical**: `instance/scheduler.db` (contains all task definitions and execution history)
- **Important**: `logs/` directory (detailed execution logs)
- **Regenerable**: `jobs.sqlite` (can be rebuilt from scheduler.db by restarting the application)
