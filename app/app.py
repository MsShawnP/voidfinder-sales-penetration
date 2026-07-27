"""Dash application factory — no external stylesheets, no dash-bootstrap-components."""

import os
import secrets

import dash

app = dash.Dash(
    __name__,
    assets_folder="../assets",
    suppress_callback_exceptions=True,
    title="Void Finder — Authorized but Not Selling",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server
server.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

# ── Branded loading overlay ──────────────────────────────────────────
# Same pattern as Spin Rate: static HTML/CSS injected into the page
# body so the browser paints it on the first frame, before any Dash
# JavaScript runs. An inline script watches for the exception grid to
# hydrate and fades the overlay out. Colors/fonts are literal Lailara
# tokens so the overlay is styled before the stylesheet loads.
_LOADING_OVERLAY = """
    <style>
      #voidfinder-loading {
        position: fixed;
        inset: 0;
        z-index: 99999;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #f5f3ee; /* Canvas — London-100 warmed */
        transition: opacity 300ms ease-out;
      }
      #voidfinder-loading.vf-hide { opacity: 0; pointer-events: none; }
      .vf-load-inner { text-align: center; padding: 0 24px; }
      .vf-load-spinner {
        width: 46px;
        height: 46px;
        margin: 0 auto 26px;
        border: 3px solid #d9d9d9;     /* London-85 gridline */
        border-top-color: #1f2e7a;     /* Chicago-20 navy */
        border-radius: 50%;
        animation: vf-spin 900ms linear infinite;
      }
      .vf-load-brand {
        font-family: 'Playfair Display', Georgia, 'Times New Roman', serif;
        font-size: 26px;              /* DS Brand-name step; 20px mobile below */
        font-weight: 700;
        color: #0d0d0d;                /* Ink */
        letter-spacing: -0.01em;
        line-height: 1.2;
      }
      .vf-load-sub {
        font-family: 'Source Sans 3', 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 12px;
        font-weight: 600;
        color: #595959;                /* Text secondary */
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 10px;
      }
      .vf-load-hint {
        font-family: 'Source Sans 3', 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 14px;
        font-weight: 400;
        color: #595959;
        margin-top: 22px;
      }
      @keyframes vf-spin { to { transform: rotate(360deg); } }
      @media (prefers-reduced-motion: reduce) {
        #voidfinder-loading { transition: none; }
        .vf-load-spinner {
          animation: none;
          border-color: #1f2e7a;
        }
      }
    </style>
    <div id="voidfinder-loading" role="status" aria-live="polite" aria-label="Loading Void Finder">
      <div class="vf-load-inner">
        <div class="vf-load-spinner" aria-hidden="true"></div>
        <div class="vf-load-brand">Void&nbsp;Finder</div>
        <div class="vf-load-sub">Authorized &times; Not&nbsp;Selling</div>
        <div class="vf-load-hint">Scanning the authorization matrix&hellip;</div>
      </div>
    </div>
    <script>
      (function () {
        var SAFETY_MS = 20000;
        function hide() {
          var el = document.getElementById('voidfinder-loading');
          if (!el || el.classList.contains('vf-hide')) return;
          el.classList.add('vf-hide');
          setTimeout(function () {
            if (el && el.parentNode) el.parentNode.removeChild(el);
          }, 400);
        }
        // The default tab is interactive once the exception grid (or
        // the no-data notice) exists in the DOM.
        function ready() {
          return !!document.querySelector('#void-grid .ag-root, #vf-no-data');
        }
        function check() {
          if (ready()) { hide(); return true; }
          return false;
        }
        if (check()) return;
        var obs = new MutationObserver(function () {
          if (check()) obs.disconnect();
        });
        obs.observe(document.documentElement, { childList: true, subtree: true });
        // Never trap the visitor behind the overlay.
        setTimeout(function () { obs.disconnect(); hide(); }, SAFETY_MS);
      })();
    </script>
"""

app.index_string = """<!DOCTYPE html>
<html lang="en">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        __LOADING_OVERLAY__
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>""".replace("__LOADING_OVERLAY__", _LOADING_OVERLAY)
