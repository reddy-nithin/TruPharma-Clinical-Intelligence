# Sub-Plan 02: Light/Dark Theme System

## Priority: Early (no dependencies)
## Can parallelize with: Sub-Plan 01, 06, 07

---

## Goal
The app has ~690 lines of hardcoded dark-mode CSS in `opioid_app.py` with hex colors like `#0a0f1a`, `#141b2d`, `#00e5c8`. Refactor into a CSS custom property system with two complete palettes (Dark + Light) and a sidebar toggle. All pages must look polished in both modes.

## Pre-Requisites
- Read `00_STATUS.md` first.
- Update status to "IN_PROGRESS".

## Context Files to Read First
1. `opioid_track/dashboard/opioid_app.py` — main app with `inject_global_css()` (~690 lines of CSS)
2. `opioid_track/dashboard/pages/drug_explorer.py` — check for hardcoded colors in Plotly charts
3. `opioid_track/dashboard/pages/landscape.py` — check for hardcoded colors
4. `opioid_track/dashboard/pages/geography.py` — check for hardcoded colors
5. `opioid_track/dashboard/pages/demographics.py` — check for hardcoded colors
6. `opioid_track/dashboard/pages/signals.py` — check for hardcoded colors
7. `opioid_track/dashboard/pages/watchdog.py` — check for hardcoded colors
8. `opioid_track/dashboard/components/accessibility.py` — check for hardcoded colors

---

## Agent Assignment

### Agent A (Worktree: `theme-system`) — Create Theme Module
**Task:** Create the theme engine.

**Create file: `opioid_track/dashboard/components/theme.py`**

```python
"""
Theme system for TruPharma Opioid Track.
Provides Dark ("Clinical Terminal") and Light ("Clinical White") palettes
using CSS custom properties for runtime switching.
"""
import streamlit as st
from typing import Dict

# === Dark Theme (current app aesthetic) ===
DARK_THEME: Dict[str, str] = {
    # Backgrounds
    "--bg-primary": "#0a0f1a",         # Main page background
    "--bg-secondary": "#141b2d",       # Cards, sidebars
    "--bg-tertiary": "#1a2332",        # Nested elements, inputs
    "--bg-hover": "#1e2a3a",           # Hover states
    "--bg-sidebar": "#0d1320",         # Sidebar background

    # Text
    "--text-primary": "#e8edf5",       # Main text
    "--text-secondary": "#8892a4",     # Muted text
    "--text-tertiary": "#5a6478",      # Very muted text
    "--text-inverse": "#0a0f1a",       # Text on light backgrounds

    # Accent colors (brand)
    "--accent-teal": "#00e5c8",        # Primary accent
    "--accent-teal-dim": "#00b89e",    # Dimmed teal
    "--accent-teal-bg": "rgba(0, 229, 200, 0.08)",  # Teal background tint
    "--accent-amber": "#f59e0b",       # Warning/medium risk
    "--accent-red": "#ef4444",         # Danger/high risk
    "--accent-green": "#22c55e",       # Success/low risk
    "--accent-purple": "#a855f7",      # Mechanism nodes

    # Borders & Shadows
    "--border-primary": "#1e2a3a",     # Main borders
    "--border-accent": "rgba(0, 229, 200, 0.3)",  # Accent borders
    "--shadow-sm": "0 1px 3px rgba(0,0,0,0.4)",
    "--shadow-md": "0 4px 12px rgba(0,0,0,0.5)",
    "--shadow-lg": "0 8px 24px rgba(0,0,0,0.6)",

    # Chart colors
    "--chart-bg": "#141b2d",           # Plotly paper_bgcolor
    "--chart-plot-bg": "#0a0f1a",      # Plotly plot_bgcolor
    "--chart-grid": "#1e2a3a",         # Grid lines
    "--chart-text": "#8892a4",         # Axis labels

    # Metric card variants
    "--metric-danger-bg": "rgba(239, 68, 68, 0.08)",
    "--metric-warning-bg": "rgba(245, 158, 11, 0.08)",
    "--metric-safe-bg": "rgba(34, 197, 94, 0.08)",

    # Scrollbar
    "--scrollbar-track": "#0a0f1a",
    "--scrollbar-thumb": "#1e2a3a",
}

# === Light Theme ===
LIGHT_THEME: Dict[str, str] = {
    # Backgrounds
    "--bg-primary": "#f8f9fb",
    "--bg-secondary": "#ffffff",
    "--bg-tertiary": "#f0f2f5",
    "--bg-hover": "#e8ebf0",
    "--bg-sidebar": "#f0f2f5",

    # Text
    "--text-primary": "#1a1f2e",
    "--text-secondary": "#5a6478",
    "--text-tertiary": "#8892a4",
    "--text-inverse": "#ffffff",

    # Accent colors (same brand teal, slightly adjusted for contrast)
    "--accent-teal": "#00b89e",
    "--accent-teal-dim": "#009e87",
    "--accent-teal-bg": "rgba(0, 184, 158, 0.08)",
    "--accent-amber": "#d97706",
    "--accent-red": "#dc2626",
    "--accent-green": "#16a34a",
    "--accent-purple": "#9333ea",

    # Borders & Shadows
    "--border-primary": "#e2e5ea",
    "--border-accent": "rgba(0, 184, 158, 0.3)",
    "--shadow-sm": "0 1px 3px rgba(0,0,0,0.08)",
    "--shadow-md": "0 4px 12px rgba(0,0,0,0.1)",
    "--shadow-lg": "0 8px 24px rgba(0,0,0,0.12)",

    # Chart colors
    "--chart-bg": "#ffffff",
    "--chart-plot-bg": "#f8f9fb",
    "--chart-grid": "#e2e5ea",
    "--chart-text": "#5a6478",

    # Metric card variants
    "--metric-danger-bg": "rgba(220, 38, 38, 0.06)",
    "--metric-warning-bg": "rgba(217, 119, 6, 0.06)",
    "--metric-safe-bg": "rgba(22, 163, 74, 0.06)",

    # Scrollbar
    "--scrollbar-track": "#f0f2f5",
    "--scrollbar-thumb": "#c8cdd5",
}


def get_current_theme() -> Dict[str, str]:
    """Returns the active theme palette dict."""
    if st.session_state.get("theme_mode", "dark") == "light":
        return LIGHT_THEME
    return DARK_THEME


def get_theme_mode() -> str:
    """Returns 'dark' or 'light'."""
    return st.session_state.get("theme_mode", "dark")


def render_theme_toggle():
    """
    Renders a theme toggle in the sidebar.
    Call this at the top of the sidebar, before navigation.
    Uses a selectbox or toggle styled as sun/moon.
    """
    current = st.session_state.get("theme_mode", "dark")
    label = "Theme"
    options = ["dark", "light"]
    # NOTE: Use st.sidebar.radio or st.sidebar.toggle
    # Store result in st.session_state.theme_mode
    ...


def generate_css_variables() -> str:
    """
    Generate a <style> block with CSS custom properties from the active theme.
    Returns a string like:
    :root {
        --bg-primary: #0a0f1a;
        --bg-secondary: #141b2d;
        ...
    }
    """
    theme = get_current_theme()
    vars_css = "\n".join(f"    {key}: {value};" for key, value in theme.items())
    return f":root {{\n{vars_css}\n}}"


def get_plotly_theme() -> dict:
    """
    Returns a dict of Plotly layout kwargs matching the current theme.
    Use like: fig.update_layout(**get_plotly_theme())

    Returns:
    {
        "paper_bgcolor": "var(--chart-bg)" won't work in Plotly,
        so return actual hex values from current theme.
        "paper_bgcolor": "#141b2d",
        "plot_bgcolor": "#0a0f1a",
        "font": {"color": "#8892a4"},
        ...
    }
    """
    theme = get_current_theme()
    return {
        "paper_bgcolor": theme["--chart-bg"],
        "plot_bgcolor": theme["--chart-plot-bg"],
        "font": {"color": theme["--chart-text"]},
        "xaxis": {"gridcolor": theme["--chart-grid"]},
        "yaxis": {"gridcolor": theme["--chart-grid"]},
    }
```

**Done criteria:** Module imports without error. `get_current_theme()` returns correct palette. `generate_css_variables()` produces valid CSS.

---

### Agent B (Sequential after A) — Refactor opioid_app.py CSS
**Task:** This is the largest task. Refactor the ~690-line `inject_global_css()` function.

**Read first:** `opioid_track/dashboard/opioid_app.py` — specifically the `inject_global_css()` function and any inline `st.markdown("""<style>...</style>""")` blocks.

**Modify: `opioid_track/dashboard/opioid_app.py`**
Step-by-step:
1. Import `render_theme_toggle`, `generate_css_variables`, `get_theme_mode` from theme module
2. At the top of the sidebar section, call `render_theme_toggle()`
3. In `inject_global_css()`:
   - Prepend the CSS variables block from `generate_css_variables()`
   - Find-and-replace every hardcoded color with its CSS variable equivalent:
     - `#0a0f1a` → `var(--bg-primary)`
     - `#141b2d` → `var(--bg-secondary)`
     - `#1a2332` → `var(--bg-tertiary)`
     - `#00e5c8` → `var(--accent-teal)`
     - `#e8edf5` or similar light text → `var(--text-primary)`
     - `#8892a4` or similar muted text → `var(--text-secondary)`
     - All `rgba(0, 229, 200, ...)` → `var(--accent-teal-bg)` or `var(--border-accent)`
     - Box shadows → `var(--shadow-sm)`, `var(--shadow-md)`, `var(--shadow-lg)`
   - Keep the structural CSS (layouts, fonts, spacing) unchanged — only swap colors

**IMPORTANT:** This is a large refactor. Work methodically through the CSS:
1. First pass: replace background colors
2. Second pass: replace text colors
3. Third pass: replace border colors
4. Fourth pass: replace shadow values
5. Fifth pass: replace accent/brand colors
6. Verify no raw hex values remain (except in the theme definitions themselves)

**Done criteria:** App renders identically in dark mode (regression check). Toggling to light mode shows light backgrounds with readable text.

---

### Agent C (Sequential after B, or parallel with B on different files) — Audit Page Files
**Task:** Check each page file for hardcoded colors in Plotly charts and inline styles.

**For each page file, do:**
1. Search for hardcoded hex colors (`#0a0f1a`, `#141b2d`, `#00e5c8`, `#e8edf5`, `#8892a4`, etc.)
2. Search for hardcoded `paper_bgcolor`, `plot_bgcolor`, `font=dict(color=...)` in Plotly `fig.update_layout()` calls
3. Replace with theme-aware values using `get_plotly_theme()` from `theme.py`
4. Search for inline `st.markdown("""<style>...</style>""")` with hardcoded colors and replace with CSS variables

**Files to audit and modify:**
1. `opioid_track/dashboard/pages/drug_explorer.py`
2. `opioid_track/dashboard/pages/landscape.py`
3. `opioid_track/dashboard/pages/geography.py`
4. `opioid_track/dashboard/pages/demographics.py`
5. `opioid_track/dashboard/pages/signals.py`
6. `opioid_track/dashboard/pages/watchdog.py`
7. `opioid_track/dashboard/components/accessibility.py` (if it has colors)
8. `opioid_track/dashboard/components/molecule_viewer.py` (if it exists and has colors)

**Pattern for Plotly charts:**
```python
# BEFORE:
fig.update_layout(
    paper_bgcolor="#141b2d",
    plot_bgcolor="#0a0f1a",
    font=dict(color="#8892a4"),
)

# AFTER:
from opioid_track.dashboard.components.theme import get_plotly_theme
fig.update_layout(**get_plotly_theme())
```

**Done criteria:** `grep -rn '#0a0f1a\|#141b2d\|#1a2332' opioid_track/dashboard/pages/` returns zero matches (no hardcoded dark colors in page files). All charts adapt to theme toggle.

---

## Execution Order
1. **Agent A** creates `theme.py` (can use worktree)
2. **Agent B** refactors `opioid_app.py` CSS (sequential, needs theme.py)
3. **Agent C** audits page files (can start in parallel with B on separate files, but merge after B)
4. Visual verification: toggle between themes
5. Commit: `git commit -m "feat(opioid): add light/dark theme system with CSS custom properties"`

## Checkpoint Protocol
This is a large sub-plan. If hitting context limits:
- **Mid-Agent B:** Note which CSS sections are done (backgrounds? text? borders? shadows? accents?) in the checkpoint
- **Mid-Agent C:** Note which page files are done in the checkpoint
- The next agent can continue from exactly where you left off

## Final Verification
```bash
# No hardcoded dark colors in page files:
grep -rn '#0a0f1a\|#141b2d\|#1a2332\|#00e5c8' opioid_track/dashboard/pages/ | wc -l
# Should be 0 (or only in comments)

# App loads in both modes:
# streamlit run opioid_track/dashboard/opioid_app.py
# Toggle theme — all pages render correctly
```
Update `00_STATUS.md` to "COMPLETED".
