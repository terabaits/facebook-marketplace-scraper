"""Load test for the /healthz endpoint.

Fires 50 concurrent requests at http://localhost:5000/healthz using only
stdlib (threading + urllib.request) and prints a summary.
"""
import threading
import time
import urllib.request
from urllib.error import URLError, HTTPError

URL = 'http://localhost:5000/healthz'
TOTAL = 50

results = {'success': 0, 'failure': 0}
lock = threading.Lock()
max_concurrent = {'value': 0}
active = {'value': 0}


def worker():
    with lock:
        active['value'] += 1
        if active['value'] > max_concurrent['value']:
            max_concurrent['value'] = active['value']

    try:
        with urllib.request.urlopen(URL, timeout=30) as response:
            body = response.read().decode('utf-8')
            if response.status == 200 and '"status": "ok"' in body:
                with lock:
                    results['success'] += 1
            else:
                with lock:
                    results['failure'] += 1
                print(f'Unexpected response: {response.status} {body}')
    except HTTPError as e:
        with lock:
            results['failure'] += 1
        body = e.read().decode('utf-8', errors='replace')[:200]
        print(f'HTTP error: {e.code} {e.reason} {body}')
    except URLError as e:
        with lock:
            results['failure'] += 1
        print(f'URL error: {e.reason}')
    except Exception as e:
        with lock:
            results['failure'] += 1
        print(f'Exception: {e}')
    finally:
        with lock:
            active['value'] -= 1


def main():
    start = time.time()
    threads = [threading.Thread(target=worker) for _ in range(TOTAL)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.time() - start

    print(f'Total requests : {TOTAL}')
    print(f'Successes      : {results["success"]}')
    print(f'Failures       : {results["failure"]}')
    print(f'Elapsed time   : {elapsed:.2f}s')
    print(f'Max concurrent : {max_concurrent["value"]}')

    if results['failure'] == 0:
        print('\nAll requests succeeded - pool survived the load.')
    else:
        print(f'\n{results["failure"]} request(s) failed.')


if __name__ == '__main__':
    main()
