# Starter Content 示例内容包

这是 DiceFrame 的内容包示例插件，演示 `content-pack` 如何贡献规则、世界模板、角色模板、NPC、道具、法术和职业。

## 打包

```powershell
python scripts\package_plugin.py plugins\examples\starter-content --overwrite
```

生成的 zip 位于 `dist/plugins/`，可以在 WebUI 的“设置 -> 插件 -> 安装插件”里安装。

## 当前效果

- 规则会出现在规则列表。
- 世界模板会出现在创建游戏的世界模板列表。
- 角色模板可从插件设置页导入角色卡库。
- NPC、道具、法术、职业可从插件设置页导入指定世界书。

此示例不启动后台进程，也不访问外部网络。
