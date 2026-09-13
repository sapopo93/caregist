"""Check ODS parsing tooling in the CareGist venv. Read-only."""
import importlib

for mod in ["odf", "pandas", "pyexcel_ods", "ezodf"]:
    try:
        importlib.import_module(mod)
        print(mod, "OK")
    except Exception as e:
        print(mod, "MISSING:", type(e).__name__)
