"""
alphaJET Interface-Tool -- Marvin Köllner --
Steuerprogramm für König & Bauer alphaJET Tintenstrahldrucker
Protokoll: G-PRINT V3.0.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog
import socket
import json
import os
import sys
import subprocess
import threading
import time
import shutil
import urllib.request
import urllib.error
import tempfile
import re
import hashlib

from utils import (
    BASE_DIR, RES_DIR, CONFIG_FILE, FUNC_FILE,
    LABELS_DIR, CONFIGS_DIR, PRINTCTL_DIR, LOGOS_DIR, LOGS_DIR,
    THEMES_DIR, PROFILES_FILE, MOCK_FTP_DIR,
    DEVICE_FTP, LABEL_EXTS, CONFIG_EXTS, PRINTCTL_EXTS, ALL_EXTS,
    has_ext, C, C_DARK, C_LIGHT, ACTIVE_THEME,
    ToolTip, lazy_tab, _ensure, load_json, save_json, pretty_xml,
    apply_theme,
    validate_ip, validate_port, validate_gprint_xml,
    security_log, sanitize_error,
)

# ─── Eingebaute Schnell-Befehle ───────────────────────────────────────────────
BUILTIN_COMMANDS = [
    ("Verbindungstest",    "<GP><MAINSTATE/></GP>"),
    ("Status abfragen",    "<GP><SYS><STATE/></SYS></GP>"),
    ("Firmware-Version",   "<GP><VERSION/></GP>"),
    ("Board-Info",         "<GP><BOARDINFO/></GP>"),
    ("Board-Info (ext.)",  "<GP><BOARDINFO_EXT/></GP>"),
    ("Datum / Uhrzeit",    "<GP><SYS><DATETIME/></SYS></GP>"),
    ("GUI sperren",        '<GP><GUICONTROL aMode="1"></GUICONTROL></GP>'),
    ("GUI schliessen",     '<GP><GUICONTROL aMode="2"></GUICONTROL></GP>'),
    ("GUI neu starten",    '<GP><GUICONTROL aMode="3"></GUICONTROL></GP>'),
    ("Drucken  START",     "<GP><START/></GP>"),
    ("Drucken  STOP",      "<GP><STOP/></GP>"),
]

# ─── Templates ────────────────────────────────────────────────────────────────
CONFIG_TEMPLATE = """\
<GP>
  <CONFIG>
    <STROKEDIV>23</STROKEDIV>
    <DENSITY>1</DENSITY>
    <PRINTHEIGHT>1</PRINTHEIGHT>
    <PRINTMODE>pm24</PRINTMODE>
    <PIXHEIGHT>24</PIXHEIGHT>
    <STROKERES>257.733585863</STROKERES>
    <LAYOUT>adj</LAYOUT>
    <PRINTOPT>fast</PRINTOPT>
  </CONFIG>
  <CONFIGINSTALL>
    <DISTDIV>1</DISTDIV>
    <ENC>intern</ENC>
    <DISTRES>11.205808081</DISTRES>
    <PSTYPE>npn</PSTYPE>
    <PSINV>0</PSINV>
    <PSENCSUPPLY>ext</PSENCSUPPLY>
    <INPUTACTIVE>hi</INPUTACTIVE>
    <INPUTSUPPLY>ext</INPUTSUPPLY>
    <OUTPUTSUPPLY>ext</OUTPUTSUPPLY>
    <OFFSFWD>0</OFFSFWD>
    <OFFSBWD>10</OFFSBWD>
  </CONFIGINSTALL>
</GP>"""

LABEL_TEMPLATE = """\
<GP>
  <LAB>
    <OBJ>
      <TYPE>text</TYPE>
      <X>0</X>
      <Y>0</Y>
      <SW>1</SW>
      <SS>0</SS>
      <MAG>1</MAG>
      <NEG>0</NEG>
      <BWD>0</BWD>
      <ANGLE>0</ANGLE>
      <TEXT>Hallo Welt</TEXT>
      <FONT aFace="m7x5" aSize="7"/>
    </OBJ>
  </LAB>
</GP>"""

PRINTCONTROL_TEMPLATE = """\
<GP>
  <PRINTCONTROL>
    <BASIC>
      <DIST>0</DIST>
      <STARTDIR>both</STARTDIR>
      <PRINTSTART>cont</PRINTSTART>
      <IGNOREDPM>0</IGNOREDPM>
    </BASIC>
    <OPS>off</OPS>
    <DISTANCE>
      <PRODCALWAYSCOUNT>0</PRODCALWAYSCOUNT>
      <FLIGHT>0</FLIGHT>
      <MEASUREDIST>start_start</MEASUREDIST>
    </DISTANCE>
    <ALARMRELAY>
      <SWNOTREADY>0</SWNOTREADY>
      <SWSERVICE>0</SWSERVICE>
      <SWERROR>0</SWERROR>
      <SWCONS>0</SWCONS>
      <TYPE>no</TYPE>
    </ALARMRELAY>
    <TEXTLIST>
      <ENABLED>0</ENABLED>
      <LASTLIST/>
    </TEXTLIST>
  </PRINTCONTROL>
</GP>"""

# ─── Standard-Konfiguration ───────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "ip":          "192.168.0.1",
    "port":        3000,
    "subnet":      "255.255.255.0",
    "gateway":     "0.0.0.0",
    "name":        "alphaJET",
    "dhcp":        False,
    "timeout":     5,
    "proxy_port":  3000,
    "mock_port":   3002,
    "device":      "AJD",
    "update_url":  "https://raw.githubusercontent.com/98koellnertd-code/alphajet-tool/main/version.json",
    "auto_update": True,
}

# ─── Hilfsfunktionen ──────────────────────────────────────────────────────────
def get_local_ips():
    ips = []
    try:
        for r in socket.getaddrinfo(socket.gethostname(), None):
            ip = r[4][0]
            if ":" not in ip and ip != "127.0.0.1" and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    return ips or ["Nicht ermittelbar"]

def guess_required_pc_ip(printer_ip):
    try:
        parts = printer_ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.111"
    except Exception:
        pass
    return ""

def send_gprint(ip, port, command, timeout=10):
    """Sendet einen G-PRINT-Befehl und gibt die Antwort zurück.
    Nutzt bytearray für O(n) Akkumulation statt O(n²) bytes-Konkatenation."""
    def _recv_until_gp(sock):
        buf = bytearray()
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buf.extend(chunk)
                if b"</GP>" in buf:
                    break
        except socket.timeout:
            pass
        return buf

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect((ip, port))
        welcome  = _recv_until_gp(s)
        s.sendall(command.encode("utf-8"))
        response = _recv_until_gp(s)
        full = welcome.decode("utf-8", errors="replace")
        if response:
            full += "\n" + response.decode("utf-8", errors="replace")
        return full.strip()

# ═════════════════════════════════════════════════════════════════════════════
#  App-Version
# ═════════════════════════════════════════════════════════════════════════════
APP_VERSION      = "2.1.2"
APP_NAME         = "K & B alphaJET - Servicetechniker Tool"

# ═════════════════════════════════════════════════════════════════════════════
#  Haupt-Anwendung
# ═════════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME}  v{APP_VERSION}")
        try:
            self.iconbitmap(os.path.join(BASE_DIR, "icon.ico"))
        except Exception:
            pass
        self.geometry("1400x960")
        self.minsize(1050, 720)
        self.configure(bg=C["bg"])
        self.overrideredirect(True)   # Windows-Titelleiste entfernen
        self._drag_x = 0             # Drag-to-Move Zustand
        self._drag_y = 0
        # Maximiert auf Arbeitsfläche (Work Area = Screen minus Taskleiste).
        # state("zoomed") ignoriert mit overrideredirect die Taskleiste →
        # stattdessen SPI_GETWORKAREA per ctypes abfragen.
        try:
            import ctypes, ctypes.wintypes
            rc = ctypes.wintypes.RECT()
            ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rc), 0)
            self.geometry(f"{rc.right - rc.left}x{rc.bottom - rc.top}+{rc.left}+{rc.top}")
        except Exception:
            try:
                self.state("zoomed")   # Fallback (nicht-Windows)
            except Exception:
                pass

        self.config_data  = load_json(CONFIG_FILE, DEFAULT_CONFIG)
        self.func_data    = load_json(FUNC_FILE, {})
        self.profiles     = load_json(PROFILES_FILE, {})
        self._last_cmd_time  = None
        self._cmd_history    = []
        self._printer_ping_id = None   # after-ID für Drucker-Ping (cancel-sicher)
        self._ping_active     = False  # True erst nach erfolgreichem Connect

        self._apply_style()
        self._build_ui()
        self._apply_keybindings()
        self._start_clock()
        self._init_session_log()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(0,   lambda: threading.Thread(target=self._run_migration, daemon=True).start())
        self.after(200, lambda: threading.Thread(
            target=lambda: _ensure(("Pillow", "PIL"), ("openpyxl", "openpyxl")),
            daemon=True).start())
        if self.config_data.get("auto_update", True):
            self.after(2000, lambda: threading.Thread(
                target=self._update_check, args=(False,), daemon=True).start())

    # ── Style ─────────────────────────────────────────────────────────────────
    def _apply_style(self):
        apply_theme(self)   # gesamtes Styling liegt in utils.apply_theme()

    # ── Haupt-UI ──────────────────────────────────────────────────────────────
    
    def _build_ui(self):
        tk.Frame(self, bg=C["accent"], height=2).pack(fill="x")

        hdr = tk.Frame(self, bg=C["header"], height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        left_hdr = tk.Frame(hdr, bg=C["header"])
        left_hdr.pack(side="left", fill="y", padx=(16, 0))
        tk.Label(left_hdr, text=" K & B",
                 bg=C["header"], fg=C["accent"],
                 font=("Segoe UI", 14, "bold")).pack(side="left")
        tk.Label(left_hdr, text="  Servicetechniker Tool",
                 bg=C["header"], fg=C["text"],
                 font=("Segoe UI", 12)).pack(side="left")
        tk.Label(left_hdr,
                 text=f"   alphaJet  ·  v{APP_VERSION}",
                 bg=C["header"], fg=C["subtext"],
                 font=("Segoe UI", 8)).pack(side="left", padx=(8, 0))

        right_hdr = tk.Frame(hdr, bg=C["header"])
        right_hdr.pack(side="right", fill="y", padx=(0, 12))

        # ── Hilfsfunktionen für einheitliche Header-Elemente ─────────────────
        def _hdr_sep():
            """Dünner vertikaler Trenner im Header."""
            tk.Frame(right_hdr, bg=C["border"], width=1
                     ).pack(side="right", fill="y", padx=8, pady=14)

        def _hdr_btn(text, cmd, tip=""):
            """Einheitlicher Header-Button (gleiche Größe für alle)."""
            b = tk.Button(right_hdr, text=text, command=cmd,
                          bg=C["surface2"], fg=C["text"],
                          font=("Segoe UI", 10), relief="flat", bd=0,
                          cursor="hand2", width=2,
                          activebackground=C["overlay"],
                          activeforeground=C["accent"])
            b.pack(side="right", pady=14, padx=2)
            if tip:
                ToolTip(b, tip)
            return b

        # ── Fenster-Steuerung: × Schließen / — Minimieren (ganz rechts) ─────
        _wbtn_close = tk.Button(
            right_hdr, text="✕", command=self._on_close,
            bg=C["header"], fg=C["red"],
            activebackground=C["red"], activeforeground="#ffffff",
            font=("Segoe UI", 11, "bold"), relief="flat", bd=0,
            cursor="hand2", width=3)
        _wbtn_close.pack(side="right", fill="y")
        ToolTip(_wbtn_close, "Anwendung schließen  (Alt+F4)")

        _wbtn_min = tk.Button(
            right_hdr, text="—", command=self._minimize_window,
            bg=C["header"], fg=C["subtext"],
            activebackground=C["overlay"], activeforeground=C["text"],
            font=("Segoe UI", 11), relief="flat", bd=0,
            cursor="hand2", width=3)
        _wbtn_min.pack(side="right", fill="y")
        ToolTip(_wbtn_min, "Minimieren")

        _hdr_sep()

        # ── Buttons: ? und Theme-Toggle ───────────────────────────────────────
        _hdr_btn("?", self._show_about, "Über diese App")

        _theme_icon = "☀" if ACTIVE_THEME == "dark" else "☾"
        _theme_tip  = "Zu hellem Design wechseln" if ACTIVE_THEME == "dark" \
                      else "Zu dunklem Design wechseln"
        self._theme_btn = _hdr_btn(_theme_icon, self._toggle_theme, _theme_tip)

        _hdr_sep()

        # ── Datum ─────────────────────────────────────────────────────────────
        self._date_lbl = tk.Label(right_hdr, text="",
                                   bg=C["header"], fg=C["subtext"],
                                   font=("Consolas", 9))
        self._date_lbl.pack(side="right", pady=14)

        _hdr_sep()

        # ── Uhrzeit ───────────────────────────────────────────────────────────
        self._clock_lbl = tk.Label(right_hdr, text="",
                                    bg=C["header"], fg=C["text"],
                                    font=("Consolas", 10, "bold"))
        self._clock_lbl.pack(side="right", pady=14)

        _hdr_sep()

        # ── IP-Adresse ────────────────────────────────────────────────────────
        self._hdr_ip = tk.Label(right_hdr,
                                 text=self.config_data.get("ip", "—"),
                                 bg=C["header"], fg=C["subtext"],
                                 font=("Consolas", 10))
        self._hdr_ip.pack(side="right", pady=14)
        tk.Label(right_hdr, text="IP ",
                 bg=C["header"], fg=C["subtext"],
                 font=("Segoe UI", 8, "bold")).pack(side="right", pady=14)

        _hdr_sep()

        # ── Druckerverbindung ─────────────────────────────────────────────────
        status_box = tk.Frame(right_hdr, bg=C["header"])
        status_box.pack(side="right", fill="y", pady=14)
        self.status_dot = tk.Label(status_box, text="●",
                                    bg=C["header"], fg=C["red"],
                                    font=("Segoe UI", 9))
        self.status_dot.pack(side="left")
        self.status_lbl = tk.Label(status_box, text="Nicht verbunden",
                                    bg=C["header"], fg=C["subtext"],
                                    font=("Segoe UI", 9))
        self.status_lbl.pack(side="left", padx=(3, 0))

        # ── Fenster-Drag: Header + Logo-Bereich als Ziehfläche ───────────────
        for _w in [hdr, left_hdr] + list(left_hdr.winfo_children()):
            _w.bind("<ButtonPress-1>", self._drag_start, add="+")
            _w.bind("<B1-Motion>",     self._drag_move,  add="+")

        tk.Frame(self, bg=C["border"], height=1).pack(fill="x")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        self.tab_net      = ttk.Frame(nb)
        self.tab_cmd      = ttk.Frame(nb)
        self.tab_func     = ttk.Frame(nb)
        self.tab_label    = ttk.Frame(nb)
        self.tab_config   = ttk.Frame(nb)
        self.tab_printctl = ttk.Frame(nb)
        self.tab_monitor  = ttk.Frame(nb)
        self.tab_editor   = ttk.Frame(nb)
        self.tab_logo     = ttk.Frame(nb)
        self.tab_ftp      = ttk.Frame(nb)
        self.tab_az       = ttk.Frame(nb)

        nb.add(self.tab_net,      text=" 🌐  Netzwerk ")
        nb.add(self.tab_cmd,      text=" ⚡  Befehle ")
        nb.add(self.tab_func,     text=" ƒ  Funktionen ")
        nb.add(self.tab_label,    text=" 📄  Labels ")
        nb.add(self.tab_config,   text=" ⚙️  Configs ")
        nb.add(self.tab_printctl, text=" 🖨️  PrintControls ")
        nb.add(self.tab_monitor,  text=" 📡  Monitor ")
        nb.add(self.tab_editor,   text=" ✏️  Label Editor ")
        nb.add(self.tab_logo,     text=" 🎨  Logo Editor ")
        nb.add(self.tab_ftp,      text=" 📂  FTP ")
        nb.add(self.tab_az,       text=" 📑  AZ & Reisekosten ")

        self._build_network_tab()
        self._build_cmd_tab()
        self._build_func_tab()
        self._build_label_tab()
        self._build_config_tab()
        self._build_printctl_tab()

        # Schwere Tabs: werden erst beim ersten Klick gebaut
        self._label_editor_ref = None
        self._logo_editor_ref  = None
        self._monitor_tab      = None

        lazy_tab(nb, self.tab_monitor, self._build_monitor_tab)
        lazy_tab(nb, self.tab_editor,  self._build_label_editor_tab)
        lazy_tab(nb, self.tab_logo,    self._build_logo_editor_tab)
        lazy_tab(nb, self.tab_ftp,      self._build_ftp_tab)
        lazy_tab(nb, self.tab_az,       self._build_az_tab)

        # Log-Leiste
        tk.Frame(self, bg=C["border"], height=1).pack(fill="x")
        log_outer = tk.Frame(self, bg=C["header"])
        log_outer.pack(fill="x")
        log_hdr = tk.Frame(log_outer, bg=C["header"])
        log_hdr.pack(fill="x", padx=10, pady=(5, 2))
        tk.Label(log_hdr, text="Kommunikations-Log",
                 bg=C["header"], fg=C["accent"],
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Button(log_hdr, text="Leeren",
                   command=lambda: self.log.delete("1.0", "end")).pack(side="right")
        for h, lbl in [("4", "S"), ("7", "M"), ("12", "L")]:
            tk.Button(log_hdr, text=lbl, bg=C["border"], fg=C["text"],
                      font=("Segoe UI", 8), relief="flat", padx=6,
                      command=lambda hh=h: self._set_log_height(hh)
                      ).pack(side="right", padx=1)
        tk.Label(log_hdr, text="Größe:", bg=C["header"], fg=C["subtext"],
                 font=("Segoe UI", 8)).pack(side="right", padx=(8, 2))
        self._log_visible = True
        self._log_toggle  = tk.Button(
            log_hdr, text="▼", bg=C["header"], fg=C["subtext"],
            font=("Segoe UI", 9), relief="flat", bd=0,
            command=self._toggle_log)
        self._log_toggle.pack(side="right", padx=(10, 4))

        self.log = scrolledtext.ScrolledText(
            log_outer, height=7,
            bg=C["header"], fg=C["text"],
            insertbackground=C["text"],
            font=("Consolas", 9), relief="flat", bd=0,
            selectbackground=C["overlay"])
        self.log.pack(fill="x", padx=10, pady=(0, 8))
        self.log.tag_config("send",  foreground=C["accent"])
        self.log.tag_config("recv",  foreground=C["green"])
        self.log.tag_config("error", foreground=C["red"])
        self.log.tag_config("info",  foreground=C["purple"])
        self.log.tag_config("warn",  foreground=C["yellow"])

    # ══════════════════════════════════════════════════════════════════════════
    #  Tabs werden genertiert nach dem anklicken
    # ══════════════════════════════════════════════════════════════════════════
    def _run_migration(self):
        for _old, _new in [
            (os.path.join(BASE_DIR, "config.json"),    CONFIG_FILE),
            (os.path.join(BASE_DIR, "functions.json"), FUNC_FILE),
        ]:
            if os.path.exists(_old) and not os.path.exists(_new):
                shutil.copy(_old, _new)
        for _old_dir, _new_dir in [
            (os.path.join(BASE_DIR, "labels"),  LABELS_DIR),
            (os.path.join(BASE_DIR, "configs"), CONFIGS_DIR),
        ]:
            if os.path.isdir(_old_dir):
                for _f in os.listdir(_old_dir):
                    _src = os.path.join(_old_dir, _f)
                    _dst = os.path.join(_new_dir, _f)
                    if os.path.isfile(_src) and not os.path.exists(_dst):
                        shutil.copy(_src, _dst)

    def _build_monitor_tab(self):
        if self._monitor_tab is not None:
            return
        from monitor import MonitorTab
        self._monitor_tab = MonitorTab(
            self.tab_monitor,
            run_cmd=self._run_cmd,
            log=self._log,
            config_data=self.config_data,
        )
        self._monitor_tab.pack(fill="both", expand=True)

    def _build_label_editor_tab(self):
        if self._label_editor_ref is not None:
            return
        from label_editor import LabelEditorTab
        self._label_editor_ref = LabelEditorTab(
            self.tab_editor, LABELS_DIR, self._run_cmd, self._log)


    def _build_logo_editor_tab(self):
        if self._logo_editor_ref is not None:
            return
        from label_editor import LogoEditorTab
        self._logo_editor_ref = LogoEditorTab(
            self.tab_logo, self._run_cmd, self._log, LOGOS_DIR)

    def _build_ftp_tab(self):
        if getattr(self, "_ftp_tab", None) is not None:
            return
        # Abhängige Tabs bauen – jeder einzeln abgesichert
        for builder, name in [
            (self._build_monitor_tab,      "Monitor"),
            (self._build_label_editor_tab, "Label Editor"),
            (self._build_logo_editor_tab,  "Logo Editor"),
        ]:
            try:
                builder()
            except Exception as e:
                self._log(f"[FTP] {name}-Tab konnte nicht initialisiert werden: {e}", "warn")
        try:
            from ftp import FTPTab
            self._ftp_tab = FTPTab(
                self.tab_ftp,
                log=self._log,
                config_data=self.config_data,
                label_editor_ref=self._label_editor_ref,
                logo_editor_ref=self._logo_editor_ref,
                file_refresh_cb=self._file_refresh,
                switch_tab_cb=self._switch_to_tab,
                cfg_name_var=self.cfg_name_var,
                cfg_editor=self.cfg_editor,
                ctl_name_var=self.ctl_name_var,
                ctl_editor=self.ctl_editor,
                monitor_tab=self._monitor_tab,
            )
            self._ftp_tab.pack(fill="both", expand=True)
        except Exception as e:
            self._log(f"[FTP] Tab konnte nicht geladen werden: {e}", "error")
            import tkinter as _tk
            _tk.Label(self.tab_ftp,
                      text=f"FTP-Tab Ladefehler:\n{e}",
                      fg=C["red"], bg=C["surface"],
                      font=("Segoe UI", 10)).pack(pady=40)

    def _build_az_tab(self):
        from az_reisekosten import AZReisekostenTab
        AZReisekostenTab(self.tab_az).pack(fill="both", expand=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  Tab: Netzwerk
    # ══════════════════════════════════════════════════════════════════════════
    def _build_network_tab(self):
        outer = tk.Frame(self.tab_net, bg=C["surface"])
        outer.pack(fill="both", expand=True, padx=16, pady=14)
        left  = tk.Frame(outer, bg=C["surface"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        right = tk.Frame(outer, bg=C["surface"])
        right.pack(side="left", fill="y", padx=(10, 0))

        lf = ttk.LabelFrame(left, text="  Drucker-Konfiguration (Ziel-Gerät)")
        lf.pack(fill="x", pady=(0, 10))
        lf.columnconfigure(1, weight=1)

        fields = [
            ("IP-Adresse des Druckers:", "ip",      "z.B. 192.168.1.100"),
            ("Port:",                    "port",    "Standard: 3000"),
            ("Subnetzmaske:",            "subnet",  "z.B. 255.255.255.0"),
            ("Standard-Gateway:",        "gateway", "z.B. 192.168.1.1"),
            ("Drucker-Name:",            "name",    "z.B. alphaJET"),
            ("Timeout (Sek.):",          "timeout", "z.B. 5"),
        ]
        self._net_vars = {}
        for row, (label, key, hint) in enumerate(fields):
            tk.Label(lf, text=label, bg=C["surface"], fg=C["text"],
                     font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=12, pady=5)
            var = tk.StringVar(value=str(self.config_data.get(key, "")))
            self._net_vars[key] = var
            ttk.Entry(lf, textvariable=var, width=28).grid(
                row=row, column=1, sticky="ew", padx=12, pady=5)
            tk.Label(lf, text=hint, bg=C["surface"], fg=C["subtext"],
                     font=("Segoe UI", 9)).grid(row=row, column=2, sticky="w", padx=6)

        dhcp_row = tk.Frame(lf, bg=C["surface"])
        dhcp_row.grid(row=len(fields), column=0, columnspan=3, sticky="w", padx=12, pady=5)
        self._dhcp_var = tk.BooleanVar(value=bool(self.config_data.get("dhcp", False)))
        ttk.Checkbutton(dhcp_row, text="DHCP aktivieren",
                        variable=self._dhcp_var).pack(side="left")

        btn_row = tk.Frame(left, bg=C["surface"])
        btn_row.pack(fill="x", pady=(0, 10))
        _b = ttk.Button(btn_row, text="  Speichern", style="Green.TButton",
                        command=self._save_network)
        _b.pack(side="left", padx=(0, 8))
        ToolTip(_b, "Speichert IP-Adresse, Port, Drucker-Name und Timeout\nin der lokalen Konfiguration.")

        cf = ttk.LabelFrame(left, text="  Verbindungstest")
        cf.pack(fill="x")
        btn_cf = tk.Frame(cf, bg=C["surface"])
        btn_cf.pack(fill="x", padx=10, pady=10)
        _b1 = ttk.Button(btn_cf, text="  Verbindung prüfen", style="Green.TButton",
                         command=self._connection_check)
        _b1.pack(side="left", padx=(0, 8))
        ToolTip(_b1, "Testet ob der Drucker per TCP erreichbar ist.\nKeine Daten werden gesendet.\nStartet danach den automatischen Ping (alle 10 s).")
        _b2 = ttk.Button(btn_cf, text="  Drucker-Status", style="Blue.TButton",
                         command=lambda: self._run_cmd("<GP><MAINSTATE/></GP>", "Hauptstatus"))
        _b2.pack(side="left", padx=(0, 8))
        ToolTip(_b2, "Fragt den aktuellen Betriebszustand des Druckers ab\n(Befehl: MAINSTATE).")
        self._disconnect_btn = ttk.Button(btn_cf, text="  Trennen", style="Red.TButton",
                                          command=self._disconnect, state="disabled")
        self._disconnect_btn.pack(side="left")
        ToolTip(self._disconnect_btn, "Stoppt den automatischen Ping und setzt den\nVerbindungsstatus zurück.")
        self.conn_result = tk.Label(cf, text="", bg=C["surface"],
                                     font=("Segoe UI", 10, "bold"))
        self.conn_result.pack(padx=10, pady=(0, 10))

        uf = ttk.LabelFrame(right, text="  Software-Update")
        uf.pack(fill="x", pady=(0, 8))
        u_row1 = tk.Frame(uf, bg=C["surface"])
        u_row1.pack(fill="x", padx=8, pady=(8, 2))
        tk.Label(u_row1, text="Update-URL (version.json):",
                 bg=C["surface"], fg=C["subtext"],
                 font=("Segoe UI", 8)).pack(side="left", padx=(0, 6))
        self._upd_url_var = tk.StringVar(value=self.config_data.get("update_url", ""))
        ttk.Entry(u_row1, textvariable=self._upd_url_var, width=34
                  ).pack(side="left", fill="x", expand=True)
        u_row2 = tk.Frame(uf, bg=C["surface"])
        u_row2.pack(fill="x", padx=8, pady=(2, 8))
        self._auto_upd_var = tk.BooleanVar(value=self.config_data.get("auto_update", True))
        ttk.Checkbutton(u_row2, text="Beim Start automatisch prüfen",
                        variable=self._auto_upd_var,
                        command=self._save_update_settings).pack(side="left")
        _bchk = ttk.Button(u_row2, text="Jetzt prüfen", style="Blue.TButton",
                           command=lambda: threading.Thread(
                               target=self._update_check, args=(True,), daemon=True).start())
        _bchk.pack(side="right", padx=(0, 4))
        ToolTip(_bchk, "Prüft sofort ob eine neue Version verfügbar ist.")
        _burl = ttk.Button(u_row2, text="URL speichern", style="Green.TButton",
                           command=self._save_update_settings)
        _burl.pack(side="right", padx=(0, 4))
        ToolTip(_burl, "Speichert die Update-URL für den automatischen Versionscheck.")

        pf = ttk.LabelFrame(right, text="  Drucker-Profile")
        pf.pack(fill="x", pady=(0, 8))
        prof_inner = tk.Frame(pf, bg=C["surface"])
        prof_inner.pack(fill="x", padx=6, pady=6)
        self._prof_lb = tk.Listbox(prof_inner, bg=C["surface2"], fg=C["text"],
                                    selectbackground=C["accent"],
                                    font=("Segoe UI", 8), height=3,
                                    relief="flat", bd=0, highlightthickness=0)
        self._prof_lb.pack(side="left", fill="x", expand=True)
        prof_sb = ttk.Scrollbar(prof_inner, orient="vertical",
                                command=self._prof_lb.yview)
        self._prof_lb.config(yscrollcommand=prof_sb.set)
        prof_sb.pack(side="left", fill="y")
        self._prof_lb.bind("<Double-Button-1>", self._profile_load)
        prof_btns = tk.Frame(pf, bg=C["surface"])
        prof_btns.pack(fill="x", padx=6, pady=(0, 6))
        _bps = ttk.Button(prof_btns, text="Speichern", style="Green.TButton", command=self._profile_save)
        _bps.pack(side="left", padx=(0, 4))
        ToolTip(_bps, "Speichert die aktuellen Netzwerkeinstellungen\nals wiederverwendbares Profil.")
        _bpl = ttk.Button(prof_btns, text="Laden", style="Blue.TButton", command=self._profile_load)
        _bpl.pack(side="left", padx=(0, 4))
        ToolTip(_bpl, "Lädt ein gespeichertes Drucker-Profil.")
        _bpd = ttk.Button(prof_btns, text="Löschen", style="Red.TButton", command=self._profile_delete)
        _bpd.pack(side="left")
        ToolTip(_bpd, "Löscht das ausgewählte Profil dauerhaft.")
        self._profile_refresh()

        nf = ttk.LabelFrame(right, text="  Netzwerk-Helfer (dieser PC)")
        nf.pack(fill="both", expand=True)
        tk.Label(nf, text="IP-Adressen dieses PCs:",
                 bg=C["surface"], fg=C["subtext"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(10, 3))
        self.ip_listbox = tk.Listbox(
            nf, bg=C["surface2"], fg=C["text"],
            selectbackground=C["accent"], selectforeground=C["header"],
            font=("Consolas", 10), width=24, height=3,
            activestyle="none", relief="flat", bd=0, highlightthickness=0)
        self.ip_listbox.pack(padx=12, pady=(0, 6), fill="x")
        _bip = ttk.Button(nf, text="  IPs aktualisieren", style="Blue.TButton",
                          command=self._refresh_local_ips)
        _bip.pack(padx=12, fill="x")
        ToolTip(_bip, "Aktualisiert die Liste aller IP-Adressen dieses PCs.")
        tk.Label(nf, text="Status:", bg=C["surface"], fg=C["subtext"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(12, 3))
        self.hint_lbl = tk.Text(
            nf, height=6, bg=C["surface2"], fg=C["yellow"],
            font=("Segoe UI", 9), wrap="word", relief="flat",
            bd=0, state="disabled", highlightthickness=0, padx=8, pady=6)
        self.hint_lbl.pack(padx=12, pady=(0, 8), fill="x")
        _bnw = ttk.Button(nf, text="  Windows-Netzwerkeinstellungen",
                          style="Orange.TButton",
                          command=lambda: os.startfile("ncpa.cpl"))
        _bnw.pack(padx=12, pady=(0, 12), fill="x")
        ToolTip(_bnw, "Öffnet die Windows-Netzwerkadapter-Einstellungen.")
        self._refresh_local_ips()

    def _refresh_local_ips(self):
        ips         = get_local_ips()
        printer_ip  = self._net_vars["ip"].get().strip()
        required_ip = guess_required_pc_ip(printer_ip)
        in_same_net = any(
            ip.rsplit(".", 1)[0] == printer_ip.rsplit(".", 1)[0]
            for ip in ips if ip != "Nicht ermittelbar")
        self.ip_listbox.delete(0, "end")
        for ip in ips:
            self.ip_listbox.insert("end", f"  {ip}")
        self.hint_lbl.config(state="normal")
        self.hint_lbl.delete("1.0", "end")
        if in_same_net:
            self.hint_lbl.insert("end",
                f"Drucker:    {printer_ip}\n"
                f"Dieser PC:  {ips[0]}\n\n"
                "OK – PC und Drucker sind im selben Subnetz.")
            self.hint_lbl.config(fg=C["green"])
        else:
            self.hint_lbl.insert("end",
                f"Drucker:  {printer_ip}\n"
                f"PC:  {', '.join(ips)}\n\n"
                f"ACHTUNG: Nicht im gleichen Subnetz!\n"
                f"PC-IP sollte z.B. {required_ip} sein.")
            self.hint_lbl.config(fg=C["red"])
        self.hint_lbl.config(state="disabled")

    def _save_network(self):
        for key, var in self._net_vars.items():
            val = var.get().strip()
            if key == "ip":
                if not validate_ip(val):
                    messagebox.showerror("Ungültige Eingabe",
                        f"'{val}' ist keine gültige IPv4-Adresse.\n"
                        "Beispiel: 192.168.1.100")
                    return
            elif key == "port":
                try:
                    val = int(val)
                except ValueError:
                    messagebox.showerror("Ungültige Eingabe", "Port muss eine Zahl sein.")
                    return
                if not validate_port(val):
                    messagebox.showerror("Ungültige Eingabe",
                        "Port muss zwischen 1 und 65535 liegen.")
                    return
            elif key == "timeout":
                try:
                    val = int(val)
                except ValueError:
                    messagebox.showerror("Ungültige Eingabe", "Timeout muss eine Zahl sein.")
                    return
                if not (1 <= val <= 120):
                    messagebox.showerror("Ungültige Eingabe",
                        "Timeout muss zwischen 1 und 120 Sekunden liegen.")
                    return
            self.config_data[key] = val
        self.config_data["dhcp"] = self._dhcp_var.get()
        save_json(CONFIG_FILE, self.config_data)
        security_log("CONFIG_CHANGE",
                     f"ip={self.config_data.get('ip')} port={self.config_data.get('port')}", "ok")
        self._log("Konfiguration gespeichert.", "info")
        self._hdr_ip.config(text=self.config_data.get("ip", "—"))
        self._refresh_local_ips()
        messagebox.showinfo("Gespeichert", "Konfiguration wurde gespeichert.")

    # ══════════════════════════════════════════════════════════════════════════
    #  Tab: Befehle
    # ══════════════════════════════════════════════════════════════════════════
    def _build_cmd_tab(self):
        outer = tk.Frame(self.tab_cmd, bg=C["surface"])
        outer.pack(fill="both", expand=True, padx=14, pady=14)
        left  = tk.Frame(outer, bg=C["surface"])
        left.pack(side="left", fill="y", padx=(0, 12))
        right = tk.Frame(outer, bg=C["surface"])
        right.pack(side="left", fill="both", expand=True)

        lf = ttk.LabelFrame(left, text="  Schnell-Befehle")
        lf.pack(fill="y", expand=True)
        for name, cmd in BUILTIN_COMMANDS:
            ttk.Button(lf, text=f"  {name}", width=22,
                       command=lambda c=cmd, n=name: self._run_cmd(c, n)
                       ).pack(pady=2, padx=10, fill="x")

        hist_lf = ttk.LabelFrame(right, text="  Verlauf (letzte 20 Befehle)")
        hist_lf.pack(fill="x", pady=(0, 8))
        hist_inner = tk.Frame(hist_lf, bg=C["surface"])
        hist_inner.pack(fill="x", padx=6, pady=6)
        self._hist_lb = tk.Listbox(hist_inner, bg=C["surface2"], fg=C["text"],
                                    selectbackground=C["accent"],
                                    font=("Segoe UI", 8), height=4,
                                    relief="flat", bd=0, highlightthickness=0)
        self._hist_lb.pack(side="left", fill="x", expand=True)
        hist_sb = ttk.Scrollbar(hist_inner, orient="vertical",
                                command=self._hist_lb.yview)
        self._hist_lb.config(yscrollcommand=hist_sb.set)
        hist_sb.pack(side="left", fill="y")
        self._hist_lb.bind("<Double-Button-1>", self._history_resend)
        _bre = ttk.Button(hist_lf, text="  Erneut senden", style="Blue.TButton",
                          command=self._history_resend)
        _bre.pack(side="left", padx=6, pady=(0, 6))
        ToolTip(_bre, "Sendet den ausgewählten Befehl aus der Historie erneut.")
        # Auto-Ping läuft immer automatisch im Hintergrund (alle 10s)

        lf2 = ttk.LabelFrame(right, text="  Freier G-PRINT Befehl")
        lf2.pack(fill="both", expand=True)
        self.cmd_editor = scrolledtext.ScrolledText(
            lf2, bg=C["surface2"], fg=C["text"],
            insertbackground=C["text"],
            font=("Consolas", 10), relief="flat", bd=0,
            selectbackground=C["overlay"], padx=8, pady=6)
        self.cmd_editor.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        self.cmd_editor.insert("end", "<GP>\n  \n</GP>")
        btn_r = tk.Frame(lf2, bg=C["surface"])
        btn_r.pack(fill="x", padx=8, pady=(0, 8))
        _bsend = ttk.Button(btn_r, text="  Senden", style="Blue.TButton",
                            command=lambda: self._run_cmd(
                                self.cmd_editor.get("1.0", "end").strip(), "Freier Befehl"))
        _bsend.pack(side="left", padx=(0, 6))
        ToolTip(_bsend, "Sendet den eingegebenen G-PRINT XML-Befehl direkt an den Drucker.")
        _bfmt = ttk.Button(btn_r, text="  Formatieren", style="Purple.TButton",
                           command=lambda: self._format_editor(self.cmd_editor))
        _bfmt.pack(side="left", padx=(0, 6))
        ToolTip(_bfmt, "Formatiert den XML-Code mit korrektem Einzug.")
        _bsave = ttk.Button(btn_r, text="  Als Funktion speichern", style="Green.TButton",
                            command=self._save_as_func)
        _bsave.pack(side="left")
        ToolTip(_bsave, "Speichert den aktuellen Befehl als wiederverwendbare Funktion.")

    def _save_as_func(self):
        xml_code = self.cmd_editor.get("1.0", "end").strip()
        if not xml_code:
            return
        name = simpledialog.askstring("Funktion speichern", "Name der Funktion:", parent=self)
        if not name:
            return
        self.func_data[name] = xml_code
        save_json(FUNC_FILE, self.func_data)
        self._log(f"Funktion '{name}' gespeichert.", "info")
        self._refresh_func_list()

    # ══════════════════════════════════════════════════════════════════════════
    #  Tab: Funktionen
    # ══════════════════════════════════════════════════════════════════════════
    def _build_func_tab(self):
        outer = tk.Frame(self.tab_func, bg=C["surface"])
        outer.pack(fill="both", expand=True, padx=14, pady=14)
        left  = tk.Frame(outer, bg=C["surface"])
        left.pack(side="left", fill="y", padx=(0, 12))
        right = tk.Frame(outer, bg=C["surface"])
        right.pack(side="left", fill="both", expand=True)

        lf_list = ttk.LabelFrame(left, text="  Gespeicherte Funktionen")
        lf_list.pack(fill="both", expand=True)
        self.func_list = tk.Listbox(
            lf_list, bg=C["surface2"], fg=C["text"],
            selectbackground=C["accent"], selectforeground=C["header"],
            font=("Segoe UI", 10), width=24,
            activestyle="none", relief="flat", bd=0, highlightthickness=0)
        self.func_list.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        self.func_list.bind("<<ListboxSelect>>", self._on_func_select)
        btn_l = tk.Frame(lf_list, bg=C["surface"])
        btn_l.pack(fill="x", padx=8, pady=(0, 8))
        _bfn = ttk.Button(btn_l, text="  + Neu", style="Green.TButton", command=self._new_func)
        _bfn.pack(side="left", fill="x", expand=True, padx=(0, 4))
        ToolTip(_bfn, "Erstellt eine neue leere Funktion.")
        _bfd = ttk.Button(btn_l, text="  Löschen", style="Red.TButton", command=self._del_func)
        _bfd.pack(side="left", fill="x", expand=True)
        ToolTip(_bfd, "Löscht die ausgewählte Funktion dauerhaft.")

        lf_ed = ttk.LabelFrame(right, text="  Editor")
        lf_ed.pack(fill="both", expand=True)
        name_row = tk.Frame(lf_ed, bg=C["surface"])
        name_row.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(name_row, text="Titel:", bg=C["surface"], fg=C["subtext"],
                 font=("Segoe UI", 9)).pack(side="left", padx=(0, 6))
        self.func_name_var = tk.StringVar()
        ttk.Entry(name_row, textvariable=self.func_name_var).pack(side="left", fill="x", expand=True)
        self.func_editor = scrolledtext.ScrolledText(
            lf_ed, bg=C["surface2"], fg=C["text"],
            insertbackground=C["text"],
            font=("Consolas", 10), relief="flat", bd=0,
            selectbackground=C["overlay"], padx=8, pady=6)
        self.func_editor.pack(fill="both", expand=True, padx=8, pady=4)
        btn_r = tk.Frame(lf_ed, bg=C["surface"])
        btn_r.pack(fill="x", padx=8, pady=(0, 8))
        _bfs = ttk.Button(btn_r, text="  Speichern", style="Green.TButton", command=self._save_func)
        _bfs.pack(side="left", padx=(0, 6))
        _bfe = ttk.Button(btn_r, text="  Ausführen", style="Blue.TButton", command=self._exec_func)
        _bfe.pack(side="left", padx=(0, 6))
        _bff = ttk.Button(btn_r, text="  Formatieren", style="Purple.TButton",
                          command=lambda: self._format_editor(self.func_editor))
        _bff.pack(side="left")
        self._refresh_func_list()

    def _refresh_func_list(self):
        self.func_list.delete(0, "end")
        for name in sorted(self.func_data.keys()):
            self.func_list.insert("end", f"  {name}")

    def _on_func_select(self, _=None):
        sel = self.func_list.curselection()
        if not sel:
            return
        name = self.func_list.get(sel[0]).strip()
        self.func_name_var.set(name)
        self.func_editor.delete("1.0", "end")
        self.func_editor.insert("end", self.func_data.get(name, ""))

    def _new_func(self):
        self.func_list.selection_clear(0, "end")
        self.func_name_var.set("Neue Funktion")
        self.func_editor.delete("1.0", "end")
        self.func_editor.insert("end", "<GP>\n  \n</GP>")

    def _save_func(self):
        name = self.func_name_var.get().strip()
        if not name:
            messagebox.showerror("Fehler", "Bitte einen Titel eingeben.")
            return
        self.func_data[name] = self.func_editor.get("1.0", "end").strip()
        save_json(FUNC_FILE, self.func_data)
        self._log(f"Funktion '{name}' gespeichert.", "info")
        self._refresh_func_list()

    def _del_func(self):
        sel = self.func_list.curselection()
        if not sel:
            return
        name = self.func_list.get(sel[0]).strip()
        if messagebox.askyesno("Löschen", f"Funktion '{name}' wirklich löschen?"):
            del self.func_data[name]
            save_json(FUNC_FILE, self.func_data)
            self._refresh_func_list()
            self.func_editor.delete("1.0", "end")

    def _exec_func(self):
        code = self.func_editor.get("1.0", "end").strip()
        if code:
            self._run_cmd(code, self.func_name_var.get().strip())

    # ══════════════════════════════════════════════════════════════════════════
    #  Tab: Labels / Configs / PrintControls  (gemeinsame Fabrik)
    # ══════════════════════════════════════════════════════════════════════════
    def _build_label_tab(self):
        self._build_file_tab(
            parent=self.tab_label, folder=LABELS_DIR,
            list_attr="label_list", name_attr="label_name_var",
            editor_attr="label_editor", template=LABEL_TEMPLATE,
            default_fn="neues_label.txt", allowed_exts=LABEL_EXTS,
            buttons=[
                ("  Lokal speichern",                  "Green.TButton",  self._label_save_local,
                 "Speichert das Label als Datei im lokalen Ordner."),
                ("  Label speichern (im Drucker)",     "Green.TButton",  self._label_save_to_printer,
                 "Speichert das Label auf der internen Drucker-Disk via SAVELAB.\n"
                 "Syntax: <GP><SAVELAB aName=\"label\\dateiname.txt\"><LAB>...</LAB></SAVELAB></GP>"),
                ("  Label laden (im Drucker-Puffer)",  "Blue.TButton",   self._label_load_to_buffer,
                 "Lädt das Label direkt in den Druckpuffer – sofort druckbereit.\n"
                 "Syntax: <GP><LAB>...</LAB></GP>  (ohne SAVELAB)"),
                ("  Formatieren",                      "Purple.TButton", lambda: self._format_editor(self.label_editor),
                 "Formatiert den XML-Code mit korrektem Einzug."),
            ])

    def _label_save_local(self):
        self._file_save(LABELS_DIR, "label_list", "label_name_var", "label_editor", LABEL_EXTS)

    def _label_save_to_printer(self):
        fn = self.label_name_var.get().strip()
        if not fn:
            messagebox.showwarning("Hinweis", "Kein Dateiname angegeben.")
            return
        if not has_ext(fn, LABEL_EXTS):
            fn += ".txt"
        content = self.label_editor.get("1.0", "end").strip()
        lab_match = re.search(r'(<LAB\b[^>]*>.*?</LAB>)', content, re.DOTALL | re.IGNORECASE)
        lab_block = lab_match.group(1) if lab_match else content
        cmd = f'<GP>\n<SAVELAB aName="label\\{fn}">\n{lab_block}\n</SAVELAB>\n</GP>'
        self._run_cmd(cmd, f"SAVELAB: {fn}")

    def _label_load_to_buffer(self):
        content = self.label_editor.get("1.0", "end").strip()
        if not content:
            messagebox.showwarning("Hinweis", "Editor ist leer.")
            return
        if not re.match(r'\s*<GP\b', content, re.IGNORECASE):
            content = f"<GP>\n{content}\n</GP>"
        self._run_cmd(content, "Label → Druckpuffer")

    def _build_config_tab(self):
        self._build_file_tab(
            parent=self.tab_config, folder=CONFIGS_DIR,
            list_attr="cfg_list", name_attr="cfg_name_var",
            editor_attr="cfg_editor", template=CONFIG_TEMPLATE,
            default_fn="neue_config.pcf", allowed_exts=CONFIG_EXTS,
            buttons=[
                ("  Config lokal speichern",      "Green.TButton",  self._cfg_save_local,
                 "Speichert die Config als Datei im lokalen Ordner."),
                ("  Config laden (in Tool)",      "Blue.TButton",   self._cfg_load_from_printer,
                 "Fragt die aktuelle Config vom Drucker ab und lädt sie in den Editor.\n"
                 "Syntax: <GP><CONFIG/></GP>"),
                ("  Config laden (im Drucker)",   "Green.TButton",  self._cfg_send_to_printer,
                 "Sendet die Config aus dem Editor direkt an den Drucker.\n"
                 "Syntax: <GP><CONFIG>...</CONFIG></GP>"),
                ("  Formatieren",                 "Purple.TButton", lambda: self._format_editor(self.cfg_editor),
                 "Formatiert den XML-Code mit korrektem Einzug."),
            ])

    def _cfg_save_local(self):
        self._file_save(CONFIGS_DIR, "cfg_list", "cfg_name_var", "cfg_editor", CONFIG_EXTS)

    def _cfg_load_from_printer(self):
        self._cmd_to_editor("<GP><CONFIG/></GP>", self.cfg_editor, "CONFIG abfragen")

    def _cfg_send_to_printer(self):
        content = self.cfg_editor.get("1.0", "end").strip()
        if not content:
            messagebox.showwarning("Hinweis", "Editor ist leer.")
            return
        self._run_cmd(content, "CONFIG → Drucker")

    def _build_printctl_tab(self):
        self._build_file_tab(
            parent=self.tab_printctl, folder=PRINTCTL_DIR,
            list_attr="ctl_list", name_attr="ctl_name_var",
            editor_attr="ctl_editor", template=PRINTCONTROL_TEMPLATE,
            default_fn="neue-printcontrol.ctl", allowed_exts=PRINTCTL_EXTS,
            buttons=[
                ("  PrintControl lokal speichern",     "Green.TButton",  self._ctl_save_local,
                 "Speichert das PrintControl als Datei im lokalen Ordner."),
                ("  PrintControl laden (in Tool)",     "Blue.TButton",   self._ctl_load_from_printer,
                 "Fragt das aktuelle PrintControl vom Drucker ab und lädt es in den Editor.\n"
                 "Syntax: <GP><PRINTCONTROL/></GP>"),
                ("  PrintControl laden (im Drucker)",  "Green.TButton",  self._ctl_send_to_printer,
                 "Sendet das PrintControl aus dem Editor direkt an den Drucker.\n"
                 "Syntax: <GP><PRINTCONTROL>...</PRINTCONTROL></GP>"),
                ("  Formatieren",                      "Purple.TButton", lambda: self._format_editor(self.ctl_editor),
                 "Formatiert den XML-Code mit korrektem Einzug."),
            ])

    def _ctl_save_local(self):
        self._file_save(PRINTCTL_DIR, "ctl_list", "ctl_name_var", "ctl_editor", PRINTCTL_EXTS)

    def _ctl_load_from_printer(self):
        self._cmd_to_editor("<GP><PRINTCONTROL/></GP>", self.ctl_editor, "PRINTCONTROL abfragen")

    def _ctl_send_to_printer(self):
        content = self.ctl_editor.get("1.0", "end").strip()
        if not content:
            messagebox.showwarning("Hinweis", "Editor ist leer.")
            return
        self._run_cmd(content, "PRINTCONTROL → Drucker")

    # ══════════════════════════════════════════════════════════════════════════
    #  Gemeinsame Datei-Tab-Fabrik
    # ══════════════════════════════════════════════════════════════════════════
    def _build_file_tab(self, parent, folder, list_attr, name_attr,
                        editor_attr, template, default_fn, allowed_exts, buttons):
        outer = tk.Frame(parent, bg=C["surface"])
        outer.pack(fill="both", expand=True, padx=14, pady=14)
        left  = tk.Frame(outer, bg=C["surface"])
        left.pack(side="left", fill="y", padx=(0, 12))
        right = tk.Frame(outer, bg=C["surface"])
        right.pack(side="left", fill="both", expand=True)

        lf_list = ttk.LabelFrame(left, text="  Gespeicherte Dateien")
        lf_list.pack(fill="both", expand=True)
        lb = tk.Listbox(
            lf_list, bg=C["surface2"], fg=C["text"],
            selectbackground=C["accent"], selectforeground=C["header"],
            font=("Segoe UI", 10), width=26,
            activestyle="none", relief="flat", bd=0, highlightthickness=0)
        lb.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        setattr(self, list_attr, lb)

        def on_select(_=None):
            sel = lb.curselection()
            if not sel:
                return
            fn = lb.get(sel[0]).strip()
            getattr(self, name_attr).set(fn)
            try:
                with open(os.path.join(folder, fn), "r", encoding="utf-8", errors="replace") as fp:
                    content = fp.read()
                ed = getattr(self, editor_attr)
                ed.delete("1.0", "end")
                ed.insert("end", content)
            except Exception as e:
                self._log(f"Fehler beim Lesen: {e}", "error")

        lb.bind("<<ListboxSelect>>", on_select)

        btn_l = tk.Frame(lf_list, bg=C["surface"])
        btn_l.pack(fill="x", padx=8, pady=(0, 4))
        _bneu = ttk.Button(btn_l, text="  + Neu", style="Green.TButton",
                           command=lambda: self._file_new(
                               folder, list_attr, name_attr, editor_attr, default_fn, template))
        _bneu.pack(fill="x", pady=2)
        ToolTip(_bneu, "Erstellt eine neue leere Datei aus der Vorlage.")
        _bimp = ttk.Button(btn_l, text="  Importieren", style="Blue.TButton",
                           command=lambda: self._file_import(folder, list_attr, allowed_exts))
        _bimp.pack(fill="x", pady=2)
        ToolTip(_bimp, "Importiert eine vorhandene Datei vom PC in diesen Ordner.")
        _bref = ttk.Button(btn_l, text="  Aktualisieren", style="Orange.TButton",
                           command=lambda: self._file_refresh(folder, list_attr, allowed_exts))
        _bref.pack(fill="x", pady=2)
        ToolTip(_bref, "Lädt die Dateiliste neu.")
        _bdel = ttk.Button(btn_l, text="  Löschen", style="Red.TButton",
                           command=lambda: self._file_delete(
                               folder, list_attr, editor_attr, name_attr))
        _bdel.pack(fill="x", pady=(2, 8))
        ToolTip(_bdel, "Löscht die ausgewählte Datei dauerhaft.")

        lf_ed = ttk.LabelFrame(right, text="  Editor")
        lf_ed.pack(fill="both", expand=True)
        name_row = tk.Frame(lf_ed, bg=C["surface"])
        name_row.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(name_row, text="Dateiname:", bg=C["surface"], fg=C["subtext"],
                 font=("Segoe UI", 9)).pack(side="left", padx=(0, 8))
        nvar = tk.StringVar()
        setattr(self, name_attr, nvar)
        ttk.Entry(name_row, textvariable=nvar, width=32).pack(side="left", fill="x", expand=True)

        ed = scrolledtext.ScrolledText(
            lf_ed, bg=C["surface2"], fg=C["text"],
            insertbackground=C["text"],
            font=("Consolas", 10), relief="flat", bd=0,
            selectbackground=C["overlay"], padx=8, pady=6)
        ed.pack(fill="both", expand=True, padx=8, pady=4)
        setattr(self, editor_attr, ed)

        btn_r = tk.Frame(lf_ed, bg=C["surface"])
        btn_r.pack(fill="x", padx=8, pady=(0, 8))
        for item in buttons:
            lbl, style, cmd_fn = item[0], item[1], item[2]
            tip = item[3] if len(item) > 3 else None
            _bt = ttk.Button(btn_r, text=lbl, style=style, command=cmd_fn)
            _bt.pack(side="left", padx=(0, 5))
            if tip:
                ToolTip(_bt, tip)

        self._file_refresh(folder, list_attr, allowed_exts)

    def _file_refresh(self, folder, list_attr, allowed_exts=ALL_EXTS):
        lb = getattr(self, list_attr)
        lb.delete(0, "end")
        try:
            files = sorted(f for f in os.listdir(folder) if has_ext(f, allowed_exts))
            for fn in files:
                lb.insert("end", f"  {fn}")
        except Exception:
            pass

    def _file_new(self, folder, list_attr, name_attr, editor_attr, default_fn, template):
        getattr(self, list_attr).selection_clear(0, "end")
        getattr(self, name_attr).set(default_fn)
        ed = getattr(self, editor_attr)
        ed.delete("1.0", "end")
        ed.insert("end", template)

    def _file_import(self, folder, list_attr, allowed_exts=ALL_EXTS):
        ext_str = " ".join(f"*{e}" for e in allowed_exts)
        path = filedialog.askopenfilename(
            title="Datei importieren",
            filetypes=[
                ("Unterstützte Dateien", f"{ext_str} {ext_str.upper()}"),
                ("Alle Dateien", "*.*")])
        if not path:
            return
        fn = os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fp:
                content = fp.read()
            dest = os.path.join(folder, fn)
            with open(dest, "w", encoding="utf-8") as fp:
                fp.write(content)
            self._file_refresh(folder, list_attr, allowed_exts)
            self._log(f"Importiert: {fn}  →  {folder}", "info")
        except Exception as e:
            self._log(f"Import-Fehler: {e}", "error")
            messagebox.showerror("Import-Fehler", sanitize_error(e))

    def _file_save(self, folder, list_attr, name_attr, editor_attr, allowed_exts=ALL_EXTS):
        fn = getattr(self, name_attr).get().strip()
        if not fn:
            messagebox.showerror("Fehler", "Bitte einen Dateinamen eingeben.")
            return
        if not has_ext(fn, allowed_exts):
            fn += ".pcf" if folder == CONFIGS_DIR else ".txt"
        code = getattr(self, editor_attr).get("1.0", "end")
        path = os.path.join(folder, fn)
        with open(path, "w", encoding="utf-8") as fp:
            fp.write(code)
        self._log(f"Lokal gespeichert: {path}", "info")
        self._file_refresh(folder, list_attr, allowed_exts)

    def _file_delete(self, folder, list_attr, editor_attr, name_attr):
        lb  = getattr(self, list_attr)
        sel = lb.curselection()
        if not sel:
            return
        fn = lb.get(sel[0]).strip()
        if messagebox.askyesno("Löschen", f"'{fn}' wirklich löschen?"):
            os.remove(os.path.join(folder, fn))
            self._file_refresh(folder, list_attr)
            getattr(self, editor_attr).delete("1.0", "end")

    # ══════════════════════════════════════════════════════════════════════════
    #  Hilfsmethoden
    # ══════════════════════════════════════════════════════════════════════════
    def _format_editor(self, editor):
        raw = editor.get("1.0", "end").strip()
        if not raw:
            messagebox.showinfo("Formatieren", "Der Editor ist leer.")
            return
        try:
            result = pretty_xml(raw)
            editor.delete("1.0", "end")
            editor.insert("end", result)
        except Exception as e:
            messagebox.showerror(
                "XML-Syntaxfehler",
                f"Das XML konnte nicht formatiert werden:\n\n{e}\n\n"
                f"Bitte auf fehlende oder falsch geschlossene Tags prüfen.")

    def _cmd_to_editor(self, cmd, editor, label="Abfrage"):
        """Sendet einen GP-Befehl und lädt die Antwort in den Editor."""
        ip, port = self._get_conn()
        self._log(f"→  {label}: {cmd[:90]}{'…' if len(cmd) > 90 else ''}", "send")
        self._history_add(label, cmd)
        self._session_log_write(f"→ SEND  [{label}]", cmd)
        def worker():
            try:
                result = send_gprint(ip, port, cmd,
                                     timeout=int(self.config_data.get("timeout", 5)))
                gp_blocks = re.findall(r'<GP>.*?</GP>', result, re.DOTALL | re.IGNORECASE)
                cleaned = gp_blocks[-1] if gp_blocks else result
                def _ok(r=result, c=cleaned):
                    self._log("← Antwort:\n" + r, "recv")
                    editor.delete("1.0", "end")
                    editor.insert("end", c)
                    self.status_dot.config(fg=C["green"])
                    self.status_lbl.config(text="Verbunden", fg=C["green"])
                    self._session_log_write("← RECV", r)
                self.after(0, _ok)
            except Exception as e:
                err = str(e)
                def _err(msg=err):
                    self._log(f"Fehler: {msg}", "error")
                    self.status_dot.config(fg=C["red"])
                    self.status_lbl.config(text="Verbindungsfehler", fg=C["red"])
                    self._session_log_write("✗ ERROR", msg)
                self.after(0, _err)
        threading.Thread(target=worker, daemon=True).start()

    def _switch_to_tab(self, tab_text):
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Notebook):
                for i, tab_id in enumerate(widget.tabs()):
                    if tab_text.lower() in widget.tab(tab_id, "text").lower():
                        widget.select(i)
                        return

    def _get_conn(self):
        return (self.config_data.get("ip", ""),
                int(self.config_data.get("port", 3000)))

    # ── Session-Log ───────────────────────────────────────────────────────────
    def _init_session_log(self):
        self._session_log_path = os.path.join(
            LOGS_DIR, f"session_{time.strftime('%Y-%m-%d_%H-%M-%S')}.log")
        with open(self._session_log_path, "w", encoding="utf-8") as f:
            f.write(f"# G-PRINT Session Log — {time.strftime('%d.%m.%Y %H:%M:%S')}\n")
            f.write(f"# IP: {self.config_data.get('ip','?')}:{self.config_data.get('port','?')}\n\n")

    def _session_log_write(self, direction, text):
        try:
            with open(self._session_log_path, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] {direction}\n{text}\n{'─'*40}\n")
        except Exception:
            pass

    # ── Updater ───────────────────────────────────────────────────────────────
    def _update_check(self, manual=True):
        url = self.config_data.get("update_url", "").strip()
        if not url:
            if manual:
                self.after(0, lambda: messagebox.showinfo(
                    "Update", "Keine Update-URL konfiguriert.\n"
                              "Bitte unter Netzwerk → Update-URL eintragen."))
            return
        try:
            with urllib.request.urlopen(url, timeout=8) as r:
                data = json.loads(r.read().decode("utf-8"))
            remote_ver      = data.get("version", "0.0.0")
            dl_url          = data.get("download_url", "")
            notes           = data.get("notes", "")
            expected_sha256 = data.get("sha256", "")
            if self._ver_newer(remote_ver, APP_VERSION):
                self.after(0, lambda: self._update_prompt(
                    remote_ver, dl_url, notes, expected_sha256))
            elif manual:
                self.after(0, lambda: messagebox.showinfo(
                    "Kein Update", f"Du hast die aktuelle Version ({APP_VERSION})."))
        except Exception as e:
            if manual:
                err = str(e)
                self.after(0, lambda: messagebox.showerror(
                    "Update-Fehler", f"Update-Prüfung fehlgeschlagen:\n{err}"))

    @staticmethod
    def _ver_newer(remote, current):
        def parts(v):
            try:
                return [int(x) for x in v.strip().lstrip("v").split(".")]
            except Exception:
                return [0]
        return parts(remote) > parts(current)

    @staticmethod
    def _verify_sha256(file_path: str, expected: str) -> bool:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest().lower() == expected.lower().strip()

    def _update_prompt(self, new_ver, dl_url, notes, sha256=""):
        msg = f"Neue Version verfügbar: {new_ver}\n(Aktuell: {APP_VERSION})"
        if notes:
            msg += f"\n\nÄnderungen:\n{notes}"
        msg += "\n\nJetzt aktualisieren?"
        if not messagebox.askyesno("Update verfügbar", msg):
            return
        if not dl_url:
            messagebox.showerror("Fehler", "Keine Download-URL angegeben.")
            return
        if not dl_url.startswith("https://"):
            messagebox.showerror("Fehler",
                "Download-URL ist nicht sicher (https:// fehlt).\nUpdate abgebrochen.")
            return
        prog_win = tk.Toplevel(self)
        prog_win.title("Download…")
        prog_win.resizable(False, False)
        prog_win.configure(bg=C["surface"])
        prog_win.transient(self)
        prog_win.geometry(
            f"+{self.winfo_rootx()+self.winfo_width()//2-180}"
            f"+{self.winfo_rooty()+self.winfo_height()//2-60}")
        tk.Label(prog_win, text=f"  Lade Version {new_ver} herunter…",
                 bg=C["surface"], fg=C["text"],
                 font=("Segoe UI", 10)).pack(padx=20, pady=(16, 4))
        prog_bar = ttk.Progressbar(prog_win, length=320, mode="indeterminate")
        prog_bar.pack(padx=20, pady=(0, 16))
        prog_bar.start(12)

        def do_download():
            try:
                tmp = os.path.join(tempfile.gettempdir(), "GPrint-Tool_new.exe")
                security_log("UPDATE_DOWNLOAD", dl_url, "start")
                urllib.request.urlretrieve(dl_url, tmp)
                if sha256:
                    if not self._verify_sha256(tmp, sha256):
                        try:
                            os.remove(tmp)
                        except Exception:
                            pass
                        security_log("UPDATE_DOWNLOAD", dl_url, "hash_error")
                        self.after(0, lambda: prog_win.destroy())
                        self.after(0, lambda: messagebox.showerror(
                            "Sicherheitsfehler",
                            "SHA-256-Prüfsumme stimmt nicht überein.\n"
                            "Update-Datei könnte manipuliert sein.\n"
                            "Update abgebrochen."))
                        return
                security_log("UPDATE_DOWNLOAD", dl_url, "ok")
                self.after(0, lambda: prog_win.destroy())
                self.after(0, lambda: self._apply_update(tmp))
            except Exception as e:
                err = sanitize_error(e)
                security_log("UPDATE_DOWNLOAD", dl_url, "error")
                self.after(0, lambda: prog_win.destroy())
                self.after(0, lambda: messagebox.showerror(
                    "Download-Fehler", f"Download fehlgeschlagen:\n{err}"))

        threading.Thread(target=do_download, daemon=True).start()

    @staticmethod
    def _clean_env():
        # PyInstaller-Bootloader-Variablen raus: verhindern dass die neue .exe
        # sich für einen Kindprozess hält ("Failed to load Python DLL").
        return {k: v for k, v in os.environ.items()
                if not (k.startswith("_MEI") or k.startswith("_PYI"))}

    def _apply_update(self, new_exe_path):
        if not getattr(sys, "frozen", False):
            messagebox.showinfo(
                "Update (Entwickler-Modus)",
                f"Im Python-Entwicklermodus kein automatisches Ersetzen.\n"
                f"Neue Exe liegt unter:\n{new_exe_path}\n\n"
                f"Manuell kopieren nach: {os.path.abspath(sys.argv[0])}")
            return
        current_exe = sys.executable
        pid         = os.getpid()
        bat_path    = os.path.join(tempfile.gettempdir(), f"_gpupdate_{pid}.bat")
        bat_content = (
            "@echo off\n"
            "timeout /t 2 /nobreak >nul\n"
            f'copy /y "{new_exe_path}" "{current_exe}"\n'
            f'start "" "{current_exe}"\n'
            'del "%~f0"\n'
        )
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
        subprocess.Popen(
            ["cmd", "/c", bat_path],
            env=self._clean_env(),
            cwd=tempfile.gettempdir(),
            creationflags=subprocess.CREATE_NO_WINDOW)
        self._on_close()

    # ── Drucker-Ping (läuft nur wenn _ping_active == True) ───────────────────
    def _start_printer_ping(self):
        """Startet den Ping-Loop (idempotent – sicheres Mehrfach-Aufrufen)."""
        if self._printer_ping_id:
            self.after_cancel(self._printer_ping_id)
            self._printer_ping_id = None
        self._ping_active = True
        self._disconnect_btn.config(state="normal")
        self._printer_ping_id = self.after(10000, self._printer_ping_loop)

    def _printer_ping_loop(self):
        """Ping-Hintergrundschleife – alle 10 s, nur wenn _ping_active."""
        if not self._ping_active:
            return
        ip, port = self._get_conn()
        def ping():
            if not self._ping_active:
                return
            try:
                send_gprint(ip, port, "<GP><MAINSTATE/></GP>", timeout=2)
                def _ok():
                    self.status_dot.config(fg=C["green"])
                    self.status_lbl.config(text="Verbunden", fg=C["green"])
                self.after(0, _ok)
            except Exception:
                def _fail():
                    self.status_dot.config(fg=C["red"])
                    self.status_lbl.config(text="Offline", fg=C["red"])
                self.after(0, _fail)
        threading.Thread(target=ping, daemon=True).start()
        self._printer_ping_id = self.after(10000, self._printer_ping_loop)

    def _disconnect(self):
        """Stoppt den Ping-Loop und setzt Verbindungsstatus zurück."""
        self._ping_active = False
        if self._printer_ping_id:
            self.after_cancel(self._printer_ping_id)
            self._printer_ping_id = None
        self.status_dot.config(fg=C["red"])
        self.status_lbl.config(text="Nicht verbunden", fg=C["subtext"])
        self.conn_result.config(text="  Getrennt", fg=C["subtext"])
        self._disconnect_btn.config(state="disabled")

    # ── Fenster-Drag & Window-Controls ───────────────────────────────────────
    def _drag_start(self, event):
        """Mausposition relativ zur Fensterecke merken."""
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()

    def _drag_move(self, event):
        """Fenster an neue Position verschieben."""
        self.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    def _minimize_window(self):
        """Minimiert das borderless-Fenster sauber in die Taskleiste."""
        self.overrideredirect(False)          # Native Frame kurz zurück (für iconify)
        self.iconify()                        # → in Taskleiste schieben
        self.bind("<Map>", self._on_window_restore)   # Callback wenn wiederhergestellt

    def _on_window_restore(self, event):
        """Stellt overrideredirect nach Taskleisten-Restore wieder her."""
        if self.state() == "normal":
            self.overrideredirect(True)
            self.unbind("<Map>")
            self.lift()
            self.focus_force()

    def _on_close(self):
        if getattr(self, "_closing", False):
            return
        self._closing = True
        self._ping_active = False
        if self._printer_ping_id:
            self.after_cancel(self._printer_ping_id)
        # KEIN manuelles Aufräumen von sys._MEIPASS mehr! Der PyInstaller-
        # Bootloader (Elternprozess) löscht seinen Temp-Ordner beim Beenden
        # selbst. Ein eigener Rename-/rmdir-Trick rennt gegen diese Routine
        # und löst genau die "Failed to remove temporary directory"-Warnung aus.
        self.destroy()

    # ── Befehlshistorie ───────────────────────────────────────────────────────
    def _history_add(self, label, cmd):
        self._cmd_history = [(label, cmd)] + [
            x for x in self._cmd_history if x[1] != cmd][:19]
        self._history_refresh()

    def _history_refresh(self):
        if not hasattr(self, "_hist_lb"):
            return
        self._hist_lb.delete(0, "end")
        for lbl, _ in self._cmd_history:
            self._hist_lb.insert("end", lbl)

    def _history_resend(self, _=None):
        sel = self._hist_lb.curselection()
        if not sel:
            return
        lbl, cmd = self._cmd_history[sel[0]]
        self._run_cmd(cmd, f"[Hist] {lbl}")

    # ── Drucker-Profile ───────────────────────────────────────────────────────
    def _profile_save(self):
        name = simpledialog.askstring("Profil speichern", "Profilname:",
                                       initialvalue=self.config_data.get("name", "Drucker"),
                                       parent=self)
        if not name:
            return
        self.profiles[name] = {
            "ip":   self.config_data.get("ip", ""),
            "port": self.config_data.get("port", 3000),
            "name": name,
        }
        save_json(PROFILES_FILE, self.profiles)
        self._profile_refresh()
        self._log(f"Profil gespeichert: {name}", "info")

    def _profile_load(self, _=None):
        if not hasattr(self, "_prof_lb"):
            return
        sel = self._prof_lb.curselection()
        if not sel:
            return
        name = self._prof_lb.get(sel[0]).split("  (")[0]
        p = self.profiles.get(name, {})
        if p:
            self.config_data["ip"]   = p.get("ip", self.config_data["ip"])
            self.config_data["port"] = p.get("port", self.config_data["port"])
            self._hdr_ip.config(text=self.config_data["ip"])
            self._refresh_net_fields()
            self._log(f"Profil geladen: {name}  ({p['ip']}:{p['port']})", "info")

    def _profile_delete(self):
        if not hasattr(self, "_prof_lb"):
            return
        sel = self._prof_lb.curselection()
        if not sel:
            return
        name = self._prof_lb.get(sel[0]).split("  (")[0]
        if messagebox.askyesno("Löschen", f"Profil '{name}' wirklich löschen?"):
            del self.profiles[name]
            save_json(PROFILES_FILE, self.profiles)
            self._profile_refresh()

    def _save_update_settings(self):
        self.config_data["update_url"]  = self._upd_url_var.get().strip()
        self.config_data["auto_update"] = self._auto_upd_var.get()
        save_json(CONFIG_FILE, self.config_data)
        self._log("Update-Einstellungen gespeichert.", "info")

    def _profile_refresh(self):
        if not hasattr(self, "_prof_lb"):
            return
        self._prof_lb.delete(0, "end")
        for name in self.profiles:
            p = self.profiles[name]
            self._prof_lb.insert("end", f"{name}  ({p.get('ip','')})")

    def _refresh_net_fields(self):
        try:
            for key, var in self._net_vars.items():
                if key in self.config_data:
                    var.set(str(self.config_data[key]))
        except Exception:
            pass

    # ── Keybindings ───────────────────────────────────────────────────────────
    def _apply_keybindings(self):
        self.bind("<F5>",         lambda e: self._connection_check())
        self.bind("<Control-s>",  lambda e: self._quick_save())
        self.bind("<Control-r>",  lambda e: self._run_cmd("<GP><MAINSTATE/></GP>", "Hauptstatus"))
        self.bind("<Control-F5>", lambda e: self._run_cmd("<GP><START/></GP>", "Drucken START"))

    def _quick_save(self):
        try:
            nb = [w for w in self.winfo_children() if isinstance(w, ttk.Notebook)][0]
            tab_text = nb.tab(nb.select(), "text").lower()
            if "label editor" in tab_text:
                self._label_editor_ref._save_label()
            elif "label" in tab_text:
                self._label_save_local()
            elif "config" in tab_text:
                self._cfg_save_local()
            elif "print" in tab_text:
                self._ctl_save_local()
        except Exception:
            pass

    # ── Uhr ───────────────────────────────────────────────────────────────────
    def _start_clock(self):
        def tick():
            self._clock_lbl.config(text=time.strftime("%H:%M:%S"))
            self._date_lbl.config(text=time.strftime("%d.%m.%Y"))
            self.after(1000, tick)
        tick()

    # ── About ─────────────────────────────────────────────────────────────────
    def _show_about(self):
        dlg = tk.Toplevel(self)
        dlg.title("Über")
        dlg.resizable(False, False)
        dlg.configure(bg=C["surface"])
        dlg.transient(self)
        dlg.grab_set()
        dlg.geometry(
            f"+{self.winfo_rootx() + self.winfo_width()//2 - 220}"
            f"+{self.winfo_rooty() + self.winfo_height()//2 - 160}")

        tk.Frame(dlg, bg=C["accent"], height=3).pack(fill="x")
        tk.Label(dlg, text="\n  AJ Interface Tool",
                 bg=C["surface"], fg=C["accent"],
                 font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(dlg, text=f"  Version {APP_VERSION}  ·  alphaJET / K&B",
                 bg=C["surface"], fg=C["subtext"],
                 font=("Segoe UI", 9)).pack(anchor="w")
        tk.Frame(dlg, bg=C["border"], height=1).pack(fill="x", pady=10, padx=14)

        infos = [
            ("Protokoll",   "G-PRINT XML / TCP"),
            ("Geräte",      "alphaJET AJD  ·  AJ5II"),
            ("Tastenkürzel","F5 = Verbindungstest"),
            ("",            "Strg+R = Hauptstatus"),
            ("",            "Strg+S = Speichern"),
            ("",            "Strg+F5 = Drucken START"),
            ("Support",     "Marvin Köllner"),
            ("E-Mail",      "marvin_koellner@outlook.de"),
        ]
        for k, v in infos:
            row = tk.Frame(dlg, bg=C["surface"])
            row.pack(fill="x", padx=14, pady=1)
            tk.Label(row, text=f"{k:<14}", bg=C["surface"], fg=C["subtext"],
                     font=("Consolas", 9)).pack(side="left")
            tk.Label(row, text=v, bg=C["surface"], fg=C["text"],
                     font=("Consolas", 9)).pack(side="left")

        tk.Frame(dlg, bg=C["border"], height=1).pack(fill="x", pady=10, padx=14)
        ttk.Button(dlg, text="  Schließen", command=dlg.destroy).pack(pady=(0, 14))

    # ── Theme-Toggle ──────────────────────────────────────────────────────────
    def _toggle_theme(self):
        new_theme = "light" if ACTIVE_THEME == "dark" else "dark"

        # Prüfen ob forest-light vorhanden (gebündelt oder heruntergeladen), ggf. herunterladen
        if new_theme == "light":
            bundled = os.path.join(THEMES_DIR, "forest-light.tcl")
            local   = os.path.join(BASE_DIR, "res", "themes", "forest-light.tcl")
        # Prüfen ob forest-dark vorhanden (gebündelt oder heruntergeladen), ggf. herunterladen
        if new_theme == "dark":
            bundled = os.path.join(THEMES_DIR, "forest-dark.tcl")
            local   = os.path.join(BASE_DIR, "res", "themes", "forest-dark.tcl")     
        self._save_and_restart(new_theme)

    def _save_and_restart(self, new_theme: str):
        cfg = load_json(CONFIG_FILE, {})
        cfg["ui_theme"] = new_theme
        save_json(CONFIG_FILE, cfg)
        if getattr(sys, "frozen", False):
            exe = sys.executable
            pid = os.getpid()
            # Pro-PID-Dateiname → kein Konflikt bei schnell aufeinander folgenden
            # Wechseln. In %TEMP% statt neben der EXE (Program Files ggf. read-only).
            # In %TEMP% statt neben der EXE (Program Files ggf. read-only).
            bat_path = os.path.join(tempfile.gettempdir(), f"_gprestart_{pid}.bat")
            bat_content = (
                "@echo off\n"
                ":wait\n"
                f"tasklist /fi \"PID eq {pid}\" 2>nul | find \"{pid}\" >nul\n"
                "if not errorlevel 1 (\n"
                "    timeout /t 1 /nobreak >nul\n"
                "    goto wait\n"
                ")\n"
                f"start \"\" \"{exe}\"\n"
                "del \"%~f0\"\n"
            )
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(bat_content)
            # Bereinigtes Env + cwd in %TEMP%: der cmd-Prozess lebt während des
            # Beendens weiter (Warte-Loop); läge sein cwd in _MEIPASS, würde das
            # den Ordner sperren und den Bootloader-Cleanup blockieren.
            subprocess.Popen(
                ["cmd", "/c", bat_path],
                env=self._clean_env(),
                cwd=tempfile.gettempdir(),
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            # Sauber beenden – der Bootloader räumt seinen _MEIPASS selbst auf.
            self._on_close()
        else:
            os.execv(sys.executable, [sys.executable] + sys.argv)

    # ── Log ───────────────────────────────────────────────────────────────────
    def _log(self, text, tag="info"):
        ts = time.strftime("%H:%M:%S")
        self.log.insert("end", f"[{ts}]  {text}\n", tag)
        self.log.see("end")

    def _toggle_log(self):
        if self._log_visible:
            self.log.pack_forget()
            self._log_toggle.config(text="▶")
        else:
            self.log.pack(fill="x", padx=10, pady=(0, 8))
            self._log_toggle.config(text="▼")
        self._log_visible = not self._log_visible

    def _set_log_height(self, h):
        self.log.config(height=int(h))
        if not self._log_visible:
            self.log.pack(fill="x", padx=10, pady=(0, 8))
            self._log_toggle.config(text="▼")
            self._log_visible = True

    # ── Verbindung ────────────────────────────────────────────────────────────
    def _connection_check(self):
        ip, port = self._get_conn()
        self._log(f"Verbindungstest  {ip}:{port} …", "info")
        def check():
            try:
                result = send_gprint(ip, port, "<GP><MAINSTATE/></GP>",
                                     timeout=int(self.config_data.get("timeout", 5)))
                self.after(0, lambda: self._conn_ok(result))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._conn_fail(err))
        threading.Thread(target=check, daemon=True).start()

    def _conn_ok(self, result):
        self.status_dot.config(fg=C["green"])
        self.status_lbl.config(text="Verbunden", fg=C["green"])
        self.conn_result.config(text="  Verbindung erfolgreich – Ping läuft alle 10 s", fg=C["green"])
        self._log("Antwort:\n" + result, "recv")
        self._start_printer_ping()   # Ping-Loop starten (idempotent)

    def _conn_fail(self, err):
        self.status_dot.config(fg=C["red"])
        self.status_lbl.config(text="Verbindungsfehler", fg=C["red"])
        self.conn_result.config(text=f"  Fehler: {err}", fg=C["red"])
        self._log(f"Verbindungsfehler: {err}", "error")

    def _run_cmd(self, cmd, label="Befehl"):
        if not cmd:
            return
        if not validate_gprint_xml(cmd):
            messagebox.showerror("Ungültiger Befehl",
                "Der Befehl muss ein gültiger G-PRINT XML-Block sein.\n\n"
                "Erwartetes Format:\n<GP>\n  …\n</GP>")
            return
        ip, port = self._get_conn()
        self._log(f"→  {label}:  {cmd[:90]}{'…' if len(cmd) > 90 else ''}", "send")
        self._history_add(label, cmd)
        self._session_log_write(f"→ SEND  [{label}]", cmd)
        def worker():
            try:
                result = send_gprint(ip, port, cmd,
                                     timeout=int(self.config_data.get("timeout", 5)))
                def _ok(r=result):
                    self._on_recv(r)
                    self.status_dot.config(fg=C["green"])
                    self.status_lbl.config(text="Verbunden", fg=C["green"])
                    self._session_log_write("← RECV", r)
                self.after(0, _ok)
            except Exception as e:
                err = str(e)
                def _err(msg=err):
                    self._log(f"Fehler: {msg}", "error")
                    self.status_dot.config(fg=C["red"])
                    self.status_lbl.config(text="Verbindungsfehler", fg=C["red"])
                    self._session_log_write("✗ ERROR", msg)
                self.after(0, _err)
        threading.Thread(target=worker, daemon=True).start()

    def _on_recv(self, result):
        self._log("← Antwort:\n" + result, "recv")


if __name__ == "__main__":
    app = App()
    app.mainloop()