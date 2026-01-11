"""
GODs Strongest Soldier AI Chatbot - Holographic GUI
Self-evolving GUI with individual tabs for each module

Notes
- Safe-by-default: the GUI can invoke *known* module actions, but it does not execute arbitrary code
  or auto-apply self-modifying patches.
- If PyQt5 is not installed, this module still imports cleanly and `launch_gui()` raises a clear error.
"""
from __future__ import annotations

import sys
import time
import random
from datetime import datetime
from typing import Dict, Any, Optional

try:
    # PyQt5 imports
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
        QHBoxLayout, QPushButton, QTextEdit, QLabel, QProgressBar,
        QComboBox, QSpinBox, QDoubleSpinBox, QGroupBox, QGridLayout,
        QSplitter, QCheckBox, QMessageBox, QLineEdit
    )
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
    from PyQt5.QtGui import QColor, QPainter, QPen, QBrush
    _PYQT5_AVAILABLE = True
    _PYQT5_IMPORT_ERROR: Optional[Exception] = None
except Exception as e:  # pragma: no cover
    _PYQT5_AVAILABLE = False
    _PYQT5_IMPORT_ERROR = e

if _PYQT5_AVAILABLE:

    class HolographicEffectWidget(QWidget):
        """Simulated holographic display effect."""
        def __init__(self, parent=None):
            super().__init__(parent)
            self.pulse_phase = 0
            self._setup_animation()

        def _setup_animation(self):
            self.anim_timer = QTimer(self)
            self.anim_timer.timeout.connect(self._update_pulse)
            self.anim_timer.start(50)  # ~20 FPS

        def _update_pulse(self):
            self.pulse_phase = (self.pulse_phase + 3) % 360
            self.update()

        def paintEvent(self, event):  # noqa: N802
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            painter.setPen(QPen(QColor(0, 255, 255, 30), 1, Qt.DotLine))
            w, h = self.width(), self.height()

            for x in range(0, w, 40):
                painter.drawLine(x, 0, x, h)
            for y in range(0, h, 40):
                painter.drawLine(0, y, w, y)

            pulse_intensity = 40 + int(30 * (0.5 + 0.5 * (self.pulse_phase / 360.0)))
            painter.fillRect(self.rect(), QBrush(QColor(0, 255, 255, pulse_intensity)))


    class ModuleTab(QWidget):
        """Individual tab for each module."""
        def __init__(self, module_name: str, module_key: str, parent=None, backend: Optional[object] = None):
            super().__init__(parent)
            self.module_name = module_name
            self.module_key = module_key
            self.backend = backend
            self.activity_history = []
            self.graph_data: Dict[str, list] = {"timestamps": [], "performance": [], "memory_usage": [], "activity_level": []}
            self._setup_ui()

        def _setup_ui(self):
            layout = QVBoxLayout(self)

            header = QHBoxLayout()
            self.status_label = QLabel(f"Module: {self.module_name}")
            self.status_label.setStyleSheet("font-size: 16px; color: cyan; font-weight: bold;")
            header.addWidget(self.status_label)

            self.activity_meter = QProgressBar()
            self.activity_meter.setRange(0, 100)
            self.activity_meter.setValue(0)
            self.activity_meter.setStyleSheet("""
                QProgressBar { border: 2px solid cyan; border-radius: 5px; text-align: center; }
                QProgressBar::chunk {
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00ffff, stop:1 #0080ff);
                }
            """)
            header.addWidget(self.activity_meter)
            layout.addLayout(header)

            # Quick input runner
            run_row = QHBoxLayout()
            run_row.addWidget(QLabel("Input:"))
            self.input_line = QLineEdit()
            self.input_line.setPlaceholderText("Type here and press Run")
            run_row.addWidget(self.input_line)
            run_btn = QPushButton("Run")
            run_btn.clicked.connect(self.run_text)
            run_row.addWidget(run_btn)
            layout.addLayout(run_row)

            splitter = QSplitter(Qt.Vertical)

            activity_group = QGroupBox("Activity Monitor")
            activity_layout = QVBoxLayout(activity_group)
            self.activity_text = QTextEdit()
            self.activity_text.setReadOnly(True)
            self.activity_text.setStyleSheet("background-color: #001a33; color: cyan;")
            activity_layout.addWidget(self.activity_text)
            splitter.addWidget(activity_group)

            tools_group = QGroupBox("Tools & Controls")
            tools_layout = QGridLayout(tools_group)
            self._add_module_specific_tools(tools_layout)
            splitter.addWidget(tools_group)

            settings_group = QGroupBox("Settings")
            settings_layout = QGridLayout(settings_group)
            self._setup_settings(settings_layout)
            splitter.addWidget(settings_group)

            layout.addWidget(splitter)

            self.update_timer = QTimer(self)
            self.update_timer.timeout.connect(self._update_realtime_data)
            self.update_timer.start(1000)

        def _add_module_specific_tools(self, layout: QGridLayout):
            if "Recursive" in self.module_name:
                layout.addWidget(QLabel("Max Depth:"), 0, 0)
                self.depth_spin = QSpinBox()
                self.depth_spin.setRange(1, 100)
                self.depth_spin.setValue(32)
                layout.addWidget(self.depth_spin, 0, 1)

                btn = QPushButton("Test Recursion")
                btn.clicked.connect(self.test_recursion)
                layout.addWidget(btn, 0, 2)

                btn2 = QPushButton("Clear Activity")
                btn2.clicked.connect(self.clear_activity)
                layout.addWidget(btn2, 1, 0, 1, 3)

            elif "Symbolic" in self.module_name:
                layout.addWidget(QLabel("Inference Engine:"), 0, 0)
                self.engine_combo = QComboBox()
                self.engine_combo.addItems(["deductive", "inductive", "abductive", "analogical"])
                layout.addWidget(self.engine_combo, 0, 1, 1, 2)

                btn = QPushButton("Run Symbolic Query")
                btn.clicked.connect(self.run_symbolic_query)
                layout.addWidget(btn, 1, 0, 1, 3)

            elif "Agentic" in self.module_name:
                btn = QPushButton("Propose Patch (Safe)")
                btn.clicked.connect(self.propose_patch)
                layout.addWidget(btn, 0, 0)

                btn2 = QPushButton("Debug Agents")
                btn2.clicked.connect(self.debug_agents)
                layout.addWidget(btn2, 0, 1)

                btn3 = QPushButton("Evolve Routing")
                btn3.clicked.connect(self.evolve_moe)
                layout.addWidget(btn3, 1, 0, 1, 2)

            elif "Reasoners" in self.module_name:
                layout.addWidget(QLabel("Reasoning Type:"), 0, 0)
                self.reasoning_combo = QComboBox()
                self.reasoning_combo.addItems(["commonsense", "creative", "singularity", "hybrid"])
                layout.addWidget(self.reasoning_combo, 0, 1, 1, 2)

                btn = QPushButton("Solve Problem")
                btn.clicked.connect(self.solve_problem)
                layout.addWidget(btn, 1, 0, 1, 3)

            elif "Hybrid" in self.module_name:
                btn = QPushButton("Meta-Train Task")
                btn.clicked.connect(self.meta_train)
                layout.addWidget(btn, 0, 0)

                btn2 = QPushButton("RL Step")
                btn2.clicked.connect(self.rl_step)
                layout.addWidget(btn2, 0, 1)

                btn3 = QPushButton("Consolidate Memory")
                btn3.clicked.connect(self.consolidate_memory)
                layout.addWidget(btn3, 1, 0, 1, 2)

            elif "Memory" in self.module_name:
                btn = QPushButton("View LTM")
                btn.clicked.connect(self.view_long_term_memory)
                layout.addWidget(btn, 0, 0)

                btn2 = QPushButton("View STM")
                btn2.clicked.connect(self.view_short_term_memory)
                layout.addWidget(btn2, 0, 1)

                btn3 = QPushButton("Clear Activity")
                btn3.clicked.connect(self.clear_activity)
                layout.addWidget(btn3, 1, 0, 1, 2)

            elif "Information" in self.module_name:
                btn = QPushButton("Run Self-Test")
                btn.clicked.connect(self.info_self_test)
                layout.addWidget(btn, 0, 0)

                btn2 = QPushButton("Clear Activity")
                btn2.clicked.connect(self.clear_activity)
                layout.addWidget(btn2, 0, 1)

        def _setup_settings(self, layout: QGridLayout):
            self.auto_evolve_check = QCheckBox("Auto-Evolution")
            self.auto_evolve_check.setChecked(True)
            layout.addWidget(self.auto_evolve_check, 0, 0)

            layout.addWidget(QLabel("Perf Threshold:"), 0, 1)
            self.perf_spin = QDoubleSpinBox()
            self.perf_spin.setRange(0.0, 1.0)
            self.perf_spin.setValue(0.8)
            self.perf_spin.setSingleStep(0.05)
            layout.addWidget(self.perf_spin, 0, 2)

            layout.addWidget(QLabel("Log Level:"), 1, 0)
            self.log_combo = QComboBox()
            self.log_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
            layout.addWidget(self.log_combo, 1, 1, 1, 2)

        def log_activity(self, message: str):
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}"
            self.activity_text.append(log_entry)
            self.activity_history.append(log_entry)
            self.activity_meter.setValue(min(100, len(self.activity_history) % 101))

        def _update_realtime_data(self):
            now = time.time()
            self.graph_data["timestamps"].append(now)
            self.graph_data["performance"].append(random.random() * 0.25 + 0.7)
            self.graph_data["memory_usage"].append(random.random() * 30 + 50)
            self.graph_data["activity_level"].append(self.activity_meter.value())
            if len(self.graph_data["timestamps"]) > 100:
                for k in list(self.graph_data.keys()):
                    self.graph_data[k] = self.graph_data[k][-100:]

        # ---- Tool handlers ----
        def _dispatch(self, action: str, payload: Dict[str, Any]) -> None:
            if not (self.backend and hasattr(self.backend, "gui_action")):
                self.log_activity("Backend not attached")
                return
            try:
                res = self.backend.gui_action(self.module_key, action, payload)
                if isinstance(res, dict):
                    # Log concise result summary
                    status = res.get("status", "")
                    rtype = res.get("type", "")
                    msg = res.get("message") or res.get("summary") or ""
                    self.log_activity(f"Result | {status} | {rtype} {msg}".strip())
            except Exception as e:
                self.log_activity(f"Action error: {e}")

        def clear_activity(self):
            self.activity_text.clear()
            self.activity_history.clear()
            self.activity_meter.setValue(0)

        def run_text(self):
            text = self.input_line.text().strip() if hasattr(self, "input_line") else ""
            if not text:
                text = "GUI default test input"
            self.log_activity(f"Running text through {self.module_key}")
            self._dispatch("run_text", {"text": text})

        def test_recursion(self):
            depth = int(self.depth_spin.value())
            self.log_activity(f"Testing recursion | max_depth={depth}")
            self._dispatch("test_recursion", {"max_depth": depth})

        def run_symbolic_query(self):
            engine = self.engine_combo.currentText()
            self.log_activity(f"Running symbolic query | engine={engine}")
            self._dispatch("run_symbolic_query", {"engine": engine})

        def propose_patch(self):
            self.log_activity("Proposing safe patch (no auto-apply)")
            self._dispatch("propose_patch", {})

        def debug_agents(self):
            self.log_activity("Debugging agents")
            self._dispatch("debug_agents", {})

        def evolve_moe(self):
            self.log_activity("Evolving routing policy")
            self._dispatch("evolve_routing", {})

        def solve_problem(self):
            mode = self.reasoning_combo.currentText()
            self.log_activity(f"Solving problem | mode={mode}")
            self._dispatch("solve_problem", {"mode": mode})

        def meta_train(self):
            self.log_activity("Starting meta-training step")
            self._dispatch("meta_train", {})

        def rl_step(self):
            self.log_activity("Executing RL step")
            self._dispatch("rl_step", {})

        def consolidate_memory(self):
            self.log_activity("Consolidating memory (STM -> LTM)")
            self._dispatch("consolidate_memory", {})

        def view_long_term_memory(self):
            self.log_activity("Viewing long-term memory")
            self._dispatch("view_ltm", {})

        def view_short_term_memory(self):
            self.log_activity("Viewing short-term memory")
            self._dispatch("view_stm", {})

        def info_self_test(self):
            self.log_activity("Information Core self-test")
            self._dispatch("self_test", {})


    class MainGUI(QMainWindow):
        """Main holographic GUI window."""
        def __init__(self, backend: Optional[object] = None):
            super().__init__()
            self.backend = backend
            self.setWindowTitle("GODs Strongest Soldier AI Chatbot - Holographic Interface")
            self.setGeometry(100, 100, 1400, 900)

            self.holo_effect = HolographicEffectWidget(self)
            self.holo_effect.setGeometry(self.rect())
            self.holo_effect.lower()

            self.tab_widget = QTabWidget()
            self.tab_widget.setStyleSheet("""
                QTabWidget::pane { border: 2px solid cyan; background-color: rgba(0, 20, 40, 200); }
                QTabBar::tab { background-color: #003366; color: cyan; padding: 10px; margin: 2px; }
                QTabBar::tab:selected { background-color: #00aaff; color: black; }
            """)

            self.tabs: Dict[str, ModuleTab] = {}
            self._create_tabs()
            self.setCentralWidget(self.tab_widget)

            self.status_bar = self.statusBar()
            self.status_bar.showMessage("System Online - Ready")
            self.status_bar.setStyleSheet("color: cyan; background-color: #001a33;")

            self.global_timer = QTimer(self)
            self.global_timer.timeout.connect(self._global_monitoring)
            self.global_timer.start(5000)

            self.system_stats = {"uptime": time.time(), "total_operations": 0, "evolution_events": 0}

        def resizeEvent(self, event):  # noqa: N802
            super().resizeEvent(event)
            self.holo_effect.setGeometry(self.rect())
            self.holo_effect.lower()

        def _create_tabs(self):
            modules = [
                ("Tiny Recursive Model", "recursive"),
                ("Neural Symbolic AI", "neural_symbolic"),
                ("Agentic Systems", "agentic"),
                ("Algorithmic Reasoners", "reasoners"),
                ("Advanced Hybrid AI", "hybrid"),
                ("Memory Core", "memory"),
                ("Information Core", "info_core"),
            ]
            for name, key in modules:
                tab = ModuleTab(name, key, self, backend=self.backend)
                self.tab_widget.addTab(tab, name)
                self.tabs[name] = tab

        def _global_monitoring(self):
            self.system_stats["total_operations"] += 1
            avg_perf = random.random() * 0.25 + 0.7
            if avg_perf < 0.7:
                self._trigger_evolution()
            uptime = int(time.time() - self.system_stats["uptime"])
            msg = f"Uptime: {uptime}s | Ops: {self.system_stats['total_operations']} | Evolutions: {self.system_stats['evolution_events']} | Perf: {avg_perf:.2f}"
            self.status_bar.showMessage(msg)

        def _trigger_evolution(self):
            self.system_stats["evolution_events"] += 1
            for tab_name, tab in self.tabs.items():
                if tab.auto_evolve_check.isChecked():
                    tab.log_activity(f"[EVOLUTION] Triggered for {tab_name}")

        def closeEvent(self, event):  # noqa: N802
            reply = QMessageBox.question(
                self, "Quit?", "Are you sure you want to stop the system?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                event.accept()
            else:
                event.ignore()


    class GUIController(QObject):
        update_signal = pyqtSignal(str, dict)

        def __init__(self, backend: Optional[object] = None):
            super().__init__()
            self.backend = backend
            self.gui: Optional[MainGUI] = None
            self.module_data: Dict[str, Dict[str, Any]] = {}

        def initialize_gui(self):
            app = QApplication(sys.argv)
            app.setStyle("Fusion")
            app.setStyleSheet("""
                QMainWindow { background-color: #000814; }
                QWidget { background-color: #001122; color: cyan; font-family: "Courier New"; font-size: 12px; }
                QPushButton { background-color: #003366; color: cyan; border: 2px solid #00aaff; padding: 5px; border-radius: 5px; }
                QPushButton:hover { background-color: #00aaff; color: black; }
                QTextEdit { background-color: #001a33; color: cyan; border: 1px solid #00aaff; }
                QProgressBar { border: 1px solid cyan; background-color: #001122; }
            """)
            self.gui = MainGUI(backend=self.backend)
            self.gui.show()
            sys.exit(app.exec_())

        def update_module_status(self, module_name: str, data: Dict[str, Any]):
            if not self.gui:
                return
            for tab in self.gui.tabs.values():
                if module_name.lower() in tab.module_key.lower() or module_name.lower() in tab.module_name.lower():
                    if "activity" in data:
                        tab.log_activity(str(data["activity"]))
            self.module_data[module_name] = data

        def get_module_data(self, module_name: str) -> Dict[str, Any]:
            return self.module_data.get(module_name, {})


    _gui_controller: Optional[GUIController] = None


    def get_gui_controller(backend: Optional[object] = None) -> GUIController:
        global _gui_controller
        if _gui_controller is None:
            _gui_controller = GUIController(backend=backend)
        return _gui_controller


def launch_gui(backend: Optional[object] = None, orchestrator: Optional[object] = None):
    """Launch the GUI application."""
    # Backward-compatible alias
    if backend is None and orchestrator is not None:
        backend = orchestrator
    if not _PYQT5_AVAILABLE:
        raise RuntimeError(
            f"PyQt5 is required to run the GUI. Import error: {_PYQT5_IMPORT_ERROR!r}\n"
            f"Install with: pip install PyQt5"
        )
    controller = get_gui_controller(backend=backend)  # type: ignore[name-defined]
    controller.initialize_gui()  # type: ignore[call-arg]


if __name__ == "__main__":  # pragma: no cover
    launch_gui()
