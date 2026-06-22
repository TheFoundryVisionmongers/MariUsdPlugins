"""Smoke tests for importing Mari USD plugin Python modules."""

import importlib
import importlib.util
import pathlib
import sys
import types


def test_import_usd_shader_module_without_mari_runtime(monkeypatch):
    """Import ``python.usdShader`` with a minimal ``mari`` stub present."""

    mari_stub = types.SimpleNamespace(
        app=types.SimpleNamespace(isRunning=lambda: False)
    )

    monkeypatch.setitem(sys.modules, "mari", mari_stub)

    module_path = pathlib.Path(__file__).resolve().parents[1] / "python" / "usdShader.py"
    spec = importlib.util.spec_from_file_location("_smoke_usdShader", module_path)
    imported = importlib.util.module_from_spec(spec)

    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(imported)

    assert imported is not None
