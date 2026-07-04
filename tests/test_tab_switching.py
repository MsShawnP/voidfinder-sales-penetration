"""Tab switching regression: the toggle callback once fell out of
register_layout during an edit (dead code after a return) and every
tab silently showed the Exception Report. These tests pin (1) the
visibility logic, (2) that the callback is actually REGISTERED with
Dash, and (3) that each tab's layout carries its own distinct content."""

import importlib
import sys


def _fresh_wsgi(monkeypatch):
    """Import the app with no database — layout and callback
    registration must not depend on data being available."""
    monkeypatch.setenv("DATABASE_URL", "")
    for mod in list(sys.modules):
        if mod == "wsgi" or mod.startswith("app"):
            del sys.modules[mod]
    return importlib.import_module("wsgi")


def test_tab_visibility_shows_only_the_selected_panel():
    from app.layout import tab_visibility

    for i, tab in enumerate(["exceptions", "rollup", "trend"]):
        styles = tab_visibility(tab)
        assert styles[i] == {"display": "block"}, f"{tab} panel hidden"
        for j, style in enumerate(styles):
            if j != i:
                assert style == {"display": "none"}, (
                    f"{tab} selected but panel {j} visible"
                )


def test_tab_toggle_callback_is_registered(monkeypatch):
    _fresh_wsgi(monkeypatch)
    # The global @callback decorator registers here (Dash 4); the
    # app-level callback_map only fills at serve time.
    from dash import _callback

    registered = "".join(_callback.GLOBAL_CALLBACK_MAP.keys())
    assert "tab-panel-exceptions.style" in registered
    assert "tab-panel-rollup.style" in registered
    assert "tab-panel-trend.style" in registered
    assert "main-tabs.value" in str(_callback.GLOBAL_CALLBACK_MAP)


def test_each_tab_panel_carries_its_own_content(monkeypatch):
    wsgi = _fresh_wsgi(monkeypatch)  # noqa: F841 — registers the layout
    from app.app import app

    layout_str = str(app.layout)
    # Each panel exists and wraps its view's distinctive component.
    for panel, marker in [
        ("tab-panel-exceptions", "void-grid"),
        ("tab-panel-rollup", "rollup-item"),
        ("tab-panel-trend", "trend-chart"),
    ]:
        assert panel in layout_str, f"{panel} missing from layout"
        assert marker in layout_str, f"{marker} missing from layout"
