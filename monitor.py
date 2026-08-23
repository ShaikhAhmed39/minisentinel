import time
from datetime import datetime
from core import get_system_stats, check_and_heal

CHECK_INTERVAL = 10

if __name__ == "__main__":
    print(f"Starting MiniSentinel monitor (checking every {CHECK_INTERVAL}s)...\n")
    try:
        while True:
            stats = get_system_stats()
            print(f"--- {datetime.now().strftime('%H:%M:%S')} ---")
            print(f"CPU: {stats['cpu_percent']}%  MEM: {stats['memory_percent']}%  DISK: {stats['disk_percent']}%")
            check_and_heal("test-app")
            print()
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
