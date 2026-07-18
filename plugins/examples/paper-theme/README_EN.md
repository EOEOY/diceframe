# Paper Theme Example

[中文](README_CN.md) | English

This DiceFrame example demonstrates how a `theme` plugin contributes safe CSS custom properties.

## Package

```powershell
python scripts\package_plugin.py plugins\examples\paper-theme --overwrite
```

After installation and enablement, select `Paper Theme` under Settings → Plugins → Themes.

Theme plugins currently support filtered CSS variables only. They cannot inject scripts, Vue components, or arbitrary CSS files.
