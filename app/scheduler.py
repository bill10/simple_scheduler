from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

scheduler = None

def init_scheduler(app):
    global scheduler
    if scheduler is None:
        jobstores = {
            'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
        }
        scheduler = BackgroundScheduler(jobstores=jobstores)
        
        # Add Flask app context to scheduler
        def job_listener(event):
            if hasattr(event, 'exception') and event.exception:
                print(f'Job failed: {event.job_id}')
                print(f'Exception: {event.exception}')
                print(f'Traceback: {event.traceback}')
        
        scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        
        scheduler.start()
    
    return scheduler
