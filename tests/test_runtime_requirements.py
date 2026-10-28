"""Guard the lean dependency set Vercel installs for the API on every cold start.

On 27 Oct 2026 the old requirements.txt (pipeline, tooling and test packages as
well as the API's own) filled the function's small /tmp during `uv sync`, so
/api/v1/health intermittently returned 500 "No space left on device".
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]

# Import name -> distribution name, where they differ.
DISTRIBUTION = {"jwt": "pyjwt", "dotenv": "python-dotenv"}
# Pulled in by another runtime requirement, or imported only behind a guard.
PROVIDED_OR_GUARDED = {
    "pydantic": "fastapi",
    "starlette": "fastapi",
    "dotenv": "uvicorn",
    "boto3": "guarded",
}
HEAVY_AND_UNUSED_BY_THE_API = {
    "pandas", "numpy", "tqdm", "python-slugify", "validators",
    "psycopg2-binary", "requests", "vercel", "pytest", "pytest-asyncio", "pytest-cov",
}


def _requirement_names(path: Path) -> set[str]:
    names = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line and not line.startswith("-"):
            names.add(re.split(r"[<>=!\[ ;]", line)[0].lower().replace("_", "-"))
    return names


def _third_party_imports_reachable_from_api() -> set[str]:
    local = {"api", "tools", "db"}
    seen: set[Path] = set()
    third: set[str] = set()

    def module_file(name: str) -> Path | None:
        parts = name.split(".")
        for end in range(len(parts), 0, -1):
            base = ROOT.joinpath(*parts[:end])
            if base.with_suffix(".py").exists():
                return base.with_suffix(".py")
            if (base / "__init__.py").exists():
                return base / "__init__.py"
        return None

    def visit(name: str) -> None:
        path = module_file(name)
        if path is None or path in seen:
            return
        seen.add(path)
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            imported: list[str] = []
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported = [node.module, *(f"{node.module}.{a.name}" for a in node.names)]
            elif (
                isinstance(node, ast.Call)
                and getattr(node.func, "id", getattr(node.func, "attr", "")) == "import_module"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                imported = [str(node.args[0].value)]
            for dotted in imported:
                top = dotted.split(".")[0]
                if top in local:
                    visit(dotted)
                elif top not in sys.stdlib_module_names:
                    third.add(top)

    visit("api.main")
    visit("tools.run_new_registration_feed_cycle")
    return third


def test_runtime_requirements_exclude_pipeline_and_test_packages():
    runtime = _requirement_names(ROOT / "requirements.txt")

    assert not runtime & HEAVY_AND_UNUSED_BY_THE_API, (
        "These belong in requirements-pipeline.txt, not the Vercel runtime set: "
        f"{sorted(runtime & HEAVY_AND_UNUSED_BY_THE_API)}"
    )


def test_runtime_requirements_cover_what_the_api_imports():
    runtime = _requirement_names(ROOT / "requirements.txt")
    missing = {
        name
        for name in _third_party_imports_reachable_from_api()
        if name not in PROVIDED_OR_GUARDED
        and DISTRIBUTION.get(name, name).lower().replace("_", "-") not in runtime
    }

    assert not missing, f"The API imports packages requirements.txt does not install: {sorted(missing)}"


def test_pipeline_requirements_extend_the_runtime_set():
    text = (ROOT / "requirements-pipeline.txt").read_text(encoding="utf-8")

    assert "-r requirements.txt" in text
    assert HEAVY_AND_UNUSED_BY_THE_API <= _requirement_names(ROOT / "requirements-pipeline.txt")
