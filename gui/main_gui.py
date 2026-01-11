from __future__ import annotations

# Optional GUI: this stub avoids hard dependency on Qt.
# Install: pip install pyside6
# Run: python -m gss_ai.gui.main_gui

def main() -> int:
    try:
        from PySide6 import QtWidgets
    except Exception as e:
        print("PySide6 not installed. Install with: pip install pyside6")
        print(f"Import error: {e}")
        return 1

    app = QtWidgets.QApplication([])
    win = QtWidgets.QMainWindow()
    win.setWindowTitle("GSS1147 AI - Modular GUI (Stub)")

    tabs = QtWidgets.QTabWidget()
    win.setCentralWidget(tabs)

    def add_tab(title: str, text: str) -> None:
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.addWidget(QtWidgets.QLabel(text))
        tabs.addTab(w, title)

    add_tab("Tiny Recursive Model", "Controls + activity meters will live here.")
    add_tab("Neural-Symbolic", "Logic constraints + reasoning traces.")
    add_tab("Agentic Systems", "Plans, tools, patch proposals, self-debug.")
    add_tab("Algorithmic Reasoners", "Search / solvers / calculators.")
    add_tab("Hybrid AI", "Memory and adaptation controls.")
    add_tab("Information Core", "File ingestion and media understanding.")
    add_tab("Memory", "Long/short-term memory viewer.")

    win.resize(1200, 800)
    win.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
