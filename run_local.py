"""
run_local.py — Single-command localhost launcher
=================================================
Run this from the stock-trading-system/ directory:

    python run_local.py

What it does:
  1. Generates mock pipeline data (no API key needed)
  2. Launches the Streamlit dashboard at http://localhost:8501
  3. Prints a checklist of next steps for live/production use

For a live run (needs MELLEA_BACKEND + API key in .env):
    python run_local.py --live
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

parser = argparse.ArgumentParser(description="Launch dashboard locally")
parser.add_argument("--live", action="store_true",
                    help="Run live pipeline instead of mock data")
parser.add_argument("--skip-pipeline", action="store_true",
                    help="Skip pipeline run, use existing data/pipeline_output.json")
args = parser.parse_args()

# ── Step 1: Install dependencies if needed ────────────────────────────────────
print("=" * 60)
print("  Stock Trading System — Localhost Launcher")
print("=" * 60)

req_file = BASE_DIR / "requirements.txt"
print(f"\n[1/3] Checking dependencies from {req_file.name}...")
result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"],
    cwd=str(BASE_DIR)
)
if result.returncode != 0:
    print("  ⚠  pip install had warnings — continuing anyway")
else:
    print("  ✓  Dependencies OK")

# ── Step 2: Generate pipeline data ────────────────────────────────────────────
if not args.skip_pipeline:
    print("\n[2/3] Generating pipeline data...")
    output_path = BASE_DIR / "data" / "pipeline_output.json"

    if args.live:
        # Check for .env file
        env_file = BASE_DIR / ".env"
        if not env_file.exists():
            print("  ⚠  No .env file found. Copy .env.example → .env and add your API key.")
            print("     Falling back to --mock mode.")
            pipeline_args = ["--mock"]
        else:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            print(f"  Loaded .env — backend: {os.getenv('MELLEA_BACKEND','not set')}")
            pipeline_args = []
    else:
        pipeline_args = ["--mock"]

    mode_label = "LIVE" if args.live and not pipeline_args else "MOCK"
    print(f"  Running daily_pipeline.py ({mode_label})...")
    result = subprocess.run(
        [sys.executable, "daily_pipeline.py"] + pipeline_args +
        ["--output", str(output_path)],
        cwd=str(BASE_DIR)
    )
    if result.returncode != 0:
        print("  ✗  Pipeline failed — dashboard will show 'no data' banner")
    else:
        print(f"  ✓  Pipeline output → {output_path}")
else:
    print("\n[2/3] Skipping pipeline (--skip-pipeline flag set)")

# ── Step 3: Launch Streamlit ──────────────────────────────────────────────────
print("\n[3/3] Launching Streamlit dashboard...")
print("\n" + "=" * 60)
print("  ✓  Dashboard running at:  http://localhost:8501")
print("  ✓  Press Ctrl+C to stop")
print("=" * 60)

print("\nNext steps for live/production use:")
print("  1. Install Ollama (https://ollama.com) and run: ollama pull llama3")
print("     (or copy .env.example → .env and set MELLEA_BACKEND=openai + OPENAI_API_KEY)")
print("  2. Run:  python run_local.py --live")
print("  3. Push to GitHub → connect Railway Pro → deploy")
print()

subprocess.run(
    [sys.executable, "-m", "streamlit", "run",
     str(BASE_DIR / "dashboard" / "app.py"),
     "--server.port", "8501",
     "--server.address", "localhost"],
    cwd=str(BASE_DIR)
)

# Made with Bob
