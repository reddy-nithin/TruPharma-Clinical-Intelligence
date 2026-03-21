# 3D Body Chart — Build Plan

## Overview

Overhaul the `_build_body_heatmap_html` function in `src/frontend/pages/primary_demo.py` to fix hotspot positioning, normalize model brightness across genders, render hotspots inside a semi-transparent body, and add visible skin/systemic symptom regions.

All changes are scoped to a single function (`_build_body_heatmap_html`, starts around line 914) in one file:

```
src/frontend/pages/primary_demo.py
```

The .glb model files (`src/frontend/static/male.glb`, `src/frontend/static/female.glb`) are unchanged.

---

## Problem Summary

The original implementation had four issues:

1. **Hotspot positions were wrong.** Coordinates assumed the model's feet were at Y=0, but both .glb models are centered at origin (Y ranges from -0.85 to +0.85). Every hotspot floated ~0.85 units above the body.
2. **Body was too large for the frame.** Camera was at 2.5m orbit distance with 30° FOV in a 420px container — the model was clipped.
3. **Female model rendered much brighter than the male.** No tone-mapping was applied, and the default exposure (1.1) amplified material differences between the two .glb files.
4. **Skin and systemic symptom counts had no visual representation.** They only appeared in the legend text. Users saw counts like "Skin (3)" but no hotspot on the body.

---

## Changes to Implement

### 1. Fix hotspot coordinates (per-gender, from trimesh analysis)

Replace the single `region_hotspots` dict with a `_HOTSPOT_COORDS` dict keyed by gender (`"male"` / `"female"`), then select with:

```python
region_hotspots = _HOTSPOT_COORDS.get(gender, _HOTSPOT_COORDS["male"])
```

**Male model** bounding box (from trimesh): Y: -0.858 to +0.858, X: ±0.491, Z: ±0.148

| Region   | Position string          | Normal         | Label |
|----------|--------------------------|----------------|-------|
| head     | `"0 0.738 0.02"`         | `"0 0.25 1"`   | True  |
| chest    | `"0 0.378 0.02"`         | `"0 0 1"`      | True  |
| abdomen  | `"0 0.137 0.02"`         | `"0 0 1"`      | True  |
| arms L   | `"-0.370 0.309 0.00"`    | `"-1 0 0"`     | True  |
| arms R   | `"0.370 0.309 0.00"`     | `"1 0 0"`      | False |
| legs L   | `"-0.108 -0.481 0.02"`   | `"0 0 1"`      | True  |
| legs R   | `"0.108 -0.481 0.02"`    | `"0 0 1"`      | False |
| skin     | `"0.18 0.26 0.02"`       | `"0 0 1"`      | True  |
| systemic | `"-0.16 0.06 0.02"`      | `"0 0 1"`      | True  |

**Female model** bounding box: Y: -0.842 to +0.842, X: ±0.489, Z: -0.230 to +0.103

| Region   | Position string          | Normal         | Label |
|----------|--------------------------|----------------|-------|
| head     | `"0 0.724 0.00"`         | `"0 0.25 1"`   | True  |
| chest    | `"0 0.371 0.00"`         | `"0 0 1"`      | True  |
| abdomen  | `"0 0.135 0.00"`         | `"0 0 1"`      | True  |
| arms L   | `"-0.370 0.303 0.00"`    | `"-1 0 0"`     | True  |
| arms R   | `"0.370 0.303 0.00"`     | `"1 0 0"`      | False |
| legs L   | `"-0.108 -0.472 0.00"`   | `"0 0 1"`      | True  |
| legs R   | `"0.108 -0.472 0.00"`    | `"0 0 1"`      | False |
| skin     | `"0.18 0.24 0.00"`       | `"0 0 1"`      | True  |
| systemic | `"-0.16 0.04 0.00"`      | `"0 0 1"`      | True  |

Z values are pushed to ~0 so hotspots sit **inside** the body volume rather than floating in front of it.

### 2. Fix camera settings (model-viewer attributes)

Update the `<model-viewer>` element attributes:

| Attribute          | Old              | New              |
|--------------------|------------------|------------------|
| shadow-intensity   | `"0.4"`          | `"0.3"`          |
| exposure           | `"1.1"`          | `"0.9"`          |
| tone-mapping       | *(not set)*      | `"commerce"`     |
| camera-orbit       | `"0deg 75deg 2.5m"` | `"0deg 75deg 3.8m"` |
| min-camera-orbit   | `"auto auto 1.2m"`  | `"auto auto 2m"`    |
| max-camera-orbit   | `"auto auto 5m"`    | `"auto auto 6m"`    |
| field-of-view      | `"30deg"`        | `"28deg"`        |

Also increase the model-viewer CSS height from `420px` to `480px`.

### 3. Add semi-transparent body rendering (JavaScript)

Add a `load` event listener in the `<script>` block that traverses the Three.js scene (exposed via `mv.model`) and sets all mesh materials to 55% opacity:

```javascript
mv.addEventListener('load', () => {
    try {
        mv.model.traverse((node) => {
            if (node.isMesh && node.material) {
                node.material.transparent = true;
                node.material.opacity = 0.55;
                node.material.needsUpdate = true;
            }
        });
    } catch(e) {}
});
```

This makes the glowing hotspot dots visible through the body surface.

### 4. Add skin & systemic hotspot rendering

In the hotspot element generation loop, add two new branches:

- **Skin**: Rendered as a **dashed-border ring** (transparent background, dashed border in the severity color, wider glow). Class: `skin-dot`.
- **Systemic**: Rendered as a **solid dot with a white semi-transparent border** (filled background, wider glow, `border: 2px solid rgba(255,255,255,0.3)`). Class: `systemic-dot`.
- All other regions keep the existing solid-dot style.

### 5. Include skin/systemic in severity scaling

Change the `body_max` calculation to include skin and systemic counts:

```python
# Old — excluded skin and systemic from max:
body_max = max(
    (v for k, v in region_counts.items() if k not in ("unknown", "skin", "systemic")),
    default=1,
) or 1

# New — only exclude unknown:
body_max = max(
    (v for k, v in region_counts.items() if k != "unknown"),
    default=1,
) or 1
```

### 6. Update systemic legend entry

Replace the old text-only legend entry with a colored dot matching the systemic hotspot style:

```python
# Old:
extra_legend += f'<span>&#9889; Systemic ({systemic_count})</span>'

# New:
sy_hex = _hex("systemic") or "#3b82f6"
extra_legend += (
    f'<span><span class="ldot" style="background:{sy_hex};'
    f'border:2px solid rgba(255,255,255,0.3)"></span> Systemic ({systemic_count})</span>'
)
```

---

## Verification

To preview without running the full RAG pipeline, create a temporary Streamlit page at `src/frontend/preview_body_chart.py` that imports `map_symptoms_to_regions` and `_build_body_heatmap_html` from `primary_demo.py`, feeds them sample symptoms, and renders via `components.html()`. Run it from `src/frontend/` so it picks up the `.streamlit/config.toml` (which has `enableStaticServing = true`) and the `static/` directory containing the .glb files:

```bash
cd src/frontend && streamlit run preview_body_chart.py
```

Sample symptoms to test all regions:

```
headache, dizziness, chest pain, tachycardia, abdominal pain, diarrhea,
rash, pruritus, urticaria, fatigue, fever, myalgia, joint pain,
peripheral neuropathy, hepatotoxicity
```

Check:
- [ ] Body fits within the viewer frame (no clipping)
- [ ] Hotspots are positioned on the correct body regions (not floating above)
- [ ] Male and female models have similar brightness
- [ ] Skin hotspot visible as a dashed ring on the right torso
- [ ] Systemic hotspot visible as a bordered dot on the left lower torso
- [ ] Hotspots appear inside the semi-transparent body, not outside
- [ ] Gender toggle switches both model and hotspot coordinates
- [ ] Legend shows entries for Low / Med / High / Skin / Systemic

Delete the preview file when done.
