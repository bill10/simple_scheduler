import os
import subprocess
import threading
from datetime import datetime, timedelta
from apscheduler.triggers.cron import CronTrigger
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytz
from flask import Blueprint, jsonify, request, current_app
from ..models.models import db, Task, TaskRun
from .auth_routes import login_required

bp = Blueprint('tasks', __name__, url_prefix='/api')

def ensure_utc(dt):
    """Ensure datetime is UTC"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    return dt.astimezone(pytz.UTC)

@bp.route('/tasks', methods=['GET'])
@login_required
def get_tasks():
    tasks = Task.query.all()
    return jsonify([{
        'id': task.id,
        'name': task.name,
        'description': task.description,
        'is_active': task.is_active,
        'last_run': get_last_run_status(task),
        'next_run': calculate_next_run(task),
        'total_runs': len(task.runs)
    } for task in tasks])

@bp.route('/tasks', methods=['POST'])
@login_required
def create_task():
    data = request.json
    task = Task(
        name=data['name'],
        description=data.get('description', ''),
        script_path=data['script_path'],
        cron_schedule=data['cron_schedule'],
        start_date=ensure_utc(datetime.fromisoformat(data['start_date'])) if data.get('start_date') else None,
        end_date=ensure_utc(datetime.fromisoformat(data['end_date'])) if data.get('end_date') else None,
        extra_args=data.get('extra_args', '')
    )
    db.session.add(task)
    db.session.commit()
    schedule_task(task)
    return jsonify({'id': task.id}), 201

@bp.route('/tasks/<int:task_id>', methods=['GET'])
@login_required
def get_task(task_id):
    task = Task.query.get_or_404(task_id)
    next_run = calculate_next_run(task)
    
    def format_utc(dt):
        if dt is None:
            return None
        # Handle case where dt is already a string
        if isinstance(dt, str):
            return dt
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        return dt.astimezone(pytz.UTC).isoformat()
    
    return jsonify({
        'id': task.id,
        'name': task.name,
        'description': task.description,
        'script_path': task.script_path,
        'cron_schedule': task.cron_schedule,
        'start_date': format_utc(task.start_date),
        'end_date': format_utc(task.end_date),
        'extra_args': task.extra_args,
        'is_active': task.is_active,
        'next_run': format_utc(next_run)
    })

@bp.route('/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.json
    
    task.name = data.get('name', task.name)
    task.description = data.get('description', task.description)
    task.cron_schedule = data.get('cron_schedule', task.cron_schedule)
    task.extra_args = data.get('extra_args', task.extra_args)
    
    if 'start_date' in data:
        task.start_date = ensure_utc(datetime.fromisoformat(data['start_date'])) if data['start_date'] else None
    if 'end_date' in data:
        task.end_date = ensure_utc(datetime.fromisoformat(data['end_date'])) if data['end_date'] else None
    
    db.session.commit()
    reschedule_task(task)
    return jsonify({'status': 'success'})

@bp.route('/tasks/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_task(task_id):
    task = Task.query.get_or_404(task_id)
    task.is_active = not task.is_active
    db.session.commit()
    
    if task.is_active:
        schedule_task(task)
    else:
        unschedule_task(task)
    
    return jsonify({'status': 'success', 'is_active': task.is_active})

@bp.route('/tasks/<int:task_id>/test', methods=['POST'])
@login_required
def test_task(task_id):
    task = Task.query.get_or_404(task_id)
    result = run_task(task, test_mode=True)
    return jsonify(result)

@bp.route('/tasks/<int:task_id>/runs/<int:run_id>/rerun', methods=['POST'])
@login_required
def rerun_task(task_id, run_id):
    task = Task.query.get_or_404(task_id)
    original_run = TaskRun.query.filter_by(id=run_id, task_id=task_id).first_or_404()
    
    # Use the original run's start time as the scheduled time for the rerun
    # Round to the nearest minute to match the original scheduled time
    scheduled_time = original_run.start_time.replace(second=0, microsecond=0)
    
    # Create a new TaskRun record for the rerun
    execution_start = datetime.utcnow()
    
    new_run = TaskRun(
        task_id=task.id,
        start_time=scheduled_time,  # Use the original scheduled time
        status='running'
    )
    db.session.add(new_run)
    db.session.commit()
    
    # Execute the task with the scheduled time
    result = run_task(task, test_mode=False, scheduled_time=scheduled_time)
    
    # Update the TaskRun record with the results
    execution_end = datetime.utcnow()
    duration = (execution_end - execution_start).total_seconds()
    
    new_run.end_time = execution_end
    new_run.status = result['status']
    new_run.duration = duration
    new_run.log_file = result['log_file']  # Use the log file from run_task
    db.session.commit()
    
    return jsonify(result)

@bp.route('/tasks/<int:task_id>/runs', methods=['GET'])
@login_required
def get_task_runs(task_id):
    Task.query.get_or_404(task_id)  # Verify task exists
    date = request.args.get('date')
    
    query = TaskRun.query.filter_by(task_id=task_id)
    if date:
        # Convert input date to UTC for comparison
        date_obj = ensure_utc(datetime.fromisoformat(date))
        
        # Create UTC start and end of day
        start_of_day = ensure_utc(datetime.combine(date_obj.date(), datetime.min.time()))
        end_of_day = ensure_utc(datetime.combine(date_obj.date(), datetime.max.time()))
            
        query = query.filter(
            TaskRun.start_time >= start_of_day,
            TaskRun.start_time <= end_of_day
        )
    
    # Always order by start time
    query = query.order_by(TaskRun.start_time.asc())
    
    runs = query.all()
    
    # Group runs by scheduled time (hour:minute)
    grouped_runs = {}
    for run in runs:
        if run.start_time:
            # Extract scheduled time (hour:minute) as the grouping key
            scheduled_time = run.start_time.replace(second=0, microsecond=0)
            scheduled_time_key = scheduled_time.strftime('%H:%M')
            
            if scheduled_time_key not in grouped_runs:
                grouped_runs[scheduled_time_key] = {
                    'scheduled_time': scheduled_time.isoformat(),
                    'scheduled_time_display': scheduled_time_key,
                    'runs': []
                }
            
            grouped_runs[scheduled_time_key]['runs'].append({
                'id': run.id,
                'start_time': ensure_utc(run.start_time).isoformat(),
                'end_time': ensure_utc(run.end_time).isoformat() if run.end_time else None,
                'status': run.status,
                'duration': run.duration,
                'log_file': run.log_file
            })
    
    # Convert to list and sort by scheduled time
    result = list(grouped_runs.values())
    result.sort(key=lambda x: x['scheduled_time'])
    
    return jsonify(result)

@bp.route('/tasks/<int:task_id>/run-status', methods=['GET'])
@login_required
def get_task_run_status(task_id):
    Task.query.get_or_404(task_id)  # Verify task exists
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Get all runs for the task within the date range
    query = TaskRun.query.filter(TaskRun.task_id == task_id)
    
    if start_date and end_date:
        query = query.filter(
            db.func.date(TaskRun.start_time).between(
                datetime.fromisoformat(start_date).date(),
                datetime.fromisoformat(end_date).date()
            )
        )
    
    runs = query.order_by(TaskRun.start_time).all()
    
    # Group runs by date and scheduled time (hour:minute)
    from collections import defaultdict
    daily_runs = defaultdict(lambda: defaultdict(list))
    
    for run in runs:
        date_str = run.start_time.strftime('%Y-%m-%d')
        # Group by scheduled time (hour:minute) to identify reruns
        time_key = run.start_time.strftime('%H:%M')
        daily_runs[date_str][time_key].append(run)
    
    # Determine status for each date
    date_statuses = {}
    
    for date_str, time_groups in daily_runs.items():
        all_time_slots_resolved = True
        has_any_runs = False
        
        for time_key, time_runs in time_groups.items():
            has_any_runs = True
            # Sort runs by start_time to get chronological order
            time_runs.sort(key=lambda r: r.start_time)
            
            # Check if this time slot is resolved (no unresolved failures)
            time_slot_resolved = True
            
            for run in time_runs:
                if run.status == 'failure':
                    # Check if there's a newer successful run after this failure
                    has_later_success = any(
                        later_run.status == 'success' and later_run.start_time > run.start_time
                        for later_run in time_runs
                    )
                    if not has_later_success:
                        time_slot_resolved = False
                        break
                elif run.status in ['running', 'pending']:
                    # Consider running/pending as unresolved for now
                    time_slot_resolved = False
            
            if not time_slot_resolved:
                all_time_slots_resolved = False
                break
        
        if not has_any_runs:
            # No runs for this date - don't include in results
            continue
        elif all_time_slots_resolved:
            date_statuses[date_str] = {'status': 'success'}
        else:
            date_statuses[date_str] = {'status': 'failure'}
    
    return jsonify(date_statuses)

@bp.route('/tasks/runs/<int:run_id>/log', methods=['GET'])
@login_required
def get_run_log(run_id):
    run = TaskRun.query.get_or_404(run_id)
    if not run.log_file or not os.path.exists(run.log_file):
        return jsonify({'error': 'Log file not found'}), 404
    
    try:
        with open(run.log_file, 'r') as f:
            content = f.read()
        return jsonify({'content': content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def run_task(task, test_mode=False, scheduled_time=None):
    # Use scheduled_time for the script but track actual execution time for duration
    execution_start = datetime.utcnow()
    script_time = scheduled_time if scheduled_time else execution_start
    
    # Log file format: task_{task_id}_{scheduled_time}_{execution_time}
    scheduled_str = script_time.strftime("%Y%m%d_%H%M%S")
    execution_str = execution_start.strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(current_app.config['LOGS_FOLDER'],
        f'task_{task.id}_{scheduled_str}_{execution_str}.log')
    
    cmd = ['python', os.path.join(current_app.config['SCRIPTS_FOLDER'], task.script_path)]
    cmd.append(script_time.isoformat())
    if task.extra_args:
        cmd.extend(task.extra_args.split())
    
    try:
        if test_mode:
            # For test mode, capture output but also write to log file
            with open(log_file, 'w') as f:
                process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                output = process.stdout if process.returncode == 0 else process.stderr
                f.write(output)
                success = process.returncode == 0
        else:
            # For normal mode, write directly to log file
            with open(log_file, 'w') as f:
                process = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
                success = process.returncode == 0
                output = ''
        
        status = 'success' if success else 'failure'
    except Exception as e:
        status = 'failure'
        output = str(e)
        with open(log_file, 'w') as f:
            f.write(output)
    
    execution_end = datetime.utcnow()
    duration = (execution_end - execution_start).total_seconds()
    
    return {
        'status': status,
        'output': output if test_mode else '',
        'duration': duration,
        'log_file': log_file
    }

def schedule_task(task):
    job_id = f'task_{task.id}'
    current_app.scheduler.add_job(
        'app.task_executor:execute_task',
        'cron',
        args=[task.id],
        id=job_id,
        replace_existing=True,
        start_date=task.start_date,
        end_date=task.end_date,
        **parse_cron_schedule(task.cron_schedule)
    )

def unschedule_task(task):
    try:
        job_id = f'task_{task.id}'
        current_app.scheduler.remove_job(job_id)
    except Exception as e:
        # Log the error but don't raise it, as the job may not exist
        current_app.logger.info(f'Could not unschedule task {task.id}: {e}')

def reschedule_task(task):
    if task.is_active:
        schedule_task(task)

def parse_cron_schedule(cron_str):
    minute, hour, day, month, day_of_week = cron_str.split()
    return {
        'minute': minute,
        'hour': hour,
        'day': day,
        'month': month,
        'day_of_week': day_of_week
    }

def get_last_run_status(task):
    last_run = TaskRun.query.filter_by(task_id=task.id).order_by(TaskRun.start_time.desc()).first()
    if not last_run:
        return None
    return {
        'status': last_run.status,
        'time': last_run.start_time.isoformat()
    }

def calculate_next_run(task):
    job_id = f'task_{task.id}'
    job = current_app.scheduler.get_job(job_id)
    return job.next_run_time.isoformat() if job and job.next_run_time else None

def execute_single_run(app, task_id, run_id):
    """Execute a single backfill run and return True if successful."""
    try:
        with app.app_context():
            # Get fresh objects in this thread's session
            task = Task.query.get(task_id)
            run = TaskRun.query.get(run_id)
            if not task or not run:
                return False
            
            result = run_task(task, scheduled_time=run.start_time)
            
            # Update run status in same session
            run.status = result.get('status', 'failure')
            run.end_time = datetime.utcnow()
            run.duration = result.get('duration', 0)
            run.log_file = result.get('log_file')
            db.session.commit()
            
            return run.status == 'success'
    except Exception as e:
        with app.app_context():
            current_app.logger.error(f'Error executing backfill run {run_id}: {e}')
            run = TaskRun.query.get(run_id)
            if run:
                run.status = 'failure'
                run.end_time = datetime.utcnow()
                run.duration = 0
                db.session.commit()
            return False

@bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    try:
        # First unschedule the task
        unschedule_task(task)
        
        # Delete all associated run log files
        runs = TaskRun.query.filter_by(task_id=task_id).all()
        for run in runs:
            if run.log_file and os.path.exists(run.log_file):
                try:
                    os.remove(run.log_file)
                except Exception as e:
                    current_app.logger.warning(f'Failed to delete log file {run.log_file}: {e}')
        
        # Then delete all associated runs
        TaskRun.query.filter_by(task_id=task_id).delete()
        
        # Finally delete the task
        db.session.delete(task)
        db.session.commit()
        
        return jsonify({'message': 'Task deleted successfully'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting task {task_id}: {e}')
        return jsonify({'error': 'Failed to delete task'}), 500

@bp.route('/tasks/<int:task_id>/backfill', methods=['POST'])
@login_required
def backfill_task(task_id):
    try:
        data = request.json
        app = current_app._get_current_object()
        
        # Get configuration with bounds checking
        max_concurrent_runs = max(1, min(10, data.get('max_concurrent_runs', 3)))
        batch_size = max(1, min(20, data.get('batch_size', 5)))
        
        task = Task.query.get_or_404(task_id)
        
        # Parse times and ensure they are UTC timezone-aware
        if 'start_time' not in data or 'end_time' not in data:
            current_app.logger.error('Missing start_time or end_time in request')
            return jsonify({'error': 'start_time and end_time are required'}), 400
            
        start_time = ensure_utc(datetime.fromisoformat(data['start_time']))
        end_time = ensure_utc(datetime.fromisoformat(data['end_time']))
    except ValueError as e:
        current_app.logger.error(f'Error parsing dates: {e}')
        return jsonify({'error': f'Invalid date format: {e}'}), 400
    except Exception as e:
        current_app.logger.error(f'Unexpected error in backfill setup: {e}')
        return jsonify({'error': str(e)}), 500
    
    # Add UTC timezone if times are naive
    if start_time.tzinfo is None:
        start_time = pytz.UTC.localize(start_time)
    if end_time.tzinfo is None:
        end_time = pytz.UTC.localize(end_time)
    
    # Validate time range
    if start_time >= end_time:
        return jsonify({'error': 'Start time must be before end time'}), 400
    
    # Get all scheduled times in the range
    cron_params = parse_cron_schedule(task.cron_schedule)
    cron_params['timezone'] = pytz.UTC  # Ensure CronTrigger uses UTC
    trigger = CronTrigger(**cron_params)
    
    scheduled_times = []
    current_time = start_time
    while current_time <= end_time:
        next_time = trigger.get_next_fire_time(None, current_time)
        if next_time is None or next_time > end_time:
            break
        scheduled_times.append(next_time)
        current_time = next_time + timedelta(seconds=1)
    
    # Create task runs for each time
    runs_created = 0
    pending_run_ids = []
    for run_time in scheduled_times:
        # Ensure run_time is timezone-aware
        if run_time.tzinfo is None:
            run_time = pytz.UTC.localize(run_time)
            
        # Skip if we already have a run at this time
        existing_run = TaskRun.query.filter(
            TaskRun.task_id == task_id,
            TaskRun.start_time == run_time
        ).first()
        
        if not existing_run:
            run = TaskRun(
                task_id=task_id,
                start_time=run_time,
                status='pending'
            )
            db.session.add(run)
            db.session.flush()  # Get the ID before commit
            pending_run_ids.append(run.id)
            runs_created += 1
    
    # Commit all runs before starting execution
    db.session.commit()
    
    # Use the pending runs we just created
    # This ensures we have access to them immediately
    
    # Store backfill state
    task.backfill_start_time = start_time
    task.backfill_end_time = end_time
    task.backfill_max_concurrent = max_concurrent_runs
    task.backfill_batch_size = batch_size
    task.backfill_total_runs = len(pending_run_ids)
    task.backfill_completed_runs = 0
    task.backfill_successful_runs = 0
    task.backfill_status = 'running'
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f'Error storing initial backfill state: {e}')
        db.session.rollback()
        raise
    
    def process_batch(batch_ids, processed_runs, successful_runs):
        futures = []
        with ThreadPoolExecutor(max_workers=max_concurrent_runs) as executor:
            # Submit all runs
            for run_id in batch_ids:
                futures.append(executor.submit(execute_single_run, app, task.id, run_id))
            
            # Process results
            for future in as_completed(futures):
                try:
                    if future.result():
                        successful_runs += 1
                    processed_runs += 1
                    
                    # Update progress after each run
                    with app.app_context():
                        current_task = Task.query.get(task.id)
                        if current_task:
                            current_task.backfill_completed_runs = processed_runs
                            current_task.backfill_successful_runs = successful_runs
                            db.session.commit()
                except Exception as e:
                    with app.app_context():
                        current_app.logger.error(f'Error processing batch result: {e}')
        
        return processed_runs, successful_runs
    
    def run_backfill():
        total_runs = len(pending_run_ids)
        processed_runs = 0
        successful_runs = 0
        
        try:
            # Process runs in batches
            for i in range(0, total_runs, batch_size):
                # Check if we should continue
                with app.app_context():
                    current_task = Task.query.get(task.id)
                    if not current_task or current_task.backfill_status != 'running':
                        break
                    
                    # Get the next batch
                    batch_ids = pending_run_ids[i:i + batch_size]
                
                # Process the batch
                new_processed, new_successful = process_batch(
                    batch_ids, processed_runs, successful_runs
                )
                processed_runs = new_processed
                successful_runs = new_successful
            
            # Mark as completed
            with app.app_context():
                current_task = Task.query.get(task.id)
                if current_task:
                    current_task.backfill_status = 'completed'
                    db.session.commit()
                    current_app.logger.info(f'Backfill completed: {successful_runs}/{total_runs} successful')
        except Exception as e:
            with app.app_context():
                current_app.logger.error(f'Error in backfill process: {e}')
                current_task = Task.query.get(task.id)
                if current_task:
                    current_task.backfill_status = 'failed'
                    db.session.commit()
    
    # Start the backfill process
    thread = threading.Thread(target=run_backfill)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'message': f'Backfill started with {runs_created} runs',
        'runs_created': runs_created,
        'backfill_status': task.backfill_status
    })

@bp.route('/tasks/<int:task_id>/backfill/status', methods=['GET'])
@login_required
def get_backfill_status(task_id):
    task = Task.query.get_or_404(task_id)
    if not task.backfill_status:
        return jsonify({
            'status': None
        })
    
    return jsonify({
        'status': task.backfill_status,
        'start_time': task.backfill_start_time.isoformat() if task.backfill_start_time else None,
        'end_time': task.backfill_end_time.isoformat() if task.backfill_end_time else None,
        'max_concurrent_runs': task.backfill_max_concurrent,
        'batch_size': task.backfill_batch_size,
        'total_runs': task.backfill_total_runs,
        'completed_runs': task.backfill_completed_runs,
        'successful_runs': task.backfill_successful_runs,
        'progress': int((task.backfill_completed_runs / task.backfill_total_runs * 100) if task.backfill_total_runs else 0)
    })
