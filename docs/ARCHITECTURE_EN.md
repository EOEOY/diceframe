# DiceFrame Architecture Guidelines

[中文](ARCHITECTURE_CN.md) | English

> These guidelines define code organization and coupling boundaries for the Vue frontend, WebUI backend, and plugin host. New features, refactors, and plugin integrations should follow them.

## Scope

This document describes DiceFrame's main layers, dependency direction, extension points, and common refactoring boundaries. It is intended for maintainers, plugin authors, and contributors who need to understand the project structure.

## 1. Layers and Dependency Direction

```text
routes/                         HTTP entry layer
  ↓
api.py (WebAPI)                delegation and shared helpers
  ↓
services/                      business logic
  ↓
engine/ generation/ lorebook/ memory/ rules/   core domains
```

Dependencies only point downward. Core domains must never import `src.webui`; doing so creates a reverse dependency that must be refactored.

The frontend and channel plugins are both HTTP consumers:

```text
frontend-v2 (Vue GM + Player) ---- HTTP/SSE ---- routes
plugins/* -> src/bots/* ---------- HTTP -------- routes
src/plugin_host ------------------ process lifecycle only
```

`frontend-v2/` builds the production application into `static-v2/`. The backend serves this single Vue application. The legacy native frontend and fallback entry points have been removed; all new UI work belongs in Vue.

## 2. Layer Responsibilities

### frontend-v2/

- Vue 3, TypeScript, and Vite. The Vite base is `/v2-assets/`; production output goes to `static-v2/`, served by the backend at `/v2-assets/{file}`.
- Three structural layers: `features/` for page views, `components/` for shared UI (`common/`, `play/`, and `admin/`), and `api/` + `stores/` + `composables/` for data and behavior. Components do not assemble URLs, interpret save JSON, or call `fetch` directly.
- Naive UI theming lives in `styles/theme.ts`; shared CSS tokens live in `styles/tokens.css`. Icons use `@vicons/ionicons5` with `NIcon`, not emoji fallbacks.
- Pinia stores own shared game, settings, and UI state (`useGame`, `useSettingsStore`, `useToast`, `useConfirm`, and `useTheme`). Components must not maintain independent copies.
- `vue-router` owns page navigation: `/login`, `/overview`, `/play`, `/settings`, `/characters`, `/lorebook`, `/memory`, `/logs`, `/rules`, `/create`, and `/join`. Internal refs are not substitutes for routing. The root route dispatches by the `game`, `user`, and `share` query parameters.
- `composables/` contains reusable behavior such as `useNaiveBridge`, `useToast`, `useConfirm`, `useTheme`, and `useGame`.
- `api/types.ts` defines strong DTO types for backend contracts. Components should not use `any` for normal API data.
- `api/` owns the HTTP/SSE client (`api()` and `gameEventSource()`) and DTOs.
- GM/player differences use permission props, backend authorization, and `solo_mode` branches. Do not duplicate core play components.
- Live state uses targeted SSE updates through `useGame.connect`; do not rebuild the page through whole-page polling.
- Events must not force-scroll when the user is reading older messages, or reset dialogs, collapsed panels, or input state.
- Do not hide errors with fallback defaults or silent `try/except`. Keep templates readable, move substantial `<script setup>` logic into composables or stores, and keep components thin.
- The standard layout uses `NLayoutHeader` and a horizontal `NMenu`, with brand, navigation, and current-table status. `ThemeToggle` is globally floating. Mobile navigation scrolls horizontally without clipping. Fullscreen login, join, and shared-player pages omit global navigation.
- List pages use responsive card grids (`repeat(auto-fill,minmax(240px,1fr))`) and the shared card styles instead of separator-only lists. `SkillEditor` is reused by character flows. `GameSidebar` collapse state persists in `localStorage`.
- `--ink` is a light input/card background in light mode and must not be used for text. Use `--text`, `--muted`, or `--gold-2`, and verify light-theme contrast when adding colors.

### routes/<domain>.py

- Decode request parameters, body data, and session state.
- Call `api.xxx()`.
- Encode JSON or SSE responses.
- Contain no business logic and do not manipulate `GameInstance`, `LorebookStore`, or files directly.
- Shared route helpers belong in `routes/_common.py`, including `_get_api`, `_require_confirmed_request`, and `MAX_*` constants.
- Each domain exports `register_xxx(app)`, called by `web_server.register_routes`.
- HTTP endpoints are multi-consumer contracts for the web frontend and channel adapters. Keep field changes backward compatible.

### api.py (WebAPI)

- Acts as a pure delegation layer. Normal methods are one-line calls such as `return domain.func(self, ...)`.
- Holds only cross-domain helpers such as `_parse_key`, `_load_rule_for_game`, and `_load_rule_by_id`.
- Owns runtime state including `_reg`, `_lore`, `_mem`, `_handler`, `_llm_client`, `_worlds_dir`, and `_rules_dir`.
- Services access those resources through `api._xxx`.

### services/<domain>.py

- Contains business logic.
- Uses module-level functions with signatures such as `def func(api: "WebAPI", ...)`.
- Services are WebAPI's friend layer and may access private runtime fields such as `api._reg` and `api._lore`.
- Use `TYPE_CHECKING` imports to avoid cycles:

```python
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.webui.api import WebAPI
```

- Cross-domain pure constants and pure functions belong in `services/_common.py`.

### Core domains

`engine/`, `generation/`, `lorebook/`, `memory/`, and `rules/` contain domain logic without WebUI dependencies. Services may import them directly.

## 3. Service Function Conventions

```python
def list_games(api: "WebAPI") -> dict[str, Any]:
    active = []
    for inst in api._reg.list_all():
        active.append({...})
    return {"games": active, "total": len(active)}
```

- The first argument is named `api` and annotated as the string `"WebAPI"` together with `from __future__ import annotations`.
- Runtime state is accessed through `api._xxx`.
- Return values must be JSON-serializable.
- Domain-private helpers use an underscore prefix and are not exported.

## 4. Cross-Domain Calls

When service A needs service B, it must call `api.b_func()`. It must not import a sibling service directly.

| Correct | Incorrect |
|---------|-----------|
| In `games.py`: `created = await api.create_player(...)` | In `games.py`: `from src.webui.services.characters import create_player` |

Direct sibling imports create a mesh of service dependencies. WebAPI delegation preserves the direction `routes -> api -> services`. WebAPI must expose a delegate for each service operation that is used across domains.

## 5. Where Shared Helpers Belong

```text
How many domains use this helper?
├─ Two or more → Does it depend on API state?
│                ├─ Yes → Keep it as a WebAPI method or staticmethod in api.py
│                └─ No  → Put it in services/_common.py
└─ One domain   → Make it a private helper in that service
```

Examples of WebAPI helpers include `_parse_key` and `_load_rule_by_id`. Pure shared values such as `_GAME_KEY_SEP` belong in `services/_common.py`. A helper used only by maps belongs in `maps.py` with an underscore prefix.

Do not redefine the same constant in several services, and do not leave a single-domain helper in the shared API layer.

## 6. Adding a Feature Domain

For a new domain such as quests:

1. Put pure domain behavior in `engine/`, without WebUI dependencies.
2. Add business functions to `services/quests.py`.
3. Add one-line WebAPI delegates in `api.py`.
4. Add HTTP handlers and `register_quests(app)` in `routes/quests.py`.
5. Call `register_quests(app)` from `web_server.register_routes`.

Validate each stage with `py_compile`, `pytest -q`, and the relevant `audit_*` scripts under `scripts/`.

## 7. Extension Points and Plugins

### 7.1 Data-Driven Extension Points

| Extension | Location | Discovery |
|-----------|----------|-----------|
| Rules | `rules/*.json` and `rules/*_<suffix>.json` | `RuleSystem.path_for(rules_dir, rule_id, language)` selects the language file and falls back to Chinese |
| World templates | `templates/worlds/*.json` | Loaded by `world_id` from `_worlds_dir` |
| Character-card library | `data/character_cards.json` | Runtime data; never committed |

Adding a valid file is enough for discovery.

### 7.2 Code Extension Points

New service/route domains, tag handlers, and LLM generation strategies follow the checklist in section 6.

### 7.3 Plugin Layer

DiceFrame plugins declare their type, capabilities, permissions, and contributions in `plugin.json`. The host supports discovery, install/uninstall, settings, store updates, secret storage, static contribution registration, and lifecycle management for supported process plugins.

Channel adapters such as QQ/NapCat consume the same HTTP API as the web frontend. Content packs can register rules, worlds, characters, NPCs, items, spells, and classes. Themes provide filtered CSS variables. Map packs contribute locations and static map assets. Import/export, Provider, and tool types remain reserved and have no store-installable runtime yet. See [PLUGIN_DEVELOPMENT_EN.md](PLUGIN_DEVELOPMENT_EN.md).

```text
plugins/<plugin-id>/
  plugin.json
  config.schema.json
  README.md or README_CN.md
src/plugin_host/
src/bots/<platform>/
  adapter.py
  command_matchers.py
  message_utils.py
  presenters.py
  delivery.py
  *_flow.py / *_commands.py
  main.py
```

Integration rules:

- `plugin_type` distinguishes `channel-adapter`, `content-pack`, `theme`, `map-pack`, `import-export`, `provider`, and `tool`.
- Unknown permissions are rejected and declared permissions appear in settings.
- Store installation resolves the latest stable GitHub Release to an exact commit and validates the manifest, type, and effective permissions. Declarative plugins auto-update only without runtime or permission expansion; process or expanding updates require confirmation.
- Local/private distribution uses `.dfplugin`. Managed processes declaring `diceframe.http` receive a plugin-specific host token; the global Bot API token is for external programs only.
- `content-pack`, `theme`, and `map-pack` may be declarative without a background process. `channel-adapter` is the currently supported process type. `import-export`, `provider`, and `tool` are reserved and cannot be installed from the store.
- Contributions are registered only while a plugin is enabled and must remain inside its directory.
- Content imports copy selected data into the user's card library or lorebook, so imported user data does not retain a file dependency on the plugin.
- Themes may provide filtered CSS variables, not scripts, components, or arbitrary CSS.
- Map asset URLs expose only declared contribution files.
- Channel adapters never import `src.webui` or call services directly; they use route-level HTTP APIs.
- HTTP fields must remain compatible for all consumers.
- Missing adapter capabilities should be added as general route APIs, not reimplemented inside a bot.
- `adapter.py` remains a thin event and session coordinator. Command matching, presentation, delivery, sync, character creation, and player tools belong in focused modules.
- Platform presentation must measure real pixels and capabilities; indentation, wrapping, columns, and ellipsis are layout parameters.
- P0 actions use synchronous HTTP responses. Reliable asynchronous delivery requires a persistent cursor, not ordinary polling.
- Platform user-to-game mappings live on the adapter side.
- Multiple adapters run as independent processes against the same web service.
- The host manages process start, stop, configuration, and cleanup. Reconnects, message deduplication, and platform sessions belong to the adapter.
- New plugins add a manifest, schema, and optional process without platform-specific lifecycle code in `web_server.py` or hard-coded UI settings.
- Normal settings are stored in `data/plugins/<id>/config.json`; secrets are stored separately in `secrets.json` and masked by public APIs.

### 7.4 Page Entry Points

| Path | Implementation |
|------|----------------|
| `/` | Vue application entry, serving `static-v2/index.html` |
| `/player`, `/player.html` | Same Vue entry in player mode through query parameters |
| `/v2-preview/` | Preview/debug alias for the same entry |
| `/v2-assets/{file}` | Built JS/CSS assets |
| `/login` | Vue login route through the same entry |

The router uses `createWebHashHistory`, producing URLs such as `/#/overview` and `/#/play?game=KEY&share=1&user=UID`. Hash routing avoids server-side SPA fallback requirements. `shareQuery()` and `gameEventSource()` read query data from `location.hash`.

Shared-player identity is constrained by query parameters and backend sessions. A GM opening a player link is a preview by default; delegated writes require `delegate=1`.

### 7.5 Validation Commands

```powershell
pytest -q
cd frontend-v2
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build
npm.cmd run test:e2e
```

## 8. Naming Conventions

| Object | Convention | Example |
|--------|------------|---------|
| Service file | Domain noun | `worlds.py`, `maps.py` |
| Service function | `verb_object` | `list_games(api, ...)` |
| WebAPI delegate | Same name as service function | `list_games(self, ...)` |
| Route handler | `api_verb_object` | `api_list_games(request)` |
| Register function | `register_domain` | `register_games(app)` |
| Private helper | Underscore prefix | `_find_map_anchor` |

## 9. Common Anti-Patterns

| Incorrect | Correct |
|-----------|---------|
| A service imports a sibling service | Call the WebAPI delegate |
| A core domain imports `src.webui` | Keep core domains independent |
| Routes contain business logic | Routes only decode and encode |
| A one-domain helper remains in `api.py` | Move it to that service |
| Constants are repeated across services | Put pure shared values in `_common.py` |
| `try/except pass` hides an error | Handle, log, or propagate it explicitly |
| A WebAPI delegate contains logic | Keep it a one-line delegation |

## 10. Avoiding Duplicate Implementations

Search for an existing entry point with the same business meaning before adding a feature or refactoring. Similar syntax is not enough reason to abstract code with different semantics.

| Business meaning | Preferred implementation | Avoid |
|------------------|--------------------------|-------|
| Rule paths and loading | `RuleSystem.path_for`, `load_for_world`, `load_for_world_path`, and WebAPI rule helpers | Repeated `rules_dir / f"{rule_id}.json"` logic that ignores language |
| World loading | `GameFactory.load_world_template` and a shared WebAPI/service helper | Repeated path construction and `json.loads` |
| Character-sheet access | `GameInstance.get_character_sheet(uid)` and focused GameInstance methods | Repeated chained dictionary access |
| Alive/dead checks | `alive_players`, `is_alive(uid)`, and `is_dead(uid)` | Independent interpretations of `deceased` |
| HP, gold, and resources | Core `character_utils` helpers | Repeated clamping, payment, healing, death, or revival rules |
| External HTTP clients | Reuse a lifecycle-owned `aiohttp.ClientSession` and close it during cleanup | A new session for every request |
| Tag and numeric parsing | Small `_parse_*` helpers that preserve warning context | Repeated split/int blocks with silent exceptions |

Guidelines:

1. If the same business meaning appears twice, prefer a helper owned by that domain.
2. Cross-domain stateful helpers belong in WebAPI; pure domain rules belong in core; single-domain helpers stay private to that domain.
3. An abstraction should reduce semantic divergence or bug surface, not merely remove a few similar lines.
4. Reuse an existing helper before introducing a second implementation.
5. If ownership is unclear, start a design discussion and state the evidence and recommended option.

Some similar-looking code should remain separate: custom serializers with different compatibility behavior, small pure functions that avoid heavy dependencies, and platform/protocol mappings with different consumer contracts.

## 11. Refactoring Checklist

When splitting a large module:

1. Identify domain boundaries around operations on the same entity.
2. Move domain behavior into `services/<domain>.py` with `func(api, ...)` signatures.
3. Route cross-domain calls through `api.xxx()`.
4. Place helpers using the decision tree in section 5.
5. Reduce WebAPI methods to one-line delegates.
6. Scan for duplicate business semantics.
7. Run `py_compile`, integrity checks, `pytest -q`, relevant `audit_*` scripts, and `git diff -w`.

## 12. When These Guidelines Do Not Decide the Answer

For coupling boundaries, domain ownership, or conflicting rules not clearly covered here, open a design discussion in an Issue, Pull Request, or maintainer channel before implementation. State the current structure, viable alternatives, coupling effects, and recommended direction so the decision is reviewable and does not create accidental long-term dependencies.
