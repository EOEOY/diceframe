# QQ / NapCat Plugin

[中文](README_CN.md) | English

This package contains the manifest and settings documentation for DiceFrame's built-in QQ/NapCat adapter. Its runtime code is supplied by the main DiceFrame application.

1. In NapCat, open Network Settings → Network Configuration → WebSocket Server, enable it, and note the port and access token.
2. Enter those connection values on the DiceFrame plugin settings page and enable the plugin.
3. Copy the Bot binding command from the GM game page and send it to the target group.
4. Players claim a character with `@Bot 加入 CharacterName`, then submit natural-language actions.

The built-in plugin does not require a manually entered DiceFrame Bot API Token. DiceFrame generates and injects it automatically. Plugin settings only need the NapCat WebSocket host, port, and access token.

Common commands:

- `@Bot 帮助`: show available commands.
- `@Bot 绑定 <game_key> <one-time-code>`: bind the current Web game to the group; the code expires immediately after success.
- `@Bot 邀请`: send the Web join link and a one-image new-player guide.
- `@Bot 邀请 @player` / `@Bot 邀请我`: keep the public group link and also attempt a direct message. If direct messaging fails, the group receives a temporary-session/friendship hint and the public-link fallback.
- `@Bot 新建角色` / `@Bot 车卡`: send character-creation guidance and the creation entry point in the group.
- `@Bot AI车卡`: when AI-assisted creation is enabled, collect a description in direct messages, generate a draft for confirmation, then post the public draft to the group.
- `@Bot 加入 CharacterName`: claim an existing Web character.
- `@Bot 前情`: show the public recap and recent turns.
- `@Bot 地图`: show the current scene and known lorebook location links.
- `@Bot 状态`: show the claimed character's HP, gold, inventory, and related summary.
- `@Bot 感知`: send recent character-private perceptions by direct message.
- `@Bot 支付`: send pending payment confirmations by direct message.
- `@Bot 确认支付` / `@Bot 拒绝支付`: accept or reject a pending payment.
- `@Bot 掷骰`: confirm an action that is waiting for dice.
- `@Bot 推进` / `@Bot 下一轮`: let the GM or an authorized account force the round forward.
- `@Bot 暂离` / `@Bot 回来`: stop or resume blocking the round. A GM may target a named character.
- `@Bot <natural-language action>`: submit an action. If it starts GM generation, the Bot first reports that the GM is thinking.

Without a public Web address, invite, character-creation, and map commands still return readable group instructions or cards. With a public address they also include clickable links.

AI-assisted character creation is enabled by default but starts only after the explicit `AI车卡` command. It uses the separate character-generation endpoint, does not enter campaign context or turn logs, and does not create a character automatically. The player confirms a public draft; the GM may edit it later in the Web character page.

Away characters remain with the party but do not count toward pending actions. AI context marks them as following the group without initiating major decisions. `@Bot 回来` restores normal participation.

Only the bound GM may force progression by default. Add assistant GMs or trusted player account IDs under the plugin's authorized progression accounts, one ID per line. NapCat normally uses QQ numbers.

Image-card cache:

- Help, status, and character-guide images are temporarily stored under `data/bot/cards`.
- Settings control retention time and maximum count; creating a card removes old `card_*.png` files.
- The settings page can clear those temporary PNG files immediately without deleting saves, character cards, or unrelated images.
