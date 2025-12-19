Contributing to x402-Notify
===========================

Thanks for helping improve this project. This short guide explains how to run tests, make changes, and submit a pull request.

Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r sdk/python/requirements-dev.txt || true
pip install -e sdk/python
```

Run tests

```bash
pytest -q
```

Formatting

- Use `ruff`/`black` for Python formatting if configured in the repo; run formatters before committing.

Submitting changes

1. Fork the repo and create a branch for your change.
2. Keep changes focused and include tests for new behavior.
3. Push your branch and open a pull request with a clear description.

Support

If you need help, open an issue describing the problem and include reproduction steps.
