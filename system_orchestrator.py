"""
GODs Strongest Soldier AI Chatbot - System Orchestrator (Self-Automated)

This entry point integrates the 7 core modules and runs an always-on automation supervisor.

Run modes:
- Default (self-automated + interactive console):  python system_orchestrator.py
- GUI (self-automated + GUI):                      python system_orchestrator.py gui
- Batch:                                           python system_orchestrator.py batch path/to/input.txt
- Headless autonomous daemon:                      python system_orchestrator.py auto

Environment:
- GSS1147_ROOT: working directory (default: X:/gss1147)

Safety:
- This system does NOT auto-execute newly written code.
- Any "self-improvement" is emitted as patch proposals for review.
"""
from __future__ import annotations

import os
import sys
import json
import time
import signal
import threading
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Iterable, Tuple

# Optional numpy (confidence averaging)
try:  # pragma: no cover
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore

# Core modules (compatibility layers)
from Automated_Tiny_Recursive_Model import get_model_manager
from Automated_Neural_Symbolic_AI import get_neural_symbolic_manager
from Automated_Agentic_Systems import get_orchestrator
from Automated_Algorithmic_Reasoners import get_reasoners_manager
from Automated_Advanced_Hybird_AI import get_hybrid_manager
from Automated_main_gui import launch_gui
from Automated_Infomation_Core import get_info_core_manager


# -----------------------------
# Persistent file index (sqlite)
# -----------------------------
class FileIndex:
    """Tracks files processed by the automation layer so ingestion is incremental."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY,
                    mtime REAL NOT NULL,
                    size INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    last_processed REAL NOT NULL,
                    meta_json TEXT
                );
                """
            )

    def needs_processing(self, path: str) -> bool:
        try:
            st = os.stat(path)
        except Exception:
            return False
        mtime, size = float(st.st_mtime), int(st.st_size)

        with self._connect() as conn:
            row = conn.execute("SELECT mtime, size, status FROM files WHERE path=?", (path,)).fetchone()
        if row is None:
            return True
        prev_mtime, prev_size, prev_status = float(row[0]), int(row[1]), str(row[2])
        # Reprocess if changed OR prior processing errored
        return (mtime != prev_mtime) or (size != prev_size) or (prev_status in {"error", "requires", "unsupported"})

    def mark(self, path: str, status: str, meta: Optional[Dict[str, Any]] = None) -> None:
        try:
            st = os.stat(path)
            mtime, size = float(st.st_mtime), int(st.st_size)
        except Exception:
            mtime, size = time.time(), 0
        payload = json.dumps(meta or {}, ensure_ascii=False)
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO files (path, mtime, size, status, last_processed, meta_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    mtime=excluded.mtime,
                    size=excluded.size,
                    status=excluded.status,
                    last_processed=excluded.last_processed,
                    meta_json=excluded.meta_json;
                """,
                (path, mtime, size, status, now, payload),
            )

    def recently_processed(self, seconds: int = 30) -> List[Tuple[str, float, str]]:
        cutoff = time.time() - float(seconds)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT path, last_processed, status FROM files WHERE last_processed>=? ORDER BY last_processed DESC",
                (cutoff,),
            ).fetchall()
        return [(str(r[0]), float(r[1]), str(r[2])) for r in rows]


# -----------------------------
# Automation supervisor
# -----------------------------
@dataclass
class AutoConfig:
    enabled: bool = True
    scan_dirs: List[str] = None  # type: ignore
    scan_recursive: bool = True
    max_files_per_scan: int = 50
    scan_interval_sec: int = 20

    # A second inbox for "command files" (each line is treated as a user input)
    command_inbox_dir: str = ""
    command_outbox_dir: str = ""
    command_scan_interval_sec: int = 10

    # Fine-tuning cadence (best-effort)
    fine_tune_interval_sec: int = 60

    # Health checks + patch proposals
    health_check_interval_sec: int = 60
    auto_patch_proposals: bool = True

    # Logging
    logs_dir: str = ""
    log_jsonl: str = ""

    def materialize(self, work_dir: str) -> "AutoConfig":
        wd = Path(work_dir)
        if self.scan_dirs is None:
            self.scan_dirs = [
                str(wd / "inbox"),
                str(wd / "information_core" / "watch"),
                str(wd / "data"),
            ]
        if not self.command_inbox_dir:
            self.command_inbox_dir = str(wd / "inbox_commands")
        if not self.command_outbox_dir:
            self.command_outbox_dir = str(wd / "outbox")
        if not self.logs_dir:
            self.logs_dir = str(wd / "logs")
        if not self.log_jsonl:
            self.log_jsonl = str(Path(self.logs_dir) / "system_events.jsonl")
        return self


class AutomationSupervisor:
    """Runs the system in an always-on autonomous mode."""

    def __init__(self, orchestrator: "SystemOrchestrator", cfg: AutoConfig):
        self.orch = orchestrator
        self.cfg = cfg.materialize(orchestrator.work_dir)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Persistent indexes
        state_dir = Path(orchestrator.work_dir) / "state"
        self.file_index = FileIndex(str(state_dir / "file_index.sqlite3"))
        self.command_index = FileIndex(str(state_dir / "command_index.sqlite3"))

        # Ensure dirs exist
        for d in [*self.cfg.scan_dirs, self.cfg.command_inbox_dir, self.cfg.command_outbox_dir, self.cfg.logs_dir]:
            os.makedirs(d, exist_ok=True)

        self._lock = threading.Lock()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="GSS-AutoSupervisor", daemon=True)
        self._thread.start()
        self._log_event("automation_started", {"scan_dirs": self.cfg.scan_dirs})

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3.0)
        self._log_event("automation_stopped", {})

    # ---- core loop ----
    def _run(self) -> None:
        t_scan = 0.0
        t_cmd = 0.0
        t_ft = 0.0
        t_hc = 0.0

        while not self._stop.is_set():
            now = time.monotonic()

            try:
                if now >= t_scan:
                    self._scan_ingestion_once()
                    t_scan = now + float(self.cfg.scan_interval_sec)
            except Exception as e:
                self._log_event("automation_scan_error", {"error": str(e)})
                self._maybe_propose_patch("automation_scan_error", str(e))

            try:
                if now >= t_cmd:
                    self._scan_command_inbox_once()
                    t_cmd = now + float(self.cfg.command_scan_interval_sec)
            except Exception as e:
                self._log_event("automation_command_error", {"error": str(e)})
                self._maybe_propose_patch("automation_command_error", str(e))

            try:
                if now >= t_ft:
                    self._fine_tune_once()
                    t_ft = now + float(self.cfg.fine_tune_interval_sec)
            except Exception as e:
                self._log_event("automation_finetune_error", {"error": str(e)})
                self._maybe_propose_patch("automation_finetune_error", str(e))

            try:
                if now >= t_hc:
                    self._health_check_once()
                    t_hc = now + float(self.cfg.health_check_interval_sec)
            except Exception as e:
                self._log_event("automation_health_error", {"error": str(e)})
                self._maybe_propose_patch("automation_health_error", str(e))

            # Always-on "ticks" for modules that support it
            try:
                self._tick_modules()
            except Exception as e:
                self._log_event("automation_tick_error", {"error": str(e)})

            time.sleep(0.25)

    # ---- tasks ----
    def _iter_files(self, base: str) -> Iterable[str]:
        p = Path(base)
        if not p.exists():
            return []
        if p.is_file():
            return [str(p)]
        if self.cfg.scan_recursive:
            return (str(x) for x in p.rglob("*") if x.is_file())
        return (str(x) for x in p.glob("*") if x.is_file())

    def _scan_ingestion_once(self) -> None:
        info = self.orch.modules.get("info_core")
        if info is None:
            return

        processed = 0
        for d in self.cfg.scan_dirs:
            for fp in self._iter_files(d):
                # only process supported formats
                ext = Path(fp).suffix.lower()
                if not hasattr(info, "reader"):
                    continue
                if ext not in getattr(info.reader, "supported_formats", {}):
                    continue

                if not self.file_index.needs_processing(fp):
                    continue

                res = info.process_file(fp, enable_fine_tuning=True)

                # Normalize status across InformationCore return shapes:
                # - read_file errors return {"status": "...", ...}
                # - successful processing returns {"original_content": ..., "metadata": {...}, ...}
                if isinstance(res, dict) and res.get("status") in {"error", "requires", "unsupported"}:
                    status = str(res.get("status"))
                elif isinstance(res, dict) and ("original_content" in res) and ("metadata" in res):
                    status = "success"
                else:
                    status = str(res.get("status") or res.get("metadata", {}).get("status") or "unknown")

                # Normalize weird variants
                if status not in {"success", "error", "requires", "unsupported"}:
                    if status.startswith("requires"):
                        status = "requires"

                self.file_index.mark(fp, status=status, meta={"format": ext})

                processed += 1
                self._log_event("file_processed", {"path": fp, "status": status, "format": ext})

                if processed >= int(self.cfg.max_files_per_scan):
                    return

    def _scan_command_inbox_once(self) -> None:
        inbox = Path(self.cfg.command_inbox_dir)
        outbox = Path(self.cfg.command_outbox_dir)
        for fp in inbox.glob("*.txt"):
            fpath = str(fp)
            if not self.command_index.needs_processing(fpath):
                continue

            try:
                text = fp.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                self.command_index.mark(fpath, "error", {"error": str(e)})
                continue

            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            results = []
            for ln in lines:
                results.append(self.orch.process_user_input(ln))

            out_name = fp.stem + "_results.json"
            out_path = outbox / out_name
            out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

            self.command_index.mark(fpath, "success", {"out": str(out_path)})
            self._log_event("command_file_processed", {"in": fpath, "out": str(out_path), "count": len(lines)})

    def _fine_tune_once(self) -> None:
        info = self.orch.modules.get("info_core")
        if info is None or not hasattr(info, "fine_tuner"):
            return
        try:
            res = info.fine_tuner.fine_tune_step()
        except Exception as e:
            res = {"status": "error", "error": str(e)}
        self._log_event("fine_tune_step", res)

    def _health_check_once(self) -> None:
        checks = self.orch.run_system_check()
        self._log_event("health_check", checks)
        if self.cfg.auto_patch_proposals and not all(checks.values()):
            bad = [k for k, v in checks.items() if not v]
            self._maybe_propose_patch("module_health_failed", f"Modules failing: {bad}")

    def _tick_modules(self) -> None:
        """Allow modules to run autonomous micro-steps without user input."""
        ctx = {"t": time.time(), "work_dir": self.orch.work_dir}
        for key, mod in self.orch.modules.items():
            if hasattr(mod, "tick"):
                try:
                    mod.tick(ctx)  # type: ignore
                except Exception as e:
                    self._log_event("module_tick_error", {"module": key, "error": str(e)})

    # ---- logging & patch proposals ----
    def _log_event(self, event: str, payload: Dict[str, Any]) -> None:
        os.makedirs(self.cfg.logs_dir, exist_ok=True)
        row = {
            "ts": datetime.now().isoformat(),
            "event": event,
            "payload": payload,
        }
        try:
            with open(self.cfg.log_jsonl, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception:
            # last-resort: avoid crashing automation due to I/O errors
            pass

    def _maybe_propose_patch(self, title: str, details: str) -> None:
        if not self.cfg.auto_patch_proposals:
            return
        agent = self.orch.modules.get("agentic")
        if agent is None or not hasattr(agent, "propose_patch"):
            return
        proposal = {
            "issue": title,
            "details": details,
            "recommendation": "Generate a safe patch proposal (no auto-apply). Include steps to reproduce and minimal diff.",
            "context": {"work_dir": self.orch.work_dir},
        }
        try:
            path = agent.propose_patch(title=title, proposal=json.dumps(proposal, indent=2), metadata={"source": "automation"})
            self._log_event("patch_proposed", {"title": title, "path": path})
        except Exception as e:
            self._log_event("patch_propose_error", {"error": str(e)})


# -----------------------------
# System orchestrator
# -----------------------------
class SystemOrchestrator:
    """Main orchestrator integrating modules + automation."""

    def __init__(self, work_dir: Optional[str] = None, enable_automation: bool = True):
        self.work_dir = work_dir or os.environ.get("GSS1147_ROOT", "X:/gss1147")
        os.makedirs(self.work_dir, exist_ok=True)

        self.running = False
        self.modules: Dict[str, Any] = {}
        self.system_stats: Dict[str, Any] = {
            "start_time": datetime.now().isoformat(),
            "total_operations": 0,
            "module_status": {},
            "performance_metrics": {},
        }

        self._initialize_modules()

        # Automation (self-running)
        self.auto_cfg = self._load_or_create_config()
        self.supervisor = AutomationSupervisor(self, self.auto_cfg)

        if enable_automation and self.auto_cfg.enabled:
            self.supervisor.start()

        # Signal handlers (best-effort on Windows)
        try:
            signal.signal(signal.SIGINT, self._shutdown_handler)
            signal.signal(signal.SIGTERM, self._shutdown_handler)
        except Exception:
            pass

    def _load_or_create_config(self) -> AutoConfig:
        cfg_path = Path(self.work_dir) / "gss_automation_config.json"
        if cfg_path.exists():
            try:
                data = json.loads(cfg_path.read_text(encoding="utf-8"))
                cfg = AutoConfig(**data)  # type: ignore[arg-type]
                return cfg.materialize(self.work_dir)
            except Exception:
                pass
        cfg = AutoConfig().materialize(self.work_dir)
        try:
            cfg_path.write_text(json.dumps(cfg.__dict__, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
        return cfg

    def _initialize_modules(self) -> None:
        print("[SYSTEM] Initializing GODs Strongest Soldier AI Chatbot...")
        self.modules = {
            "recursive": get_model_manager(),
            "neural_symbolic": get_neural_symbolic_manager(),
            "agentic": get_orchestrator(self.work_dir),
            "reasoners": get_reasoners_manager(),
            "hybrid": get_hybrid_manager(),
            "info_core": get_info_core_manager(),
        }
        print("[SYSTEM] All modules initialized successfully")

    # ---- GUI integration hook ----
    def gui_action(self, module_key: str, action: str, payload: Dict[str, Any]):
        """Called by GUI tabs. Logs and dispatches to modules when applicable."""
        try:
            if module_key == "recursive" and action == "test_recursion":
                depth = int(payload.get("max_depth", 32))
                self.modules["recursive"].process_input("GUI recursion test", max_depth=depth)

            elif module_key == "neural_symbolic" and action == "run_symbolic_query":
                engine = payload.get("engine", "deductive")
                self.modules["neural_symbolic"].process_logical_query(f"engine={engine}")

            elif module_key == "agentic" and action == "propose_patch":
                path = self.modules["agentic"].propose_patch(
                    title="gui_proposal",
                    proposal="GUI requested a safe patch proposal. Populate this with diff/patch content as needed.",
                    metadata={"source": "GUI"},
                )
                print(f"[SYSTEM] Patch proposal written: {path}")

            elif module_key == "info_core" and action == "process_path":
                target = payload.get("path")
                if target:
                    res = self.modules["info_core"].process_path(target) if hasattr(self.modules["info_core"], "process_path") else self.modules["info_core"].process_file(target)
                    print(f"[SYSTEM] InfoCore processed: {target} | status={res.get('status')}")

        except Exception as e:
            print(f"[SYSTEM] GUI action error: {e}")

    def run_system_check(self) -> Dict[str, bool]:
        results: Dict[str, bool] = {}
        for name, mod in self.modules.items():
            try:
                if hasattr(mod, "get_stats"):
                    stats = mod.get_stats()
                    results[name] = bool(stats)
                else:
                    results[name] = mod is not None
            except Exception as e:
                print(f"[SYSTEM] Module {name} check failed: {e}")
                results[name] = False
        return results

    def process_user_input(self, input_text: str) -> Dict[str, Any]:
        self.system_stats["total_operations"] += 1
        try:
            recursive_result = self.modules["recursive"].process_input(input_text)
            symbolic_result = self.modules["neural_symbolic"].process_logical_query(input_text)

            agentic_task = {"description": input_text, "recursive_output": recursive_result, "symbolic_output": symbolic_result}
            agentic_result = self.modules["agentic"].orchestrate_task(agentic_task)

            reasoning_result = self.modules["reasoners"].solve_problem(input_text)
            hybrid_result = self.modules["hybrid"].process_input(input_text)
            info_result = self.modules["info_core"].enhance_input(input_text)

            conf = self._calculate_confidence(
                {
                    "recursive": recursive_result,
                    "symbolic": symbolic_result,
                    "reasoning": reasoning_result,
                    "hybrid": hybrid_result,
                }
            )

            return {
                "status": "success",
                "input": input_text,
                "timestamp": datetime.now().isoformat(),
                "recursive": recursive_result,
                "symbolic": symbolic_result,
                "agentic": agentic_result,
                "reasoning": reasoning_result,
                "hybrid": hybrid_result,
                "info_enhanced": info_result,
                "confidence": conf,
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "input": input_text, "timestamp": datetime.now().isoformat()}

    def _calculate_confidence(self, results: Dict[str, Any]) -> float:
        scores: List[float] = []
        for r in results.values():
            if isinstance(r, dict) and "confidence" in r:
                scores.append(float(r["confidence"]))
            elif isinstance(r, dict) and r.get("status") == "success":
                scores.append(0.7)
            else:
                scores.append(0.5)
        if not scores:
            return 0.5
        if np is not None:
            return float(np.mean(scores))
        return float(sum(scores) / len(scores))

    def get_system_status(self) -> Dict[str, Any]:
        module_status: Dict[str, Any] = {}
        for name, mod in self.modules.items():
            try:
                module_status[name] = mod.get_stats() if hasattr(mod, "get_stats") else {"status": "active"}
            except Exception as e:
                module_status[name] = {"status": "error", "error": str(e)}
        self.system_stats["module_status"] = module_status

        start = datetime.fromisoformat(self.system_stats["start_time"])
        uptime = (datetime.now() - start).total_seconds()
        return {
            "system_status": self.system_stats,
            "uptime_sec": uptime,
            "total_operations": self.system_stats["total_operations"],
            "module_health": {name: ("error" if "error" in st else "healthy") for name, st in module_status.items()},
            "automation": {
                "enabled": bool(self.auto_cfg.enabled),
                "scan_dirs": self.auto_cfg.scan_dirs,
                "recent_files": self.supervisor.file_index.recently_processed(30),
                "command_inbox": self.auto_cfg.command_inbox_dir,
                "command_outbox": self.auto_cfg.command_outbox_dir,
                "log_jsonl": self.auto_cfg.log_jsonl,
            },
        }

    # ---- shutdown ----
    def _shutdown_handler(self, signum, frame):
        print(f"\n[SYSTEM] Received shutdown signal {signum}")
        self.shutdown()

    def shutdown(self):
        print("[SYSTEM] Shutting down...")
        self.running = False
        try:
            self.supervisor.stop()
        except Exception:
            pass

        state_file = os.path.join(self.work_dir, "system_state.json")
        try:
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(self.system_stats, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        print("[SYSTEM] Shutdown complete")
        raise SystemExit(0)

    # ---- run modes ----
    def run_interactive_mode(self):
        self.running = True
        print("\n[SYSTEM] Interactive console online (automation running in background).")
        print("Commands: status | recent | quit")
        while self.running:
            try:
                user_input = input("\n[You] ").strip()
                if not user_input:
                    continue
                if user_input.lower() == "quit":
                    break
                if user_input.lower() == "status":
                    print(json.dumps(self.get_system_status(), indent=2, ensure_ascii=False))
                    continue
                if user_input.lower() == "recent":
                    print(json.dumps(self.supervisor.file_index.recently_processed(300), indent=2, ensure_ascii=False))
                    continue

                result = self.process_user_input(user_input)
                print(json.dumps(result, indent=2, ensure_ascii=False))

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[Error] {e}")

        self.shutdown()

    def run_gui_mode(self):
        print("[SYSTEM] Starting GUI mode (automation running)...")
        launch_gui(orchestrator=self)

    def run_batch_mode(self, input_file: str):
        print(f"[SYSTEM] Batch processing: {input_file}")
        try:
            with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
                inputs = [ln.strip() for ln in f.readlines() if ln.strip()]
            results = [self.process_user_input(ln) for ln in inputs]
            out_file = os.path.join(self.work_dir, "batch_results.json")
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"[SYSTEM] Batch complete -> {out_file}")
        except Exception as e:
            print(f"[SYSTEM] Batch failed: {e}")

    def run_auto_mode(self):
        self.running = True
        print("[SYSTEM] Autonomous mode online. Automation is running. Press Ctrl+C to stop.")
        try:
            while self.running:
                time.sleep(1.0)
        except KeyboardInterrupt:
            pass
        self.shutdown()


def main():
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "interactive"
    orch = SystemOrchestrator(enable_automation=True)

    print("[SYSTEM] Running initial system check...")
    print(json.dumps(orch.run_system_check(), indent=2, ensure_ascii=False))

    if mode == "gui":
        orch.run_gui_mode()
    elif mode == "batch" and len(sys.argv) > 2:
        orch.run_batch_mode(sys.argv[2])
        orch.shutdown()
    elif mode == "auto":
        orch.run_auto_mode()
    else:
        orch.run_interactive_mode()


if __name__ == "__main__":
    main()
