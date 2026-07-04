"""Lailara design-system tokens used by charts and components.

Values trace to LAILARA_DESIGN_SYSTEM.md v2 — family and step noted
per constant. Do not add ad-hoc hex values.
"""

LL_CANVAS = "#f5f3ee"          # London-100 warmed (canvas)

LL_CHICAGO = "#1f2e7a"         # Chicago-20: primary buttons, anchor data series
LL_CHICAGO_LIGHT = "#8e9ad0"   # Chicago-70
LL_CHICAGO_HOVER = "#141e52"   # Chicago-10
LL_CHICAGO_SURFACE = "#e8eaf4" # Chicago-95

LL_HK = "#158f75"              # Hong Kong-35: positive/secondary series
LL_HK_LIGHT = "#6dcdb5"        # HK-70
LL_HK_DARK = "#0c6552"         # HK-20
LL_HK_SURFACE = "#e4f5f0"      # HK-95

LL_TOKYO = "#b82d4a"           # Tokyo-40: contrast/negative series
LL_TOKYO_LIGHT = "#e68a9a"     # Tokyo-70
LL_TOKYO_DARK = "#7e1f34"      # Tokyo-20
LL_TOKYO_SURFACE = "#fbe9ed"   # Tokyo-95

LL_SG = "#ee8a2a"              # Singapore-55
LL_SG_DARK = "#7a3d10"         # Singapore-20
LL_SG_SURFACE = "#fdeee0"      # Singapore-95

LL_RED = "#cc100a"             # Red-42: brand accent, text and 1px rules only

LL_INK = "#0d0d0d"             # London-5: chart titles, primary headings
LL_TEXT = "#333333"            # London-20: body text
LL_TEXT_SEC = "#595959"        # London-35: axis text, subtitles
LL_REFERENCE = "#666666"       # London-40: reference lines, dashed
LL_GRIDLINE = "#d9d9d9"        # London-85: horizontal gridlines only
LL_SURFACE = "#f2f2f2"         # London-95: soft card surface

LL_SERIF_FAMILY = "Playfair Display, Georgia, Times New Roman, serif"
LL_SANS_FAMILY = "Source Sans 3, Source Sans Pro, Helvetica Neue, Helvetica, Arial, sans-serif"


def fmt_dollars(v) -> str:
    return f"${v:,.0f}"

# Sequential Tokyo ramp for magnitude-ranked loss data (map fills).
# Steps 85 → 5; darkest = largest loss. Step 95 is never a data fill.
LL_SEQ_TOKYO = [
    "#f3c1cb",  # Tokyo-85
    "#e68a9a",  # Tokyo-70
    "#d9506e",  # Tokyo-55
    "#b82d4a",  # Tokyo-40
    "#94243c",  # Tokyo-30
    "#7e1f34",  # Tokyo-20
    "#470f1c",  # Tokyo-5
]

# Categorical chart palette — paired system, assigned in order.
LL_CAT_10 = [
    "#1f2e7a", "#8e9ad0",   # Chicago dark/light
    "#0c6552", "#6dcdb5",   # Hong Kong dark/light
    "#7e1f34", "#e68a9a",   # Tokyo dark/light
    "#7a3d10", "#f6b97c",   # Singapore dark/light
    "#8e0b07", "#ee8880",   # Red dark/light
]
