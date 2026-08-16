---
name: Lumina Precision
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#424754'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#727785'
  outline-variant: '#c2c6d6'
  surface-tint: '#005ac2'
  primary: '#0058be'
  on-primary: '#ffffff'
  primary-container: '#2170e4'
  on-primary-container: '#fefcff'
  inverse-primary: '#adc6ff'
  secondary: '#565e74'
  on-secondary: '#ffffff'
  secondary-container: '#dae2fd'
  on-secondary-container: '#5c647a'
  tertiary: '#4d5d73'
  on-tertiary: '#ffffff'
  tertiary-container: '#66768d'
  on-tertiary-container: '#fdfcff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#004395'
  secondary-fixed: '#dae2fd'
  secondary-fixed-dim: '#bec6e0'
  on-secondary-fixed: '#131b2e'
  on-secondary-fixed-variant: '#3f465c'
  tertiary-fixed: '#d3e4fe'
  tertiary-fixed-dim: '#b7c8e1'
  on-tertiary-fixed: '#0b1c30'
  on-tertiary-fixed-variant: '#38485d'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  display-lg:
    fontFamily: Hanken Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-sm:
    fontFamily: Hanken Grotesk
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px
  panel-gutter: 1px
  safe-margin: 12px
---

## Brand & Style
This design system shifts from a traditional "dark mode" editor to a high-clarity, professional light workspace. The brand personality is clinical, precise, and high-performance, designed to reduce eye strain during long editorial sessions by using a structured, high-contrast palette.

The style is **Minimalist with a focus on Tonal Layering**. It avoids heavy shadows in favor of subtle border increments and distinct grayscale shifts to define the interface's functional zones (Timeline, Preview, Assets). The goal is to make the vibrant video content the focal point while the UI provides a stable, "paper-white" architectural frame.

## Colors
The palette is engineered for professional utility. 
- **Base Background:** Pure `#FFFFFF` is reserved for the primary workspace and document areas.
- **Surface Tiers:** `#F8FAFC` (Level 1) and `#F1F5F9` (Level 2) are used to compartmentalize toolbars and panels.
- **Primary Accent:** `#3B82F6` (Vibrant Blue) is used exclusively for interactive states, playback indicators, and primary "Export" actions.
- **Typography:** Deep Charcoal (`#0F172A`) ensures AAA contrast ratios for all critical labels and metadata.

## Typography
The typographic hierarchy prioritizes legibility in data-dense environments. 
- **Headlines:** Use **Hanken Grotesk** for a contemporary, sharp technical feel.
- **Body:** **Inter** is utilized for its high x-height and exceptional readability at small sizes in property inspectors.
- **Metadata/Timecodes:** **JetBrains Mono** is used for all numerical data, timecodes, and technical labels to ensure character alignment and a "pro-tool" aesthetic.

## Layout & Spacing
The design system employs a **Fixed-Panel Grid** model typical of professional creative suites. 
- **Layout Model:** A 1px "inner-border" gutter system separates major functional zones (Timeline, Source, Program, Bin).
- **Density:** High-density spacing (4px/8px increments) is used within property inspectors to maximize visible controls.
- **Responsive Behavior:** On desktop, panels are resizable with minimum widths. On tablet, the layout reflows into a single-column stack with retractable sidebars.

## Elevation & Depth
In this light-themed system, depth is conveyed through **Tonal Stepping** rather than shadows to maintain a "flat-plus" professional look.
- **Level 0 (Base):** White (`#FFFFFF`) for the main canvas.
- **Level 1 (Panels):** `#F8FAFC` for secondary toolbars.
- **Level 2 (Trays/Modals):** `#F1F5F9` with a subtle 1px border (`#E2E8F0`).
- **Interaction:** Shadows are only used for floating "Popovers" or "Context Menus," using a very soft, low-opacity blue-tinted shadow (e.g., `0px 10px 15px -3px rgba(15, 23, 42, 0.08)`).

## Shapes
A **Soft** shape language (4px / 0.25rem) is used for all UI elements. This maintains a disciplined, technical appearance while feeling modern. 
- **Buttons & Inputs:** Use the standard 4px radius.
- **Timeline Clips:** Use a 2px radius to maximize internal space for waveforms/thumbnails.
- **Container Groups:** Larger panels remain sharp (0px) at the screen edges to integrate with the application frame.

## Components
- **Buttons:** 
  - *Primary:* Solid `#3B82F6` with White text.
  - *Secondary:* White background with `#E2E8F0` border and `#0F172A` text.
- **Timeline Clips:** Light grey base with a high-contrast 2px top-border color-coded by media type (Video, Audio, Adjustment).
- **Input Fields:** Minimalist style. Use a white background with a 1px `#E2E8F0` border that transforms to a 2px blue border on focus.
- **Lists/Trees:** Use a blue "active bar" (2px wide) on the left edge of selected assets in the project bin.
- **Checkboxes:** Square with a 2px radius; when checked, use solid blue with a white checkmark.
- **Playhead/Scrubbers:** The playhead is a 2px blue line with a small inverted-triangle handle at the top for precise frame-targeting.