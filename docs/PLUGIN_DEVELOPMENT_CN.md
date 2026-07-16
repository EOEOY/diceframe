# DiceFrame 插件开发指南

本指南适用于 QQ、Discord、Telegram 等外部渠道插件。首个参考实现位于 `src/bots/qq/`。

## 1. 插件边界

- 插件是由主服务托管生命周期的独立进程，不与 Web 服务共享内存。
- 插件只调用 `/api/` HTTP 契约，禁止直接读取 `data/` 存档。
- 插件禁止 `import src.webui`；缺少能力时按 `routes -> api -> services -> core` 补正式接口。
- 平台账号与游戏角色的映射只保存在插件自己的数据目录。
- 骰点、状态变化和剧情推进由服务端完成，插件只做协议转换与展示。

## 2. 推荐目录

```text
src/bots/<platform>/
  __init__.py
  config.py       # 环境变量/启动参数及校验
  transport.py    # 平台连接、重连、心跳和发送
  api_client.py   # 对 DiceFrame HTTP API 的唯一访问入口
  store.py        # 平台会话映射、游标和消息去重
  adapter.py      # 平台事件入口、权限/会话调度和主命令路由
  command_matchers.py  # 命令谓词/意图匹配
  message_utils.py     # 平台消息段解析
  presenters.py        # 文案和卡片内容组装
  delivery.py          # 文本/图片发送、降级、限速和缓存清理
  *_flow.py / *_commands.py  # 车卡、行动、同步、玩家工具等分域流程
  main.py         # 独立进程入口
tests/test_<platform>_bot.py
```

`adapter.py` 不应继续堆成巨型单文件；新增命令、卡片、同步、车卡向导等功能时，优先放入对应分域模块，再由 adapter 调度。展示层生成图片卡片时，按实际像素宽度处理换行、缩进、列宽和省略号；不要只按字符数截断，也不要把缩进拼进文本后再按未缩进宽度测量。

## 3. 插件包标准

DiceFrame 插件以 `plugins/<plugin-id>/` 为安装单位。插件可以随源码仓库内置，也可以打成 zip 后在 WebUI“设置 -> 插件”中安装。

最小插件包结构：

```text
<plugin-id>/
  plugin.json
  config.schema.json
  README_CN.md
```

zip 包允许两种结构：

```text
plugin.json
config.schema.json
README_CN.md
```

或：

```text
<plugin-id>/
  plugin.json
  config.schema.json
  README_CN.md
```

安装器会拒绝包含多个 `plugin.json`、绝对路径、`..` 路径穿越和符号链接的 zip 包。覆盖同 ID 插件必须在 WebUI 显式勾选“覆盖同 ID 插件”。

### 3.1 plugin.json

`plugin.json` 是插件清单，必须是 UTF-8 JSON：

```json
{
  "schema_version": 1,
  "id": "qq-napcat",
  "name": "QQ / NapCat",
  "version": "1.0.0",
  "description": "通过 NapCat WebSocket 服务器将群聊连接到 DiceFrame。",
  "entrypoint": ["{python}", "-m", "src.bots.qq.main"],
  "config_schema": "config.schema.json",
  "capabilities": ["channel.group", "channel.private", "game.action"],
  "docs": "README_CN.md"
}
```

字段约定：

- `schema_version`：当前固定为 `1`。
- `id`：稳定插件 ID，必须匹配 `^[a-z0-9]+(?:-[a-z0-9]+)*$`，且安装后目录名必须等于该 ID。
- `name` / `version` / `description`：展示信息。
- `entrypoint`：插件进程启动命令，字符串数组。`"{python}"` 会替换为当前 Python 解释器。
- `config_schema`：配置 schema 文件路径，必须位于插件目录内。
- `capabilities`：声明能力，供用户和后续权限模型识别。只声明实际需要的能力。
- `docs`：插件目录内的说明文档路径。

插件进程工作目录是 DiceFrame 项目根目录。插件不得依赖当前工作目录写入运行数据；运行数据应写入宿主通过环境变量传入的数据路径，或写入 `data/plugins/<plugin-id>/` 下的专属目录。

### 3.2 config.schema.json

配置 schema 使用受限 JSON Schema 子集：

- 顶层必须是 `{"type": "object", "properties": {...}}`。
- 支持字段类型：`boolean`、`string`、`number`、`integer`、`array`。
- 支持 UI 控件：`switch`、`text`、`secret`、`number`、`select`、`string-list`。
- 敏感字段使用 `ui.sensitive: true` 或 `ui.control: "secret"`；敏感值保存到 `data/plugins/<id>/secrets.json`，公开 API 只返回掩码。
- 普通字段保存到 `data/plugins/<id>/config.json`。
- `ui.env` 可把配置注入插件进程环境变量。
- `ui.generate: true` 只用于敏感字段；启动插件时如果为空，宿主会自动生成令牌。

示例：

```json
{
  "type": "object",
  "required": ["enabled", "host", "port"],
  "properties": {
    "enabled": {
      "type": "boolean",
      "title": "启用适配器",
      "default": false,
      "ui": {"control": "switch", "order": 10}
    },
    "host": {
      "type": "string",
      "title": "主机地址",
      "default": "127.0.0.1",
      "ui": {"control": "text", "env": "NAPCAT_HOST", "order": 20}
    },
    "token": {
      "type": "string",
      "title": "访问令牌",
      "ui": {"control": "secret", "sensitive": true, "env": "NAPCAT_TOKEN", "order": 30}
    }
  }
}
```

### 3.3 安装与卸载语义

- 安装：WebUI 上传 zip，宿主先解压到临时目录，校验 `plugin.json` 和 `config.schema.json` 后再移动到 `plugins/<id>/`。
- 覆盖安装：若同 ID 插件已存在，必须显式覆盖；宿主会先停止旧插件，再替换目录。
- 卸载：宿主先停止插件，再删除 `plugins/<id>/`。默认保留 `data/plugins/<id>/`，避免误删令牌、绑定和会话映射。
- 重新安装同 ID 插件会自动复用保留的配置数据。

### 3.4 插件商店收录

官方社区索引仓库为 `https://github.com/EOEOY/diceframe-plugins`。WebUI “插件 -> 插件商店”默认读取该仓库 `main` 分支的 `plugin_details.json`，并通过镜像源自动重试。

最小商店条目：

```json
{
  "id": "example-plugin",
  "repository_url": "https://github.com/username/example-plugin",
  "branch": "main",
  "tags": ["adapter"],
  "manifest": {
    "schema_version": 1,
    "id": "example-plugin",
    "name": "示例插件",
    "version": "0.1.0",
    "description": "一句话说明插件用途",
    "capabilities": ["bot-adapter"],
    "docs": "README_CN.md"
  }
}
```

商店安装默认会下载 `repository_url` 对应 GitHub 仓库的分支 zip。若插件仓库不是“仓库根目录即插件目录”的结构，应提供 `package_url`，指向已经打包好的 DiceFrame 插件 zip。商店安装允许 GitHub 自动 zip 的顶层目录名与插件 ID 不一致，但包内仍必须只有一个有效 `plugin.json`，且 `plugin.json.id` 必须等于商店条目 `id`。

镜像源只用于提高 GitHub raw/下载可用性，不作为可信来源。安装前宿主仍会做路径越界、符号链接、manifest、schema、插件 ID 等本地校验。

## 4. 接入步骤

1. 在 `src/bots/<platform>/` 完成独立适配进程，复用现有 HTTP Bot 契约。
2. 在 `STATE` 增加 `<platform>_bot_enabled` 和连接配置；令牌等敏感字段进入 `secrets.json`，公开配置只返回掩码。
3. 为插件实现 `_start_*`、`_stop_*`、`_restart_*`；主服务启动时恢复，配置变化时重启，cleanup 时回收。
4. 在设置“插件”页添加独立插件项，至少包含开关、运行状态、连接配置、使用说明和错误提示。
5. 为绑定、身份校验、消息去重、重连和启停生命周期添加测试，再运行完整测试集。

## 5. HTTP 鉴权

- `X-Bot-Token`：证明调用方是已启用的受信插件。
- `X-Bot-Actor`：声明本次请求代表的游戏内 `user_id`。
- 后端必须校验 Actor 属于目标游戏；服务令牌不能代替玩家身份。
- 游戏绑定凭证由 GM 在当前游戏中生成，不能通过普通游戏详情接口暴露。

## 6. 生命周期要求

- 插件关闭时，进程和 Bot API 应同时停用。
- 插件开启但平台暂不可达时，应在子进程内退避重连，不能阻塞 Web 服务启动。
- 修改连接参数后自动重启插件，避免要求用户手动重启整个游戏。
- 主服务退出时先终止插件，超时后再强制回收。
- 运行状态不写入配置文件；启用状态和连接配置需要持久化。

## 7. 发布检查

- 不复制许可证不兼容的第三方适配器源码。
- zip 包只包含一个插件，不包含 `__pycache__`、日志、临时文件、私有账号或本机绝对路径。
- `plugin.json` 的 `id`、目录名和安装包顶层目录保持一致。
- `config.schema.json` 的敏感字段必须标记为 secret，不把 token 放进普通配置。
- 不记录完整令牌、玩家私密消息或角色感知内容。
- 消息事件必须用平台 `message_id` 去重，并持久化有限窗口。
- HTTP 字段保持向后兼容；新增平台不得要求 Web 前端改用平台专属字段。
- 图片卡片必须覆盖长中文、中英文混排、首行缩进、长标题/页脚等渲染测试。
- 运行 `py_compile`、平台插件测试和 `pytest -q`。
