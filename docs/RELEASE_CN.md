# 发布与打包

中文 | [English](RELEASE_EN.md)

本文档给维护者使用，说明如何生成 GitHub Release 附件。

## 本地生成 Windows 包

发布前先确认版本号：

```text
src/version.py
```

然后在干净的公开仓库目录运行：

```powershell
python scripts\build_release.py
```

生成物会放到：

```text
dist/DiceFrame-v版本-windows.zip
```

如果要生成“解压即用”的 Windows 便携包，运行：

```powershell
python scripts\build_portable.py
```

生成物会放到：

```text
dist/DiceFrame-v版本-windows-portable.zip
```

这个 zip 包包含：

- Python 后端源码
- Vue 前端源码
- 已编译好的 `static-v2/`
- `web_ui.bat`
- Docker 文件、模板、插件、用户文档

便携包额外包含：

- `DiceFrame.exe`
- Windows 嵌入式 Python
- 已安装好的后端运行依赖

便携包用户不需要安装 Python，也不需要安装 Node.js。

便携构建会校验嵌入式 Python 和用于引导安装的 pip wheel 的 SHA-256，并使用 `requirements-portable.lock` 中固定版本、固定哈希的 Windows wheel。引导 pip 不会先安装 setuptools/wheel 等未锁定工具。任何下载内容与锁定值不一致时都会停止构建。修改 Python 版本或依赖时，必须在审阅来源后同步更新 URL、版本和哈希，不能通过关闭校验来让发布通过。

不会包含：

- `data/`
- `.env`
- 日志
- 测试目录
- `node_modules`
- 本地 IDE 与辅助工具配置目录

发布脚本还会识别并排除旧版本遗留在 `templates/` 下的自定义世界和规则。用户内容只应保存在 `data/templates/`，不能进入公开发布包。

如果只是本地试包，当前工作区有未提交改动时可以运行：

```powershell
python scripts\build_release.py --allow-dirty
```

正式发布不要用 `--allow-dirty`。

## GitHub 自动生成

仓库包含 `.github/workflows/release.yml`。推送 `v*` 标签后，GitHub Actions 会自动：

1. 安装 Python 和 Node.js。
2. 构建前端。
3. 生成 `DiceFrame-v版本-windows.zip`。
4. 把 zip 挂到对应 GitHub Release。
5. Windows runner 会额外生成 `DiceFrame-v版本-windows-portable.zip`。

工作流中的 GitHub Actions 使用完整 commit SHA 固定；升级 Action 时应先确认官方版本标签所指向的提交，再提交 SHA 变更。

命令示例：

```powershell
git tag v0.1.0
git push origin v0.1.0
```

Release 正文就是应用内“更新日志”的来源。发布后请到 GitHub Release 页面填写更新内容。
