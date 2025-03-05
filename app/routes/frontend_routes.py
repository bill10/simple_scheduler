from flask import Blueprint, render_template, abort, jsonify
import os

bp = Blueprint('frontend', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/tasks/new')
def new_task():
    return render_template('task_form.html')

@bp.route('/tasks/<int:task_id>')
def task_detail(task_id):
    return render_template('task_detail.html')

@bp.route('/tasks/<int:task_id>/edit')
def edit_task(task_id):
    return render_template('task_form.html')

@bp.route('/api/scripts')
def list_scripts():
    """List all available Python scripts in the scripts directory."""
    scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'scripts')
    scripts = []
    if os.path.exists(scripts_dir):
        for file in os.listdir(scripts_dir):
            if file.endswith('.py'):
                scripts.append(file)
    return jsonify(scripts)
