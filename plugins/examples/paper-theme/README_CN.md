# Paper Theme 示例主题

这是 DiceFrame 的主题示例插件，演示 `theme` 插件如何贡献安全 CSS 变量。

## 打包

```powershell
python scripts\package_plugin.py plugins\examples\paper-theme --overwrite
```

安装并启用后，可以在 WebUI 的“设置 -> 插件 -> 主题”里选择 `Paper Theme`。

主题插件当前只支持 CSS 变量，不支持脚本、Vue 组件或任意 CSS 文件注入。
