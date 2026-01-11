# GODs Strongest Soldier AI Chatbot (GSS1147) — Self‑Automated Local Runtime

This bundle runs **self‑automated** by default:
- continuously ingests supported files from watch folders (incremental; sqlite indexed),
- optionally performs best‑effort fine‑tuning steps when enough buffer data exists,
- runs periodic health checks and emits **patch proposals** (safe; no auto-apply),
- supports an optional PyQt5 GUI.

## Requirements
- Python 3.10+ recommended (Windows 10 OK)

## Install (Windows PowerShell)
```powershell
cd X:\gss1147\gss_ai_system
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### Optional (GUI)
```powershell
pip install -r requirements-optional.txt
```

## Run

### Default (self‑automation + interactive console)
```powershell
python system_orchestrator.py
```
Console commands:
- `status`  -> full system + automation status
- `recent`  -> recently processed files
- `quit`    -> shutdown

### Autonomous daemon (no console)
```powershell
python system_orchestrator.py auto
```

### GUI (self‑automation + GUI)
```powershell
python system_orchestrator.py gui
```

### Batch
```powershell
python system_orchestrator.py batch path\to\inputs.txt
```

## Self‑Automation: How to use it

### 1) Drop files to be ingested into any watch folder
Default watch folders (created automatically under your root):
- `X:\gss1147\inbox`
- `X:\gss1147\information_core\watch`
- `X:\gss1147\data`

The Information Core ingests supported formats incrementally and stores a processing index in:
- `X:\gss1147\state\file_index.sqlite3`

### 2) “Command files” (fully unattended processing of prompts)
Create a `.txt` file in:
- `X:\gss1147\inbox_commands`

Each non-empty line is treated as a user prompt. Results are written to:
- `X:\gss1147\outbox\<filename>_results.json`

An index is stored in:
- `X:\gss1147\state\command_index.sqlite3`

### 3) Logs
Structured events are appended to:
- `X:\gss1147\logs\system_events.jsonl`

### 4) Configure automation
Automation settings are written on first run to:
- `X:\gss1147\gss_automation_config.json`

You can change scan intervals, directories, max files per scan, etc.

## Safety model (important)
This bundle does **not** auto‑execute generated code and does **not** auto‑apply patches.
When automation detects errors/health failures it generates **patch proposals** to:
- `X:\gss1147\patch_proposals\`

You review and apply changes manually.
