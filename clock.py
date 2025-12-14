from mailer.mailer import generate_today_cache, send_cached_for_today
import datetime
import time

tasks = [
    ((6, 0, 0), generate_today_cache),
    ((8, 0, 0), send_cached_for_today),
]

while True:
    for (hh, mm, ss), task in tasks:
        now = datetime.datetime.now()
        if now.hour * 3600 + now.minute * 60 + now.second < hh * 3600 + mm * 60 + ss:
            target = now.replace(hour=hh, minute=mm, second=ss, microsecond=0)
            delta = (target - now).total_seconds()
            print(
                f"Sleeping for {delta} seconds until {hh:02}:{mm:02}:{ss:02} to run {task.__name__}"
            )
            time.sleep(delta)
            print(f"Running task {task.__name__} at {datetime.datetime.now()}")
            task()
    # wait for next day
    now = datetime.datetime.now()
    target = now.replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + datetime.timedelta(days=1)
    delta = (target - now).total_seconds()
    print(f"Sleeping for {delta} seconds until midnight for next day's tasks")
    time.sleep(delta)
