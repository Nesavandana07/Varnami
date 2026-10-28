# Claude Code instructions

## Project layout

The CARNA-AI Flask application is in `VARNAMI DATASETS/carna_ai/carna_ai/`.
Its Python package is `carna/`, its dashboard is in `static/`, and its tests
are in `tests/`. The repository root also contains Python modules; do not assume
they are the active Flask application.

## Development commands

Run these from `VARNAMI DATASETS/carna_ai/carna_ai/`:

```powershell
python -m pip install -r requirements.txt
python -m pytest tests
python app.py
```

The Flask app listens on `http://127.0.0.1:5000`. The first run may train a
bootstrap model.

## Project constraints

- Preserve the distinction between synthetic test results and real-audio
  validation. Consult the project README before making claims about model
  accuracy or changing data-dependent behavior.
- Raga knowledge and expert-verified musical details are data-sensitive;
  do not invent or mark scales, prayogas, gamakas, or film-song annotations as
  expert-verified.
- Prefer focused tests in `tests/` for changes to the CARNA-AI application.
- Avoid changing generated model files, cached files, or dataset archives
  unless the task specifically requires it.
