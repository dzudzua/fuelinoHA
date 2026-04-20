# FuelinoHA Brand Assets

Place Home Assistant brand images for the custom integration in this folder.

Supported filenames:

- `icon.png`
- `logo.png`
- `dark_icon.png`
- `dark_logo.png`
- `[email protected]`
- `[email protected]`
- `[email protected]`
- `[email protected]`

Minimum practical setup:

- `icon.png` for the integration icon
- `logo.png` for the integration logo

Home Assistant 2026.3+ can load these local brand assets directly from the integration.

You can also generate SVG variants with:

```powershell
python tools\generate_brand_svg.py
```
