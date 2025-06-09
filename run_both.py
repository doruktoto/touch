import subprocess
import sys
import signal

# Start both scripts as subprocesses
procs = []
try:
    procs.append(subprocess.Popen([sys.executable, '7-key.py']))
    procs.append(subprocess.Popen([sys.executable, 'pinch_cc3.py']))
    print("Both 7-key.py and pinch_cc3.py are running. Press Ctrl+C to stop.")
    # Wait for both to finish (they won't, unless error or killed)
    for p in procs:
        p.wait()
except KeyboardInterrupt:
    print("\nKeyboardInterrupt received. Terminating both processes...")
    for p in procs:
        p.terminate()
    for p in procs:
        p.wait()
    print("Both processes terminated.") 