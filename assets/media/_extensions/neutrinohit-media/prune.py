#!/usr/bin/env python3
"""Post-render script: delete the local copies of films that the media projects serve."""
import subprocess
import sys
from pathlib import Path

sys.exit(subprocess.run([sys.executable, str(Path(__file__).with_name("media.py")), "prune"]).returncode)
