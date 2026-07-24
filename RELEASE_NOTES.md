# DiceFrame v1.4.1

## 中文

本版本修复了机器人桥接的玩家入口链接和移动端游玩页布局问题。

### 修复

- 机器人在群聊中给出的玩家入口链接现在优先使用 DiceFrame 服务端配置的公开地址，避免暴露内部地址；插件显式配置的公开地址仍具有最高优先级。
- 修复移动端游玩页在内容较长时被截断、无法滚动的问题；时间线和操作区在小屏上可正常显示与滚动。

## English

This release fixes bot bridge join links and the mobile play page layout.

### Fixes

- Join links returned by the bot in group chat now prefer the public address configured on the DiceFrame server, instead of leaking the internal address. An explicit plugin override still takes the highest priority.
- Fixed the mobile play page clipping long content and blocking scrolling; the timeline and controls now display and scroll correctly on small screens.
