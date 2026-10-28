#!/usr/bin/env python3
"""CARNA-AI / VARNAMI root application runner and proxy."""
import sys, os, importlib.util
from pathlib import Path

carna_dir = Path(__file__).resolve().parent / "VARNAMI DATASETS" / "carna_ai" / "carna_ai"
app_file = carna_dir / "app.py"

if not carna_dir.exists() or not app_file.exists():
    raise FileNotFoundError(f"CARNA-AI app not found at {carna_dir}")

sys.path.insert(0, str(carna_dir))
os.chdir(str(carna_dir))

spec = importlib.util.spec_from_file_location("carna_ai_app", str(app_file))
carna_module = importlib.util.module_from_spec(spec)
sys.modules["carna_ai_app"] = carna_module
spec.loader.exec_module(carna_module)

app = carna_module.app
_enc = carna_module._enc

if __name__ == "__main__":
    from carna import classify
    try:
        classify.load_model()
    except Exception as e:
        print(f"Model bootstrap note: {e}")
    port = int(os.environ.get("PORT", 5000))
    print(f"VARNAMI (CARNA-AI) running at http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
