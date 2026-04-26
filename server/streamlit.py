"""Stub module to avoid optional Streamlit import failures in some setups.

This environment is served via FastAPI/Uvicorn. If an external/legacy `app.py`
on `PYTHONPATH` tries to import Streamlit, we prefer a harmless stub over a hard
crash during test collection.
"""

def __getattr__(name):  # pragma: no cover
    raise AttributeError(name)

