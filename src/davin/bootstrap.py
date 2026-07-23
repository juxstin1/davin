"""Locate Resolve's scripting module and attach to the running app."""

from __future__ import annotations

import importlib.util
import os
import sys

RESOLVE_APP_DIR = r"C:\Program Files\Blackmagic Design\DaVinci Resolve"
SCRIPT_MODULE = os.path.join(
    os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
    "Blackmagic Design",
    "DaVinci Resolve",
    "Support",
    "Developer",
    "Scripting",
    "Modules",
    "DaVinciResolveScript.py",
)

NOT_RUNNING_HINT = (
    "Could not attach to DaVinci Resolve. Checklist:\n"
    "  1. Resolve is running (fully loaded, past the splash screen)\n"
    "  2. Preferences > System > General > 'External scripting using' is set to Local\n"
    "  3. You are on Studio (the free edition does not allow external scripting)"
)


class ResolveConnectionError(RuntimeError):
    pass


def _import_script_module():
    """Import DaVinciResolveScript, falling back to Resolve's install path."""
    try:
        import DaVinciResolveScript as dvr  # user may have PYTHONPATH set up

        return dvr
    except ImportError:
        pass

    module_path = os.environ.get("DAVIN_SCRIPT_MODULE", SCRIPT_MODULE)
    if not os.path.isfile(module_path):
        raise ResolveConnectionError(
            f"DaVinciResolveScript.py not found at {module_path} - "
            "is DaVinci Resolve installed?"
        )
    if os.name == "nt" and os.path.isdir(RESOLVE_APP_DIR):
        os.add_dll_directory(RESOLVE_APP_DIR)

    spec = importlib.util.spec_from_file_location("DaVinciResolveScript", module_path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ImportError as exc:
        raise ResolveConnectionError(
            f"Failed to load fusionscript via {module_path}: {exc}"
        ) from exc
    # The shim swaps itself out for the fusionscript extension module.
    return sys.modules.get("DaVinciResolveScript", module)


def get_resolve():
    """Return a live, verified Resolve app object, or raise ResolveConnectionError.

    scriptapp() can hand back a proxy into a Resolve process that has since
    quit or restarted; the liveness call makes that fail loudly here instead
    of surfacing as a confusing None deep inside a workflow.
    """
    dvr = _import_script_module()
    app = dvr.scriptapp("Resolve")
    if app is None:
        raise ResolveConnectionError(NOT_RUNNING_HINT)
    try:
        alive = app.GetProductName()
    except Exception as exc:
        raise ResolveConnectionError(NOT_RUNNING_HINT) from exc
    if not alive:
        raise ResolveConnectionError(NOT_RUNNING_HINT)
    return app
