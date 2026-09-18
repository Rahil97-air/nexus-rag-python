"""Public, sample-only deployment entry point. Full local app: app.py."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name("app.py")),
              init_globals={"PUBLIC_DEMO": True}, run_name="__main__")
