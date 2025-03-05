from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    script_path = db.Column(db.String(255), nullable=False)
    cron_schedule = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    extra_args = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    runs = db.relationship('TaskRun', backref='task', lazy=True, cascade='all, delete-orphan')
    
    # Backfill state
    backfill_start_time = db.Column(db.DateTime)
    backfill_end_time = db.Column(db.DateTime)
    backfill_max_concurrent = db.Column(db.Integer)
    backfill_batch_size = db.Column(db.Integer)
    backfill_total_runs = db.Column(db.Integer)
    backfill_completed_runs = db.Column(db.Integer)
    backfill_successful_runs = db.Column(db.Integer)
    backfill_status = db.Column(db.String(20))  # 'running', 'completed', 'failed', or None

class TaskRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False)  # 'success', 'failure', 'running'
    duration = db.Column(db.Float)  # in seconds
    log_file = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
