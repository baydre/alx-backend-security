# How to run Celery and test:
1. Start Redis server: `sudo service redis-server start` (if not already running).

2. Start Celery Worker: In a separate terminal, navigate to your project's root directory (where manage.py is) and run:

```Bash

celery -A your_project_name worker -l info -P gevent # Or eventlet, or solo for simple testing
```

Replace `your_project_name` with your actual project name. `gevent` or `eventlet` are good for I/O-bound tasks. `solo` is for single-threaded testing.

3. Start Celery Beat (Scheduler): In another separate terminal, run:

```Bash

celery -A your_project_name beat -l info
```
This will start the scheduler that periodically calls your detect_anomalies task based on CELERY_BEAT_SCHEDULE.

4. Run Django Server: `python manage.py runserver`

5. Generate traffic: Access your Django application repeatedly from various IPs (if possible, or just your own) to create `RequestLog` entries. Access sensitive paths like `/admin/` repeatedly.

6. Check `SuspiciousIP` model: After an hour (or your test `timedelta` for `CELERY_BEAT_SCHEDULE`), check your database (e.g., via Django Admin or `python manage.py shell`) to see if any IPs have been flagged in the `SuspiciousIP` table. You can manually call the task from the Django shell for immediate testing:

```Bash

python manage.py shell
from ip_tracking.tasks import detect_anomalies
detect_anomalies.delay() # To run asynchronously
# OR
detect_anomalies() # To run synchronously (for immediate testing in shell)
exit()
```