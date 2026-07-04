/**
 * clientside.js — Void Finder.
 *
 * Fix Plotly text clipping caused by the web-font loading race.
 * `font-display: swap` (lailara-frame.css) paints chart text with a
 * fallback font immediately, then swaps to the brand fonts once they
 * download. Plotly measures text widths ONCE, at layout time, with
 * whichever font is active at that instant — if a chart draws before
 * the swap completes, labels are positioned with the fallback font's
 * metrics and the wider brand glyphs overflow the space Plotly already
 * committed to. Plotly never re-measures on its own.
 *
 * Fix (same as Spin Rate): once the browser confirms the fonts have
 * finished loading, resize every drawn plot so Plotly re-measures with
 * the final metrics. Charts that draw after the fonts are ready never
 * hit the race at all.
 */
(function () {
    function resizePlotlyCharts() {
        document.querySelectorAll(".js-plotly-plot").forEach(function (gd) {
            if (window.Plotly && gd._fullLayout) {
                window.Plotly.Plots.resize(gd);
            }
        });
    }

    if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(resizePlotlyCharts);
    }
})();
