import os
import sys
import re as _re
import tkinter as tk
import subprocess
import xml.dom.minidom
import json
import datetime as _datetime
import threading as _threading

# ─── Pfade (funktioniert als .py und als .exe) ────────────────────────────────
if getattr(sys, "frozen", False):
    # --onedir: sys.executable = die .exe; sys._MEIPASS = _internal/ (PyInstaller >=5.8)
    BASE_DIR    = os.path.dirname(sys.executable)
    _BUNDLE_DIR = getattr(sys, "_MEIPASS", BASE_DIR)
else:
    BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
    _BUNDLE_DIR = BASE_DIR

# Persistente Pfade (neben der .exe / im Projektordner) ───────────────────────
RES_DIR       = os.path.join(BASE_DIR, "res")
CONFIG_FILE   = os.path.join(RES_DIR, "config.json")
FUNC_FILE     = os.path.join(RES_DIR, "functions.json")
LABELS_DIR    = os.path.join(RES_DIR, "labels")
CONFIGS_DIR   = os.path.join(RES_DIR, "configs")
PRINTCTL_DIR  = os.path.join(RES_DIR, "printcontrol")
LOGOS_DIR     = os.path.join(RES_DIR, "logos")
LOGS_DIR      = os.path.join(RES_DIR, "logs")
PROFILES_FILE = os.path.join(RES_DIR, "profiles.json")
MOCK_FTP_DIR  = os.path.join(RES_DIR, "mock_ftp")

# Read-only gebündelte Assets (sys._MEIPASS / _internal) ─────────────────────
# Themes + Fonts aus _BUNDLE_DIR – liegen in sys._MEIPASS (_internal/),
# nicht zwingend neben der .exe.
THEMES_DIR    = os.path.join(_BUNDLE_DIR, "res", "themes")
FONTS_DIR     = os.path.join(_BUNDLE_DIR, "fonts")

for _d in (LABELS_DIR, CONFIGS_DIR, PRINTCTL_DIR, LOGOS_DIR, LOGS_DIR):
    os.makedirs(_d, exist_ok=True)

# ─── FTP-Zugangsdaten je Gerätetyp ───────────────────────────────────────────
# Herstellerseitige Standardzugangsdaten – sollten am Gerät geändert werden.
# Überschreibbar über res/ftp_credentials.json (gleiche Schlüsselstruktur).
_DEVICE_FTP_DEFAULTS = {
    "AJD":  {"user": "User", "pass": "user$ftp",  "port": 21,   "host": ""},
    "AJ5":  {"user": "User", "pass": "c0d1n9b",   "port": 21,   "host": ""},
    "Mock": {"user": "test", "pass": "test",       "port": 2121, "host": "127.0.0.1"},
}

def _load_device_ftp():
    _creds_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)) if not getattr(__import__('sys'), 'frozen', False)
        else os.path.dirname(__import__('sys').executable),
        "res", "ftp_credentials.json")
    overrides = {}
    if os.path.exists(_creds_file):
        try:
            with open(_creds_file, "r", encoding="utf-8") as _f:
                overrides = json.load(_f)
        except Exception:
            pass
    merged = {k: v.copy() for k, v in _DEVICE_FTP_DEFAULTS.items()}
    for dev, cred in overrides.items():
        if dev in merged:
            merged[dev].update(cred)
        else:
            merged[dev] = cred
    return merged

DEVICE_FTP = _load_device_ftp()

# ─── Erlaubte Dateiendungen ───────────────────────────────────────────────────
LABEL_EXTS    = (".txt", ".TXT", ".Txt", ".xml", ".gp", ".GP")
CONFIG_EXTS   = (".txt", ".TXT", ".Txt", ".xml", ".gp", ".pcf", ".PCF", ".Pcf")
PRINTCTL_EXTS = (".ctl", ".CTL", ".elt", ".ELT", ".gp", ".GP")
ALL_EXTS      = (".txt", ".xml", ".gp", ".pcf", ".ctl", ".elt")

def has_ext(filename, exts):
    return filename.lower().endswith(tuple(e.lower() for e in exts))

# ─── Security: Eingabe-Validierung ───────────────────────────────────────────
_IP_RE = _re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')

def validate_ip(ip: str) -> bool:
    """Prüft ob ip eine gültige IPv4-Adresse ist."""
    s = ip.strip()
    if not _IP_RE.match(s):
        return False
    try:
        return all(0 <= int(p) <= 255 for p in s.split('.'))
    except ValueError:
        return False

def validate_port(port) -> bool:
    """Prüft ob port im gültigen Bereich 1–65535 liegt."""
    try:
        return 1 <= int(port) <= 65535
    except (ValueError, TypeError):
        return False

def validate_gprint_xml(cmd: str) -> bool:
    """Prüft ob cmd eine minimale G-PRINT-XML-Struktur hat (<GP>…</GP>)."""
    s = cmd.strip()
    return bool(s) and s.startswith('<GP') and '</GP>' in s

def validate_local_path(dest: str, base_dir: str) -> bool:
    """Path-Traversal-Schutz: stellt sicher dass dest innerhalb von base_dir liegt."""
    try:
        real_dest = os.path.realpath(dest)
        real_base = os.path.realpath(base_dir)
        return real_dest == real_base or real_dest.startswith(real_base + os.sep)
    except Exception:
        return False

# ─── Security Audit Log ───────────────────────────────────────────────────────
_sec_log_lock = _threading.Lock()

def security_log(event: str, detail: str, result: str = "ok") -> None:
    """Schreibt sicherheitsrelevante Ereignisse als JSON-Zeilen in security_audit.jsonl."""
    entry = json.dumps({
        "ts":     _datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event":  event,
        "detail": detail,
        "result": result,
    }, ensure_ascii=False)
    try:
        with _sec_log_lock:
            with open(os.path.join(LOGS_DIR, "security_audit.jsonl"), "a", encoding="utf-8") as _f:
                _f.write(entry + "\n")
    except Exception:
        pass

def sanitize_error(e: Exception) -> str:
    """Gibt Fehlermeldung zurück, absolute Dateipfade auf Dateinamen reduziert."""
    msg = str(e)
    msg = _re.sub(r'[A-Za-z]:\\(?:[^\'"]+)', lambda m: os.path.basename(m.group()), msg)
    msg = _re.sub(r'(?<!\w)/(?:[^\'" ]+/)+([^\'" ]+)', r'\1', msg)
    return msg

# ─── Farben: Dark (forest-dark) ───────────────────────────────────────────────
C_DARK = {
    "bg":         "#272727",   # Hintergrundfläche hinter allem
    "surface":    "#313131",   # Haupt-Panel (= forest-dark native bg)
    "surface2":   "#3c3c3c",   # Karten, Listenzeilen, Eingabefelder
    "border":     "#4a4a4a",
    "overlay":    "#555555",
    "text":       "#eeeeee",   # forest-dark fg
    "subtext":    "#a0a0a0",
    "accent":     "#3ecf6f",   # forest-kompatibles Grün (hell auf Dunkel)
    "green":      "#3ecf6f",
    "red":        "#e06060",
    "orange":     "#e09848",
    "yellow":     "#d4b840",
    "purple":     "#b090e0",
    "header":     "#252525",   # Kopf-/Fußleiste
    "row_stripe": "#4a4a4a",   # Tabellenzeile alternierend (= border)
}

# ─── Farben: Light (forest-light) ─────────────────────────────────────────────
C_LIGHT = {
    "bg":         "#e0e0e0",   # Hintergrundfläche – deutlich vom Surface abgesetzt
    "surface":    "#f5f5f5",   # Haupt-Panel – fast weiß, leicht warm
    "surface2":   "#eaeaea",   # Karten, Eingabefelder – klar unterscheidbar
    "border":     "#8a8a8a",   # Rahmen gut sichtbar
    "overlay":    "#c8c8c8",
    "text":       "#141414",   # sehr dunkler Text
    "subtext":    "#444444",   # dunkles Grau – lesbar auf hellem Grund
    "accent":     "#1a6b3c",   # forest-Grün, tiefer für Kontrast auf Weiß
    "green":      "#1a6b3c",
    "red":        "#b02828",
    "orange":     "#b86018",
    "yellow":     "#8a6808",
    "purple":     "#5e2882",
    "header":     "#d4d4d4",   # spürbar dunkler als surface – Header klar abgegrenzt
    "row_stripe": "#d4d4d4",   # Tabellenzeile alternierend – sichtbar aber nicht zu dunkel
}

# ─── Aktives Theme aus Config lesen ───────────────────────────────────────────
# CONFIG_FILE ist bereits oben berechnet – kein doppeltes BASE_DIR nötig
_raw_ui_cfg: dict = {}
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as _f:
            _raw_ui_cfg = json.load(_f)
    except Exception:
        pass

ACTIVE_THEME: str = _raw_ui_cfg.get("ui_theme", "dark")   # "dark" | "light"
C: dict = (C_DARK if ACTIVE_THEME == "dark" else C_LIGHT).copy()

class ToolTip:
    """Einfacher Hover-Tooltip für beliebige tk/ttk-Widgets."""
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text   = text
        self.delay  = delay
        self._id    = None
        self._win   = None
        widget.bind("<Enter>",  self._schedule, add="+")
        widget.bind("<Leave>",  self._cancel,   add="+")
        widget.bind("<Button>", self._cancel,   add="+")

    def _schedule(self, _=None):
        self._cancel()
        self._id = self.widget.after(self.delay, self._show)

    def _cancel(self, _=None):
        if self._id:
            self.widget.after_cancel(self._id)
            self._id = None
        if self._win:
            self._win.destroy()
            self._win = None

    def _show(self):
        if self._win:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._win = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        tk.Label(tw, text=self.text,
                 bg=C["surface2"], fg=C["text"],
                 relief="solid", borderwidth=1,
                 font=("Segoe UI", 8),
                 wraplength=320, justify="left",
                 padx=8, pady=5).pack()

def apply_theme(root):
    """
    Lädt das aktive forest-Theme (dark/light) und konfiguriert alle TTK-Stile.
    Muss einmalig auf dem Root-Fenster (tk.Tk) aufgerufen werden –
    TTK-Stile gelten danach global für die gesamte Anwendung.

    Verwendung in jedem Modul das ein eigenes Toplevel braucht:
        from utils import apply_theme
        win = tk.Toplevel()
        apply_theme(win)   # optional – Stile sind nach dem ersten Aufruf global
    """
    import tkinter.ttk as ttk

    theme_name = f"forest-{ACTIVE_THEME}"
    tcl_path   = os.path.join(THEMES_DIR, f"{theme_name}.tcl")
    st = ttk.Style(root)

    # ── Forest-Theme laden ────────────────────────────────────────────────────
    # In --onefile: THEMES_DIR zeigt auf sys._MEIPASS (gebündelt).
    # Fallback: BASE_DIR/res/themes/ für manuell heruntergeladene Themes (z.B. forest-light).
    if not os.path.exists(tcl_path):
        alt = os.path.join(BASE_DIR, "res", "themes", f"{theme_name}.tcl")
        if os.path.exists(alt):
            tcl_path = alt

    if os.path.exists(tcl_path):
        try:
            root.tk.call("source", tcl_path)
            st.theme_use(theme_name)
        except Exception as e:
            print(f"[theme] Forest konnte nicht geladen werden: {e}")
            st.theme_use("clam")
    else:
        print(f"[theme] {tcl_path} fehlt – Fallback auf clam")
        st.theme_use("clam")

    # ── tk_setPalette: forest setzt #313131 – wir wollen unsere Farben ───────
    root.tk.call("tk_setPalette",
                 "background",       C["surface"],
                 "foreground",       C["text"],
                 "highlightColor",   C["accent"],
                 "selectBackground", C["accent"],
                 "selectForeground", C["header"],
                 "activeBackground", C["overlay"],
                 "activeForeground", C["text"])

    # ── Globale Basis (Schrift, Hintergrund, Fokus) ───────────────────────────
    st.configure(".",
            font=("Segoe UI", 9),
            background=C["surface"], foreground=C["text"],
            focuscolor=C["accent"])
    st.configure("TFrame",  background=C["surface"])
    st.configure("TLabel",  background=C["surface"], foreground=C["text"])

    # ── TButton kompakter ─────────────────────────────────────────────────────
    st.configure("TButton", padding=(6, 3), font=("Segoe UI", 9))

    # ── Eingabefelder (forest setzt fieldbackground=grün – überschreiben) ─────
    _border_w = 1 if ACTIVE_THEME == "dark" else 2   # light: dickere Border
    st.configure("TEntry",
            fieldbackground=C["surface2"], foreground=C["text"],
            insertcolor=C["accent"], relief="solid",
            bordercolor=C["border"], borderwidth=_border_w, padding=(6, 5))
    st.map("TEntry",
            fieldbackground=[("focus", C["surface2"])],
            bordercolor=[("focus", C["accent"]),
                          ("!focus", C["border"])])

    st.configure("TCombobox",
            fieldbackground=C["surface2"], foreground=C["text"],
            background=C["surface2"], bordercolor=C["border"],
            borderwidth=_border_w,
            selectbackground=C["overlay"], selectforeground=C["text"])
    st.map("TCombobox",
            fieldbackground=[("readonly", C["surface2"]),
                             ("focus",    C["surface2"]),
                             ("disabled", C["surface"])],
            foreground=[("readonly", C["text"]),
                         ("disabled", C["subtext"])],
            bordercolor=[("focus",  C["accent"]),
                          ("!focus", C["border"])],
            background=[("readonly", C["surface2"]),
                         ("active",   C["overlay"])])

    st.configure("TScrollbar",
            background=C["border"], troughcolor=C["surface2"],
            arrowcolor=C["subtext"], borderwidth=0)
    st.map("TScrollbar",
            background=[("active", C["overlay"])])

    # ── Notebook-Tabs ────────────────────────────────────────────────────────
    # padding BEWUSST NICHT setzen: forest-dark/-light verwendet eine interne
    # -border 5 / -padding {14 4} am Image-Element. Jeder extra bottom-Wert
    # in unserem configure() verkürzt das Image und schiebt die Randlinie
    # mitten in den Text (→ Strikethrough). Nur Schriftgröße setzen –
    # forest skaliert die Tabs dann natürlich mit dem Font.
    st.configure("TNotebook",     background=C["header"], borderwidth=0)
    st.configure("TNotebook.Tab", font=("Segoe UI", 13))
    st.map("TNotebook.Tab",
           foreground=[("selected",  C["accent"]),
                        ("active",    C["text"]),
                        ("!selected", C["subtext"])])

    # ── Treeview ──────────────────────────────────────────────────────────────
    st.configure("Treeview",
            background=C["surface2"], foreground=C["text"],
            fieldbackground=C["surface2"], rowheight=24,
            font=("Segoe UI", 9))
    st.configure("Treeview.Heading",
            background=C["surface"], foreground=C["subtext"],
            font=("Segoe UI", 8, "bold"))
    st.map("Treeview",
           background=[("selected", C["accent"])],
           foreground=[("selected", C["header"])])
    st.map("Treeview.Heading",
           background=[("active", C["overlay"])],
           foreground=[("active", C["text"])])

    # ── LabelFrame ────────────────────────────────────────────────────────────
    st.configure("TLabelframe",
            background=C["surface"], foreground=C["text"],
            bordercolor=C["border"], relief="groove",
            borderwidth=_border_w)
    st.configure("TLabelframe.Label",
            background=C["surface"], foreground=C["text"],
            font=("Segoe UI", 8, "bold"))

    # ── Checkbutton ───────────────────────────────────────────────────────────
    st.configure("TCheckbutton",
            background=C["surface"], foreground=C["text"],
            focuscolor=C["surface"])
    st.map("TCheckbutton", background=[("active", C["surface"])])

    # ── TSeparator ────────────────────────────────────────────────────────────
    st.configure("TSeparator", background=C["border"])

    # ── Progressbar ───────────────────────────────────────────────────────────
    st.configure("TProgressbar",
            troughcolor=C["surface2"], background=C["accent"],
            borderwidth=0, thickness=6)

    # ── option_add: Defaults für native tk-Widgets (Text, Listbox …) ──────────
    root.option_add("*Entry.selectBackground",   C["accent"])
    root.option_add("*Entry.selectForeground",   C["header"])
    root.option_add("*Text.background",          C["surface2"])
    root.option_add("*Text.foreground",          C["text"])
    root.option_add("*Text.selectBackground",    C["accent"])
    root.option_add("*Text.selectForeground",    C["header"])
    root.option_add("*Text.insertBackground",    C["accent"])
    root.option_add("*Listbox.background",       C["surface2"])
    root.option_add("*Listbox.foreground",       C["text"])
    root.option_add("*Listbox.selectBackground", C["accent"])
    root.option_add("*Listbox.selectForeground", C["header"])

    # ── Farbige TButton-Stile ─────────────────────────────────────────────────
    # Forest's Button-Image ist opak → background wird verdeckt.
    # Flat-Layout entfernt das Image und macht unsere Hintergrundfarbe sichtbar.
    _flat = [("Button.padding", {
        "sticky": "nswe",
        "children": [("Button.label", {"sticky": "nswe"})]
    })]

    if ACTIVE_THEME == "dark":
        _btns = [
            ("Green",  "#1e6840", "#247a4c"),   # satt dunkelgrün
            ("Red",    "#8c2828", "#a63030"),
            ("Orange", "#8c5218", "#a66020"),
            ("Blue",   "#1e5c90", "#246aaa"),
            ("Teal",   "#1a6462", "#1e7472"),
            ("Yellow", "#7a6614", "#907818"),
            ("Purple", "#542894", "#6030aa"),
        ]
        _fg = "#ffffff"
    else:
        _btns = [
            ("Green",  "#217346", "#1a5c38"),   # forest-green
            ("Red",    "#c0392b", "#a93226"),
            ("Orange", "#c87020", "#b06018"),
            ("Blue",   "#2471a3", "#1a5f8a"),
            ("Teal",   "#1a7a78", "#156a68"),
            ("Yellow", "#9a7010", "#7a580c"),
            ("Purple", "#7d3c98", "#6a3282"),
        ]
        _fg = "#ffffff"

    for name, bg, hover in _btns:
        st.layout(f"{name}.TButton", _flat)
        st.configure(f"{name}.TButton",
                background=bg, foreground=_fg,
                padding=(8, 3), font=("Segoe UI", 9, "bold"))
        st.map(f"{name}.TButton",
                background=[("active", hover), ("pressed", bg)],
                foreground=[("active", _fg)])


def lazy_tab(nb, frame, factory):
    """factory() wird einmalig aufgerufen wenn der Tab erstmals geöffnet wird.
    Der Event-Handler wird nach Ausführung automatisch entbunden."""
    cb_id = [None]
    def _cb(evt):
        if nb.select() != str(frame):
            return
        nb.unbind("<<NotebookTabChanged>>", cb_id[0])
        factory()
    cb_id[0] = nb.bind("<<NotebookTabChanged>>", _cb, add="+")

def _ensure(*packages):
    """Installiert fehlende Pakete per pip — nur wenn nicht eingefroren (PyInstaller)."""
    if getattr(sys, "frozen", False):
        return
    import importlib
    for pkg, import_name in packages:
        try:
            importlib.import_module(import_name)
            continue
        except ImportError:
            pass
        print(f"[tool] Installiere {pkg}…")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg, "-q",
             "--disable-pip-version-check"],
            capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[pip Fehler] {result.stderr.strip()}")
        importlib.invalidate_caches()

def _btn(parent, text, bg, fg, hover, cmd, **kw):
    """tk.Button im App-Stil."""
    b = tk.Button(parent, text=text, bg=bg, fg=fg,
                  activebackground=hover, activeforeground=fg,
                  font=("Segoe UI", 9, "bold"),
                  relief="flat", bd=0, padx=8, pady=3,
                  command=cmd, **kw)
    return b

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default.copy() if isinstance(default, dict) else default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def pretty_xml(raw):
    """Formatiert XML — wirft Exception bei ungültigem XML."""
    raw = (raw.strip()
           .replace("“", '"').replace("”", '"')
           .replace("‘", "'").replace("’", "'"))
    dom = xml.dom.minidom.parseString(raw)
    return dom.toprettyxml(indent="  ")
