import os
from flask import Blueprint, render_template, request, redirect, url_for, session
from functools import wraps
from dotenv import load_dotenv

bp = Blueprint('auth', __name__)

# Load environment variables
load_dotenv()

# Get credentials from environment variables
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.clear()
            session['user_id'] = username
            session['is_authenticated'] = True
            
            # Redirect to the next page or home
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('frontend.index'))
        else:
            error = 'Invalid username or password'
    
    return render_template('login.html', error=error)

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
