import sys
import json
import subprocess
import winreg
import os
import winreg as _reg
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QScrollArea, QFrame, QStackedWidget,
    QPushButton, QRadioButton, QButtonGroup, QCheckBox, QSizePolicy
)
from PyQt6.QtCore import QTimer, Qt, QStandardPaths
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor

# -- Folder layout --
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SERVICES_FILE = os.path.join(BASE_DIR, "services", "services.json")
ABOUT_FILE    = os.path.join(BASE_DIR, "about", "about.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

APP_NAME      = "Tarry v1.1"
STARTUP_KEY   = r"Software\Microsoft\Windows\CurrentVersion\Run"

# ── Colour palette  ◄ CUSTOMISE COLOURS HERE ─────────────────────────────────
C_BG          = "#1e1e1e"   # main background
C_BG_DARK     = "#111111"   # title bar / header background
C_BG_ROW_ALT  = "#242424"   # alternate row background
C_GROUP_HDR   = "#2c2c2c"   # group header background
C_TEXT        = "#e0e0e0"   # primary text
C_TEXT_DIM    = "#888888"   # secondary / dim text
C_ACTIVE      = "#ff6b6b"   # ACTIVE status colour
C_DISABLED    = "#51cf66"   # Disabled status colour
C_UNKNOWN     = "#888888"   # Unknown status colour
C_ACCENT      = "#3a7bd5"   # button / nav accent
C_NAV_SEL     = "#2a4a7f"   # selected nav button background
C_SCROLLBAR   = "#555555"   # scrollbar handle

# ── Font sizes  ◄ CUSTOMISE FONT SIZES HERE ───────────────────────────────────
FS_TITLE      = "13px"   # window title bar
FS_NAV        = "11px"   # nav tab buttons
FS_GROUP      = "10px"   # group header labels
FS_SERVICE    = "11px"   # service name text
FS_STATUS     = "10px"   # status badge text
FS_SETTINGS   = "11px"   # settings page text
FS_ABOUT      = "11px"   # about page text


# ── JSON helpers ──────────────────────────────────────────────────────────────

def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_settings() -> dict:
    defaults = {
        "startup": "off",          # "off" | "normal" | "minimized"
        "run_interval": "minute",  # "startup_once" | "minute" | "hour"
        "startup_delay_s": 10
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            saved = load_json(SETTINGS_FILE)
            defaults.update(saved)
        except Exception:
            pass
    return defaults


# ── Check helpers ─────────────────────────────────────────────────────────────

def check_service(name: str):
    try:
        r = subprocess.run(["sc", "query", name], capture_output=True, text=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        return "RUNNING" in r.stdout
    except Exception:
        return None

def check_process(name: str):
    try:
        r = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {name}"],
                           capture_output=True, text=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        return name.lower() in r.stdout.lower()
    except Exception:
        return None

def check_registry(hive: str, key_path: str, value_name: str, expected, invert: bool = False):
    root = winreg.HKEY_LOCAL_MACHINE if hive == "HKLM" else winreg.HKEY_CURRENT_USER
    try:
        key = winreg.OpenKey(root, key_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        value, _ = winreg.QueryValueEx(key, value_name)
        winreg.CloseKey(key)
        result = (value == expected) if expected is not None else bool(value)
        return (not result) if invert else result
    except (FileNotFoundError, OSError):
        return None

def check_dism(feature: str):
    try:
        r = subprocess.run(["dism", "/online", "/get-featureinfo", f"/featurename:{feature}"],
                           capture_output=True, text=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        return "State : Enabled" in r.stdout
    except Exception:
        return None

def run_check(c: dict):
    t = c["type"]
    if t == "service":
        return check_service(c["service_name"])
    if t == "process":
        return check_process(c["process_name"])
    if t == "registry":
        return check_registry(c["hive"], c["key_path"], c["value_name"],
                              c.get("expected_enabled"), c.get("invert", False))
    if t == "dism_feature":
        r = check_dism(c["feature_name"])
        if r is None and "fallback" in c:
            r = run_check(c["fallback"])
        return r
    return None

def evaluate_service(svc: dict):
    results = [run_check(c) for c in svc["checks"]]
    if any(r is True for r in results):
        return True
    if all(r is False for r in results):
        return False
    return None


# ── Startup registry helpers ──────────────────────────────────────────────────

def _exe_path() -> str:
    return f'"{sys.executable}" "{os.path.abspath(__file__)}"'

def set_startup(mode: str):
    """mode: 'off' | 'normal' | 'minimized'"""
    try:
        key = _reg.OpenKey(_reg.HKEY_CURRENT_USER, STARTUP_KEY, 0, _reg.KEY_SET_VALUE)
        if mode == "off":
            try:
                _reg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        else:
            cmd = _exe_path()
            if mode == "minimized":
                cmd += " --minimized"
            _reg.SetValueEx(key, APP_NAME, 0, _reg.REG_SZ, cmd)
        _reg.CloseKey(key)
    except OSError:
        pass


# ── Main window ───────────────────────────────────────────────────────────────

class TarryApp(QWidget):
    def __init__(self, start_minimized: bool = False):
        super().__init__()
        self.services      = load_json(SERVICES_FILE)["services"]
        self.about_data    = load_json(ABOUT_FILE) if os.path.exists(ABOUT_FILE) else {}
        self.settings      = load_settings()
        self.status_labels = {}
        self.timer         = QTimer()
        self.startup_timer = QTimer()
        self.startup_timer.setSingleShot(True)

        self._setup_window()
        self._build_ui()
        self._setup_tray()
        self._apply_timer_setting()

        if start_minimized:
            self.hide()
        else:
            self.show()

    # ── Window geometry ───────────────────────────────────────────────────────

    def _setup_window(self):
        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        screen = QApplication.primaryScreen().geometry()
        w = int(screen.width()  * 0.20)
        h = int(screen.height() * 0.50)
        margin = 10
        x = screen.width()  - w - margin
        y = screen.height() - h - margin - 40   # 40 = taskbar clearance
        self.setFixedSize(w, h)
        self.move(x, y)

    # ── Master UI ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setStyleSheet(f"""
            QWidget      {{ background:{C_BG}; color:{C_TEXT};
                            font-family:'Segoe UI',Arial,sans-serif; font-size:{FS_SERVICE}; }}
            QScrollArea  {{ border:none; }}
            QScrollBar:vertical {{ background:#2a2a2a; width:5px; border-radius:2px; }}
            QScrollBar::handle:vertical {{ background:{C_SCROLLBAR}; border-radius:2px; }}
            QPushButton  {{ background:{C_ACCENT}; color:#fff; border:none;
                            border-radius:3px; padding:4px 8px; font-size:{FS_NAV}; }}
            QPushButton:hover  {{ background:#4a8be5; }}
            QPushButton:pressed {{ background:#2a5bb5; }}
            QRadioButton {{ font-size:{FS_SETTINGS}; color:{C_TEXT}; }}
            QCheckBox    {{ font-size:{FS_SETTINGS}; color:{C_TEXT}; }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        title = QLabel(f"  🛡 {APP_NAME}")
        title.setStyleSheet(
            f"background:{C_BG_DARK}; color:{C_TEXT_DIM}; font-size:{FS_TITLE};"
            "font-weight:bold; padding:6px 4px;"
        )
        root.addWidget(title)

        # Nav bar
        nav = QHBoxLayout()
        nav.setContentsMargins(4, 2, 4, 2)
        nav.setSpacing(4)
        self._nav_btns = {}
        for idx, label in enumerate(["Monitor", "Settings", "About"]):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(
                f"font-size:{FS_NAV}; background:{C_BG_DARK}; color:{C_TEXT_DIM};"
                "border:none; padding:4px 6px; border-radius:3px;"
            )
            btn.clicked.connect(lambda _, i=idx: self._switch_page(i))
            nav.addWidget(btn)
            self._nav_btns[idx] = btn
        nav.addStretch()
        nav_widget = QWidget()
        nav_widget.setStyleSheet(f"background:{C_BG_DARK};")
        nav_widget.setLayout(nav)
        root.addWidget(nav_widget)

        # Stacked pages
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_monitor_page())
        self.stack.addWidget(self._build_settings_page())
        self.stack.addWidget(self._build_about_page())
        root.addWidget(self.stack)

        self._switch_page(0)

    def _switch_page(self, idx: int):
        self.stack.setCurrentIndex(idx)
        for i, btn in self._nav_btns.items():
            if i == idx:
                btn.setStyleSheet(
                    f"font-size:{FS_NAV}; background:{C_NAV_SEL}; color:#fff;"
                    "border:none; padding:4px 6px; border-radius:3px;"
                )
            else:
                btn.setStyleSheet(
                    f"font-size:{FS_NAV}; background:{C_BG_DARK}; color:{C_TEXT_DIM};"
                    "border:none; padding:4px 6px; border-radius:3px;"
                )

    # ── Monitor page ──────────────────────────────────────────────────────────

    def _build_monitor_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        self.list_layout = QVBoxLayout(container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(0)
        scroll.setWidget(container)
        layout.addWidget(scroll)

        groups = {}
        for svc in self.services:
            groups.setdefault(svc["group"], []).append(svc)

        for group_name, items in groups.items():
            hdr = QLabel(f"  {group_name}")
            hdr.setStyleSheet(
                f"background:{C_GROUP_HDR}; color:{C_TEXT_DIM}; font-size:{FS_GROUP};"
                "font-weight:bold; padding:4px 2px; letter-spacing:0.5px;"
            )
            self.list_layout.addWidget(hdr)
            for svc in items:
                self.list_layout.addWidget(self._make_row(svc))

        self.list_layout.addStretch()
        return page

    def _make_row(self, svc: dict) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"border-bottom:1px solid #2a2a2a;")
        row = QHBoxLayout(frame)
        row.setContentsMargins(8, 3, 8, 3)
        row.setSpacing(4)

        name_lbl = QLabel(svc["name"])
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        name_lbl.setWordWrap(True)
        # ◄ Service name text size: change FS_SERVICE at top
        name_lbl.setStyleSheet(f"color:{C_TEXT}; background:transparent; border:none; font-size:{FS_SERVICE};")

        status_lbl = QLabel("…")
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        status_lbl.setFixedWidth(72)
        # ◄ Status badge text size: change FS_STATUS at top
        status_lbl.setStyleSheet(f"color:{C_TEXT_DIM}; background:transparent; border:none; font-size:{FS_STATUS};")

        row.addWidget(name_lbl, stretch=1)
        row.addWidget(status_lbl, stretch=0)
        self.status_labels[svc["key"]] = status_lbl
        return frame

    # ── Settings page ─────────────────────────────────────────────────────────

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        def section(text):
            lbl = QLabel(text)
            # ◄ Settings section header size: change font-size value below
            lbl.setStyleSheet(f"color:{C_TEXT_DIM}; font-size:10px; font-weight:bold; margin-top:6px;")
            return lbl

        # -- Startup --
        layout.addWidget(section("STARTUP"))
        self._startup_grp = QButtonGroup(self)
        for val, label in [("off", "Disabled"), ("normal", "Start with Windows"),
                           ("minimized", "Start minimized to tray")]:
            rb = QRadioButton(label)
            rb.setProperty("startup_val", val)
            if self.settings.get("startup") == val:
                rb.setChecked(True)
            self._startup_grp.addButton(rb)
            layout.addWidget(rb)
        self._startup_grp.buttonClicked.connect(self._on_startup_changed)

        # -- Check interval --
        layout.addWidget(section("CHECK INTERVAL"))
        self._interval_grp = QButtonGroup(self)
        for val, label in [("startup_once", f"Once at startup (after {self.settings['startup_delay_s']}s delay)"),
                           ("minute", "Every minute"),
                           ("hour",   "Every hour")]:
            rb = QRadioButton(label)
            rb.setProperty("interval_val", val)
            if self.settings.get("run_interval") == val:
                rb.setChecked(True)
            self._interval_grp.addButton(rb)
            layout.addWidget(rb)
        self._interval_grp.buttonClicked.connect(self._on_interval_changed)

        # -- Manual run --
        layout.addWidget(section("MANUAL"))
        run_btn = QPushButton("▶  Run checks now")
        run_btn.clicked.connect(self.check_all_status)
        layout.addWidget(run_btn)

        layout.addStretch()
        return page

    # ── About page ────────────────────────────────────────────────────────────

    def _build_about_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(12, 12, 12, 12)
        inner_layout.setSpacing(6)

        if self.about_data:
            for field, value in self.about_data.items():
                if field == "description":
                    lbl = QLabel(str(value))
                    lbl.setWordWrap(True)
                    # ◄ About page text size: change FS_ABOUT at top
                    lbl.setStyleSheet(f"color:{C_TEXT}; font-size:{FS_ABOUT}; line-height:1.5;")
                    inner_layout.addWidget(lbl)
                else:
                    row = QHBoxLayout()
                    key_lbl = QLabel(f"{field}:")
                    key_lbl.setStyleSheet(f"color:{C_TEXT_DIM}; font-size:{FS_ABOUT}; font-weight:bold;")
                    key_lbl.setFixedWidth(80)
                    val_lbl = QLabel(str(value))
                    val_lbl.setWordWrap(True)
                    val_lbl.setStyleSheet(f"color:{C_TEXT}; font-size:{FS_ABOUT};")
                    row.addWidget(key_lbl)
                    row.addWidget(val_lbl, stretch=1)
                    inner_layout.addLayout(row)
        else:
            lbl = QLabel("about/about.json not found.")
            lbl.setStyleSheet(f"color:{C_TEXT_DIM}; font-size:{FS_ABOUT};")
            inner_layout.addWidget(lbl)

        inner_layout.addStretch()
        scroll.setWidget(inner)
        layout.addWidget(scroll)
        return page

    # ── Tray ──────────────────────────────────────────────────────────────────

    def _setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self._make_icon())
        menu = QMenu()
        menu.addAction("Show / Hide").triggered.connect(self._toggle_visibility)
        menu.addAction("Refresh Now").triggered.connect(self.check_all_status)
        menu.addSeparator()
        menu.addAction("Exit").triggered.connect(QApplication.quit)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _make_icon(self, color=QColor(100, 100, 100)) -> QIcon:
        px = QPixmap(64, 64)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(4, 4, 56, 56)
        p.end()
        return QIcon(px)

    # ── Timer / interval logic ────────────────────────────────────────────────

    def _apply_timer_setting(self):
        self.timer.stop()
        self.startup_timer.stop()
        interval = self.settings.get("run_interval", "minute")

        if interval == "startup_once":
            delay_ms = self.settings.get("startup_delay_s", 10) * 1000
            self.startup_timer.timeout.connect(self.check_all_status)
            self.startup_timer.start(delay_ms)
        elif interval == "minute":
            self.timer.timeout.connect(self.check_all_status)
            self.timer.start(60_000)
            self.check_all_status()
        elif interval == "hour":
            self.timer.timeout.connect(self.check_all_status)
            self.timer.start(3_600_000)
            self.check_all_status()

    def _on_interval_changed(self, btn):
        self.settings["run_interval"] = btn.property("interval_val")
        save_json(SETTINGS_FILE, self.settings)
        self._apply_timer_setting()

    def _on_startup_changed(self, btn):
        mode = btn.property("startup_val")
        self.settings["startup"] = mode
        save_json(SETTINGS_FILE, self.settings)
        set_startup(mode)

    # ── Status checks ─────────────────────────────────────────────────────────

    def check_all_status(self):
        active = 0
        total  = len(self.services)
        for svc in self.services:
            status = evaluate_service(svc)
            self._update_label(svc["key"], status)
            if status is True:
                active += 1
        self._update_tray_icon(active, total)

    def _update_label(self, key: str, status):
        lbl = self.status_labels.get(key)
        if lbl is None:
            return
        if status is None:
            lbl.setText("Unknown")
            lbl.setStyleSheet(f"color:{C_UNKNOWN}; background:transparent; border:none; font-size:{FS_STATUS};")
        elif status:
            lbl.setText("ACTIVE ⚠")
            lbl.setStyleSheet(f"color:{C_ACTIVE}; font-weight:bold; background:transparent; border:none; font-size:{FS_STATUS};")
        else:
            lbl.setText("Disabled ✓")
            lbl.setStyleSheet(f"color:{C_DISABLED}; background:transparent; border:none; font-size:{FS_STATUS};")

    def _update_tray_icon(self, active: int, total: int):
        if active == 0:
            color, tip = QColor(0, 200, 0), "All telemetry disabled"
        elif active < total / 2:
            color, tip = QColor(255, 165, 0), f"{active}/{total} services active"
        else:
            color, tip = QColor(255, 0, 0), f"⚠ {active}/{total} services active"
        self.tray_icon.setIcon(self._make_icon(color))
        self.tray_icon.setToolTip(tip)

    # ── Events ────────────────────────────────────────────────────────────────

    def _toggle_visibility(self):
        self.hide() if self.isVisible() else (self.show(), self.activateWindow())

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_visibility()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(APP_NAME, "Minimized to tray",
                                   QSystemTrayIcon.MessageIcon.Information, 2000)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    minimized = "--minimized" in sys.argv
    window = TarryApp(start_minimized=minimized)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
