import subprocess
import os
from datetime import datetime

# Store Flask app reference
flask_app = None

def init_executor(app):
    global flask_app
    flask_app = app

def execute_task(task_id):
    """Execute a task by its ID. This function is serializable and can be stored by APScheduler."""
    global flask_app
    if not flask_app:
        raise RuntimeError("Flask app not initialized in task executor")

    with flask_app.app_context():
        from .models.models import TaskRun, db
        from .routes.task_routes import Task  # Import here to avoid circular imports
        
        task = Task.query.get(task_id)
        if not task:
            return
        
        start_time = datetime.utcnow()
        log_file = os.path.join(flask_app.config['LOGS_FOLDER'],
            f'task_{task.id}_{start_time.strftime("%Y%m%d_%H%M%S")}.log')
        
        run = TaskRun(
            task_id=task.id,
            start_time=start_time,
            status='running',
            log_file=log_file
        )
        db.session.add(run)
        db.session.commit()
        
        cmd = ['python', os.path.join(flask_app.config['SCRIPTS_FOLDER'], task.script_path)]
        cmd.append(start_time.isoformat())
        if task.extra_args:
            cmd.extend(task.extra_args.split())
        
        try:
            with open(log_file, 'w') as f:
                process = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
                success = process.returncode == 0
            
            status = 'success' if success else 'failure'
        except Exception as e:
            status = 'failure'
            with open(log_file, 'w') as f:
                f.write(str(e))
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        run.status = status
        run.end_time = end_time
        run.duration = duration
        db.session.commit()
        
        return {
            'status': status,
            'duration': duration
        }
    
    run = TaskRun(
        task_id=task.id,
        start_time=start_time,
        status='running',
        log_file=log_file
    )
    db.session.add(run)
    db.session.commit()
    
    cmd = ['python', os.path.join(flask_app.config['SCRIPTS_FOLDER'], task.script_path)]
    cmd.append(start_time.isoformat())
    if task.extra_args:
        cmd.extend(task.extra_args.split())
    
    try:
        with open(log_file, 'w') as f:
            process = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
            success = process.returncode == 0
        
        status = 'success' if success else 'failure'
    except Exception as e:
        status = 'failure'
        with open(log_file, 'w') as f:
            f.write(str(e))
    
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    run.status = status
    run.end_time = end_time
    run.duration = duration
    db.session.commit()
    
    return {
        'status': status,
        'duration': duration
    }
