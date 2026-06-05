# APP STARTUP SERVICES

**Document Created:** 2026-01-23
**Purpose:** Reference document listing all services that start automatically during app launch
**Main File:** `AGI IN ACTION(BASIC) 2.3.py`

---

## Startup Sequence Overview

The app's `main()` function (starting around line 7243) initializes services in a specific order. Below is the complete list of services that start automatically.

---

## 1. Early Initialization (Pre-Window)

| Order | Service | Location | Description |
|-------|---------|----------|-------------|
| 1.1 | Platform Detection | Line 7244 | Detects OS (Darwin/Windows/Linux) |
| 1.2 | Log Cleanup | Line 7248 | `cleanup_log_files()` removes old logs |
| 1.3 | Browser Cleanup | Line 7251 | `force_close_browsers()` closes leftover browser instances |
| 1.4 | Model Manager Init | Line 7256 | `ModelManager()` for AI model management |
| 1.5 | Auth Key Init | Lines 7259-7269 | Loads or generates authentication key for mobile app |

---

## 2. Window Creation & Basic Setup

| Order | Service | Location | Description |
|-------|---------|----------|-------------|
| 2.1 | Window Creation | Line 7294 | `create_window(model_manager)` |
| 2.2 | Folder Initialization | Line 7310 | `initialize_folders()` creates required directories |
| 2.3 | General Settings Load | Line 7320 | `load_general_settings()` |
| 2.4 | Chat Sync Settings Load | Line 7330 | `load_chat_sync_settings()` |
| 2.5 | Model Switching Settings | Lines 7334-7337 | `load_switching_settings()` |

---

## 3. Vision/Screen Recording Module

| Order | Service | Location | Description |
|-------|---------|----------|-------------|
| 3.1 | Vision Module Init | Line 7347 | `VisionRecordingModule()` if available |
| 3.2 | Auto-Start Thread | Line 7404 | Background thread waits 10s then auto-starts: |
|     | - Continuous Recording | Line 7386 | If `continuous_mode=True` in config |
|     | - Vision RAG Worker | Line 7393 | If `auto_vision_update=True` in config |

**Config File:** `ScreenRecording/ScreenRecordingSettings.json`

---

## 4. API/VPS Configuration

| Order | Service | Location | Description |
|-------|---------|----------|-------------|
| 4.1 | VPS Config Load | Lines 7417-7438 | Loads VPS IP/ports from `BrowsingAgent_Config/vps_connection.json` |
| 4.2 | Model Config Load | Lines 7447-7454 | Loads last used model for CHAT_MODE |

---

## 5. Unified System Initialization

| Order | Service | Location | Description |
|-------|---------|----------|-------------|
| 5.1 | UnifiedSystem Init | Line 7457 | `UnifiedSystem(api_key, model_name)` - Core system |
| 5.2 | Window Reference | Line 7458 | `system.set_window(window)` |

---

## 6. AgentList Tab Initialization

| Order | Service | Location | Description |
|-------|---------|----------|-------------|
| 6.1 | AgentSystem Init | Line 7464 | `AgentSystem()` - Manages agent files |
| 6.2 | Global Dicts Init | Lines 7467-7469 | `scheduled_agents`, `active_agents`, `agent_stop_flags` |
| 6.3 | Agent List Load | Lines 7477-7478 | Loads agents into listbox |
| 6.4 | AgentScheduler Init | Lines 7483-7489 | Creates scheduler with async event loop |
| 6.5 | Scheduler Thread Start | Line 7489 | `agent_scheduler.start_scheduler_thread()` |

**NOTE:** Currently, previously scheduled agents are **NOT** reloaded on startup.
Config files exist in `AgentListTab/AgentConfig/` but are not loaded automatically.

---

## 7. QR API Servers

| Order | Service | Location | Description |
|-------|---------|----------|-------------|
| 7.1 | Both Servers Start | Line 7496 | `qr_api_linux_module_1.start_both_servers()` |
|     | - NGINX Server | | Reverse proxy for HTTPS |
|     | - API Server | | Python API server for mobile app |

---

## 8. Model Display Update

| Order | Service | Location | Description |
|-------|---------|----------|-------------|
| 8.1 | Chat Model Display | Lines 7518-7525 | Updates `-CURRENT_CHAT_MODEL-` |
| 8.2 | Action Model Display | Lines 7527-7531 | Updates `-CURRENT_ACTION_MODEL-` |

---

## 9. WebSocket TTS/STT Server

| Order | Service | Location | Description |
|-------|---------|----------|-------------|
| 9.1 | Whisper STT Load | Line 7541 | `load_whisper_model()` for speech-to-text |
| 9.2 | Kokoro TTS Load | Line 7551 | `load_kokoro_model()` for text-to-speech |
| 9.3 | HTTP Server Start | Line 7561 | `start_http_server()` for audio downloads |
| 9.4 | Cleanup Scheduler | Line 7567 | `start_cleanup_scheduler()` - temp file cleanup every 5 mins |
| 9.5 | WebSocket Server | Lines 7570-7579 | Background thread running async WebSocket server |

**Ports:**
- HTTP Server: `HTTP_PORT`
- WebSocket: `WEBSOCKET_HOST:WEBSOCKET_PORT`

---

## 10. WebSocket Client Configuration

| Order | Service | Location | Description |
|-------|---------|----------|-------------|
| 10.1 | Config Load | Lines 7596-7617 | Loads `websocket_config.json` |
| 10.2 | Auto-Connect | Lines 7620-7628 | Connects if `auto_connect_enabled=True` |

---

## 11. Browser Module Setup

| Order | Service | Location | Description |
|-------|---------|----------|-------------|
| 11.1 | Browser Settings Init | Line 7644 | `browser_module.initialize_browser_settings()` |
| 11.2 | Last Browser Load | Line 7647 | Loads Chrome/Edge settings |
| 11.3 | Browser Path Setup | Lines 7659-7695 | Platform-specific browser path defaults |

---

## 12. RAG Settings Load

| Order | Service | Location | Description |
|-------|---------|----------|-------------|
| 12.1 | RAG Config Load | Lines 7707-7718 | Loads max memories, auto-save interval, etc. |
| 12.2 | Digital Brain Settings | Lines 7715-7718 | Memories per prompt, total active missions |

---

## 13. Scheduled Agents Restore (2026-01-23)

| Order | Service | Location | Description |
|-------|---------|----------|-------------|
| 13.1 | Config Scan | Lines 7728-7820 | Scans `AgentListTab/AgentConfig/` for `*_config.json` files |
| 13.2 | Agent Restore | | For each config: loads task content, calculates next run, calls `appoint_agent()` |
| 13.3 | Display Update | | Scheduler auto-updates GUI via `-UPDATE_SCHEDULED_DISPLAY-` event |

**Behavior:**
- **One-time agents:** Restored only if original start datetime is still in the future
- **Repeat agents:** Start 30 seconds after app launch, then repeat at configured interval
- Skips agents with missing/empty task files
- Logs restoration status for debugging

---

## 14. OpenClaw AutoStart (2026-02-12)

| Order | Service | Location | Description |
|-------|---------|----------|-------------|
| 14.1 | Config Check | Line 7957 | Checks `OPENCLAW_AVAILABLE` flag |
| 14.2 | AutoStart Call | Line 7959 | `autostart_openclaw_services(window)` |
| 14.3 | Gateway Start | Background thread | Starts OpenClaw Gateway on port 18789 |
| 14.4 | TUI Start | Background thread | Starts OpenClaw TUI (after gateway is up) |

**Behavior:**
- Only runs if `OPENCLAW_AVAILABLE` is True (bridge module loaded successfully)
- Reads `OpenClaw/openclaw_bridge_config.json` — only starts services if `autostart: true`
- Runs in a **background thread** so the GUI doesn't freeze during startup
- Gateway starts first, waits 2 seconds, then TUI starts
- If Gateway fails, TUI startup is skipped
- Logs status to console: `[STARTUP] OpenClaw Gateway: ...` and `[STARTUP] OpenClaw TUI: ...`
- Also logs to the OpenClaw tab's log display

**Config File:** `OpenClaw/openclaw_bridge_config.json`
```json
{
  "enabled": true,
  "autostart": true,
  "timeout": 300
}
```

---

## 15. Main Event Loop Start

| Order | Service | Location | Description |
|-------|---------|----------|-------------|
| 15.1 | Return Key Binding | Line 7704 | `window.bind('<Return>', 'Send')` |
| 15.2 | Event Loop | Line 7965 | `while True: event, values = window.read(timeout=1000)` |

---

## Background Threads Summary

| Thread | Purpose | Daemon | Started At |
|--------|---------|--------|------------|
| Cleanup Scheduler | Temp file cleanup (5 min interval) | Yes | Line 379 |
| Screen Recording Auto-Start | Delayed auto-start of recording services | Yes | Line 7404 |
| WebSocket Server | TTS/STT WebSocket server | Yes | Line 7575 |
| AgentScheduler Event Loop | Async scheduler for agents | Yes | Line 7489 (via `start_scheduler_thread()`) |

---

## Scheduled Agents Config Reference

### Config File Structure
**Location:** `AgentListTab/AgentConfig/{Agent Name}_config.json`

```json
{
  "schedule_type": "repeat",       // "one-time" or "repeat"
  "start_date": "2025-12-19",      // YYYY-MM-DD
  "start_time": "04:03:00",        // HH:MM:SS
  "hours": 24,                     // Repeat interval hours
  "minutes": 0,                    // Repeat interval minutes
  "seconds": 0,                    // Repeat interval seconds
  "provider": "LM Studio",         // AI provider
  "model_name": "qwen/qwen3-vl-30b" // Model name
}
```

### Restoration Logic
1. Scan config folder for `*_config.json` files
2. Extract agent name from filename
3. Load task content from `AgentList/{agent_name}.txt`
4. Calculate next run time:
   - **One-time:** Use original datetime (skip if passed)
   - **Repeat:** Now + 30 seconds (allows services to stabilize)
5. Call `agent_scheduler.appoint_agent()` to restore
6. GUI auto-updates via scheduler event

---

## Related Files

| File | Purpose |
|------|---------|
| `AgentListTab/agent_list.py` | AgentSystem, AgentScheduler classes |
| `AgentListTab/AgentList/*.txt` | Agent task content files |
| `AgentListTab/AgentConfig/*.json` | Agent schedule configurations |
| `qr_api_linux_module_1.py` | QR API server module |
| `browser_module.py` | Browser settings and control |
| `ScreenRecording/ScreenRecordingSettings.json` | Screen recording config |
| `websocket_config.json` | WebSocket client config |
| `OpenClaw/openclaw_bridge.py` | OpenClaw bridge module |
| `OpenClaw/openclaw_bridge_config.json` | OpenClaw checkbox/timeout persistence |
