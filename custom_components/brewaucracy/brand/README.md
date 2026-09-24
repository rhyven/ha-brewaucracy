# Brand images

Home Assistant 2026.3 and later serve these in preference to the brands CDN.
Older versions ignore this directory.

Present:

| File | Size |
| --- | --- |
| `icon.png` | 256×256, square |

Optional additions, all PNG:

| File | Size |
| --- | --- |
| `icon@2x.png` | 512×512 — re-export from the source SVG rather than upscaling `icon.png` |
| `logo.png` / `logo@2x.png` | landscape; omit entirely and Home Assistant falls back to the icon |
| `dark_icon.png` / `dark_logo.png` | dark-theme variants |
