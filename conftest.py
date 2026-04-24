"""pytest configuration: add repo root to sys.path so all project.* imports resolve."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
