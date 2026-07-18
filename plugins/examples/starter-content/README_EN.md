# Starter Content Example

[中文](README_CN.md) | English

This DiceFrame `content-pack` example contributes a rule, world template, character template, NPC, item, spell, and class.

## Package

```powershell
python scripts\package_plugin.py plugins\examples\starter-content --overwrite
```

The zip is written to `dist/plugins/` and can be installed under Settings → Plugins → Install plugin.

## Current Behavior

- Rules appear in the rule list.
- World templates appear during game creation.
- Character templates can be imported into the character-card library from plugin settings.
- NPCs, items, spells, and classes can be imported into a selected lorebook.

This example starts no background process and makes no external network request.
