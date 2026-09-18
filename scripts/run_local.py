"""Start both local services; stop only processes started by this launcher."""
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def occupied(port):
    with socket.socket() as sock:
        sock.settimeout(1)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def main():
    children = []
    services = [
        (8000, [sys.executable, "-m", "uvicorn", "nexus_rag.api:app", "--host", "127.0.0.1", "--port", "8000", "--no-access-log"]),
        (8501, [sys.executable, "-m", "streamlit", "run", "app.py"]),
    ]
    try:
        for port, command in services:
            if occupied(port):
                print(f"Port {port} is already in use; leaving its existing process untouched.")
                continue
            children.append(subprocess.Popen(command, cwd=ROOT,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0))
        print("App: http://127.0.0.1:8501\nAPI docs: http://127.0.0.1:8000/docs")
        print("Keep this window open. Ctrl+C stops only services started by this launcher.")
        while children:
            for child in children:
                if child.poll() is not None:
                    raise RuntimeError(f"A service exited with code {child.returncode}. See its error above.")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping local services…")
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()


if __name__ == "__main__":
    main()
