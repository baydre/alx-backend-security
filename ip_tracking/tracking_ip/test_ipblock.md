# How to test this:
1. Run your Django development server: `python manage.py runserver`

2. In a separate terminal, block your own IP (or a test IP if you have one):
```Bash
python manage.py block_ip 127.0.0.1
```
*(Replace 127.0.0.1 with your actual public IP if testing from an external machine, or ::1 for IPv6 localhost).*

3. Try to access your Django application in the browser. You should now see the *"You are blocked." 403 Forbidden message.*

4. You can unblock an IP by deleting it from the Django Admin or directly via shell:
```Bash
python manage.py shell
from ip_tracking.models import BlockedIP
BlockedIP.objects.filter(ip_address='127.0.0.1').delete()
exit()
```
