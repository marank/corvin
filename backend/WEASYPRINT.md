# WeasyPrint Quirks & Workarounds

This document records WeasyPrint-specific layout issues discovered during
invoice-template development, along with the workarounds applied in this
project. All findings are against **WeasyPrint 70.0** (current as of
September 2026).

---

## Table of Contents

1. [Flex `min-height: auto` inflates items containing grids](#1-flex-min-height-auto-inflates-items-containing-grids)
2. [`height: 100%` does not resolve in paged context](#2-height-100-does-not-resolve-in-paged-context)
3. [Negative vertical margins cannot escape `@page` margins](#3-negative-vertical-margins-cannot-escape-page-margins)
4. [Negative vertical margins do not extend past body padding](#4-negative-vertical-margins-do-not-extend-past-body-padding)
5. [Nested flex children can cause unexpected page breaks](#5-nested-flex-children-can-cause-unexpected-page-breaks)
6. [CSS cascade: user CSS must come before structural CSS](#6-css-cascade-user-css-must-come-before-structural-css)
7. [Internal coordinate system uses CSS pixels, not PDF points](#7-internal-coordinate-system-uses-css-pixels-not-pdf-points)

---

## 1. Flex `min-height: auto` inflates items containing grids

**Severity:** High — causes visually incorrect footer spacing.

### Problem

In a `flex-direction: column` container with explicit height, flex items
with `flex: 0 0 auto` whose children include a CSS grid are allocated
more height than their content requires. The excess equals the height the
grid would occupy if its content were reflowed at minimum (zero) width.

The CSS Flexbox spec says the default `min-height` for flex items is
`auto`, which resolves to the item's min-content height. WeasyPrint
computes this min-content height by doing a hypothetical layout at zero
width. For a grid child with long text (e.g. "IBAN: DE02120300000000202051"),
this hypothetical layout wraps text to many more lines, producing a much
taller result. This inflated min-content height then becomes the item's
actual rendered height, even though the grid at its real width is much
shorter.

### Reproduction

```html
<!DOCTYPE html>
<html><head><style>
@page { size: 210mm 297mm; margin: 0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  height: 297mm;
  display: flex;
  flex-direction: column;
}
#header { flex: 0 0 auto; height: 40mm; }
#content { flex: 1 1 auto; min-height: 0; }
#footer {
  flex: 0 0 auto;
  padding: 8mm 15mm 15mm 25mm;
  background: #eee;
  font-size: 7.5pt;
  line-height: 1.45;
}
.grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr 1.2fr;
  gap: 8mm;
}
</style></head>
<body>
  <div id="header">Header</div>
  <div id="content"><p>Content</p></div>
  <div id="footer">
    <div class="grid">
      <div>My Company<br>Name<br>Musterallee 123<br>
           12345 Musterstadt<br>Deutschland</div>
      <div>Telefon: 012345<br>a@bc.de</div>
      <div>Geschaeftskonto<br>Inhaber: Firma GmbH<br>
           IBAN: DE02120300000000202051<br>BIC: BYLADEM1001</div>
    </div>
  </div>
</body></html>
```

**Expected:** `#footer` height ≈ 42mm (grid content 19mm + padding 23mm).

**Actual:** `#footer` height ≈ 54mm. The extra ~12mm is empty space between
the grid bottom and the padding-bottom region.

Short text in the grid cells (e.g. "A", "B", "C") does not trigger the bug.

### Workaround

Set `min-height: 0` on all flex items that should not grow:

```css
body > #page-header,
body > #page-footer {
  flex: 0 0 auto;
  min-height: 0;       /* ← prevents inflated min-content height */
}
```

This tells the flex algorithm to use the actual rendered height instead of
the min-content height.

### Upstream status

Not fixed as of WeasyPrint 70.0. Related open issues:
- [#2400 — Flex support enhancement](https://github.com/Kozea/WeasyPrint/issues/2400)
  (umbrella tracking issue; `min-content` / `max-content` sizes listed as TODO)
- [#2145 — Grid support enhancements](https://github.com/Kozea/WeasyPrint/issues/2145)
  (complex `min-content` / `max-content` cases listed as TODO)
- [#2362 — Improve flex layout](https://github.com/Kozea/WeasyPrint/issues/2362)

The v70.0 fix `#2815` ("Remove flex placeholders added when setting item
width") is related to flex sizing but does not address the min-content
height calculation for column-direction containers with grid children.

---

## 2. `height: 100%` does not resolve in paged context

**Severity:** High — breaks flex-grow entirely.

### Problem

In a paged (PDF) context, `body { height: 100% }` does not resolve to
the page height. The body only sizes to its content. As a result,
`flex: 1` on a content div has nothing to grow into, and the footer is
not pushed to the page bottom.

### Workaround

Use an explicit height matching the page dimensions:

```css
body {
  height: 297mm;  /* explicit, not 100% */
  display: flex;
  flex-direction: column;
}
```

In this project, the template's `page_height` property (e.g. `"297mm"`,
`"11in"`) is injected into the structural CSS by `build_pdf_html()`.

---

## 3. Negative vertical margins cannot escape `@page` margins

**Severity:** Medium — footer background doesn't reach the page edge.

### Problem

`@page { margin: 20mm }` creates a hard boundary. Negative margins on
body content are clipped at this boundary in all directions, unlike
browser behaviour where `overflow: hidden` allows content to extend into
padding areas.

Horizontal negative margins appear to work because the clipping is less
visible at the footer's narrow height.

### Workaround

Use `@page { margin: 0 }` and handle all spacing via body/element
padding or CSS custom properties. This moves the margins into the CSS
box model where negative margins work as expected.

---

## 4. Negative vertical margins do not extend past body padding

**Severity:** Medium — affects "full-bleed footer" patterns.

### Problem

Even with `@page { margin: 0 }`, a footer's `margin-bottom: -20mm`
cannot extend past `body { padding-bottom: 20mm }`. The footer's
background stops at the body padding boundary, leaving a visible gap.

Horizontal negative margins (`margin-left`, `margin-right`) **do** work
to extend past body padding — a child can escape the padding box
horizontally. The asymmetry is specific to WeasyPrint's vertical handling.

### Workaround

Do not set body/wrapper padding. Let each section (`#page-header`,
`#page-content`, `#page-footer`) handle its own padding via the
`--page-margin-*` CSS custom properties. The footer sits at the page
edge naturally without needing negative margins.

---

## 5. Nested flex children can cause unexpected page breaks

**Severity:** High — footer placed on second page.

### Problem

A nested structure such as:

```html
<div id="page-footer">         <!-- flex child -->
  <div class="document-footer"> <!-- inner wrapper -->
    ...content...
  </div>
</div>
```

can cause WeasyPrint to place the footer on a second page, even when
the calculated remaining space is sufficient. This was observed when
the inner element had `width: calc(100% + ...)` expanding it beyond
the content box, but also occurred with simpler nested structures in
some configurations.

A direct child (no nesting) consistently stayed on one page.

### Workaround

This was resolved by removing server-side padding from the wrapper
elements. With zero padding on the body and no width expansion on the
footer, the nesting no longer triggers the page break. The current
structure uses `#page-header`, `#page-content`, and `#page-footer` as
thin wrappers with user CSS controlling all spacing.

If the issue recurs, flatten the structure: apply footer styles directly
to `#page-footer` instead of a nested element.

---

## 6. CSS cascade: user CSS must come before structural CSS

**Severity:** High — structural layout silently breaks.

### Problem

If user CSS appears **after** structural CSS in the same `<style>` block,
a user rule like:

```css
body {
  margin: 0;
  background: white;
  color: black;
}
```

will override the structural:

```css
body {
  height: 297mm;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}
```

because they have equal specificity and the last declaration wins. The
flex layout is silently destroyed.

### Workaround

In `build_pdf_html()`, user CSS is emitted **first**, and structural CSS
**second**. The structural rules win on `body`, `@page`, and
`#page-content` since they appear later. User styles for `body`
(background, color, etc.) still apply because they set non-conflicting
properties.

```html
<style>
  /* 1. User CSS (from template) */
  {css}
  /* 2. Structural CSS (from server) */
  @page { size: A4; margin: 0; }
  html, body { margin: 0; }
  body { height: 297mm; display: flex; ... }
  ...
</style>
```

---

## 7. Internal coordinate system uses CSS pixels, not PDF points

**Severity:** Low — affects diagnostic/debugging only.

### Problem

WeasyPrint's internal layout tree (accessed via `page._page_box`)
reports coordinates and dimensions in **CSS pixels** (96 DPI), not
PDF points (72 DPI) or millimeters.

Conversion factors:
- 1 mm ≈ 3.78 CSS px (`96 / 25.4`)
- 1 CSS px ≈ 0.265 mm (`25.4 / 96`)
- 1 PDF pt = 1/72 inch ≈ 0.353 mm

PDF content streams use a different coordinate system with Y-axis
transforms (e.g. `1 0 0 -1 0 841.89 cm`). Layout-tree measurements
and content-stream measurements must not be mixed without proper
conversion.

### Impact

Earlier diagnostic analysis in this project produced incorrect
conclusions (e.g. page appearing to be 133mm when CSS specified 100mm)
due to treating layout-tree values as PDF points.

---

## Summary of Applied Workarounds

| Issue | Workaround | Location |
|-------|-----------|----------|
| min-height inflates flex items | `min-height: 0` on header/footer | `build_pdf_html()`, HTML preview |
| `height: 100%` ignored | Explicit `height: 297mm` (etc.) | `build_pdf_html()` |
| `@page` margins are hard boundaries | `@page { margin: 0 }` | `build_pdf_html()` |
| Negative bottom margins don't work | Zero wrapper padding; user CSS owns margins | `build_pdf_html()`, user CSS |
| Nested children cause page breaks | Thin wrapper divs, no server padding | `build_pdf_html()`, HTML preview |
| CSS cascade destroys structure | User CSS before structural CSS | `build_pdf_html()` |

All workarounds are centralised in `backend/core/services/pdf.py`
(`build_pdf_html()`) and `backend/core/views/invoice_template.py`
(HTML preview endpoint).
