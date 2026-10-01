# Design System & Aesthetics Guide

This document outlines the core design language for our project, heavily inspired by modern, premium web aesthetics (e.g., Vercel, Stripe). The goal is to create a UI that feels responsive, alive, minimalist, and incredibly polished.

## Core Philosophy
1. **Premium Minimalism**: Remove visual clutter. Let typography and spacing do the heavy lifting.
2. **High Contrast**: Use stark contrasts (deep black backgrounds, bright white text) for dark mode.
3. **Subtle Details**: Borders should be extremely faint. Shadows should be soft and diffuse.
4. **Dynamic Interaction**: Every interactive element should provide immediate, smooth visual feedback.

## 1. Typography
We prioritize sans-serif fonts that look incredibly crisp on high-DPI screens.
- **Primary Font**: [Geist](https://vercel.com/font), Inter, or system-ui.
- **Headers**: Tightly tracked (negative letter-spacing like `-0.02em`), heavy font weights (600-700).
- **Body Text**: Readable line height (1.6), medium weights (400-500). Font size typically `14px` or `15px` for a sleek dashboard feel.

## 2. Color Palette (Dark Mode First)
- **Background**: `#000000` (Pure Black)
- **Foreground (Text)**: `#EDEDED` (Soft White)
- **Muted Text**: `#A1A1AA` (Zinc 400)
- **Borders/Lines**: `#333333` (Subtle Dark Gray) or `rgba(255, 255, 255, 0.1)`
- **Accents**: 
  - *Primary*: A vibrant, highly saturated color (e.g., `#0070F3` Vercel Blue)
  - *Success*: `#17C964`
  - *Error*: `#F31260`

## 3. UI Components & Layout
### Glassmorphism
Use subtle frosted glass effects for fixed headers, tooltips, and floating menus.
```css
.glass-panel {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}
```

### Cards
Cards should not have harsh dropshadows in dark mode. Instead, they rely on a faint `1px` border or a very subtle gradient border.
```css
.card {
  background-color: #111;
  border: 1px solid #333;
  border-radius: 8px;
  transition: border-color 0.2s ease, transform 0.2s ease;
}
.card:hover {
  border-color: #555;
}
```

### Buttons
Buttons should feel tactile. Primary buttons should invert the color scheme.
- **Primary**: White background, black text. On hover: slightly dimmer white.
- **Secondary**: Transparent background, faint border, white text. On hover: light gray background.

## 4. Micro-Animations & Interactivity
- **Hover Effects**: All buttons and links must have a smooth `transition: all 0.2s ease-out;`.
- **Loading States**: Use skeleton screens with a subtle shimmer effect instead of basic spinners where possible.
- **Focus Rings**: Ensure active elements have a high-contrast focus ring (e.g., `outline: 2px solid #0070F3; outline-offset: 2px;`) for accessibility.

> [!TIP]
> **Vercel Trick**: Use a subtle radial gradient mask over cards on hover to simulate a "flashlight" effect revealing the border. It adds an immense premium feel to the UI.

## 5. Implementation Rules
1. **No generic colors**: Never use `red`, `blue`, or `green`. Always use specific hex/HSL values tailored to the palette.
2. **Spacing**: Use a strict 4px/8px grid system (`gap-4`, `p-8`).
3. **Icons**: Use minimal, thin-stroke icons (e.g., Lucide or Radix Icons).
