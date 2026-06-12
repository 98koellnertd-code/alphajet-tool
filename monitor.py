import os
import time
import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from utils import C, ToolTip, _ensure, pretty_xml, MOCK_FTP_DIR

# ─── Mock-Drucker Antworten ───────────────────────────────────────────────────
MOCK_RESPONSES = {
    "MAINSTATE":     "<GP><MAINSTATE>0x00000018</MAINSTATE></GP>",
    "STATE":         "<GP><SYS><STATE>0x00000010</STATE></SYS></GP>",
    "VERSION":       "<GP><VERSION><PRINTSERVER>3.1.0.0</PRINTSERVER>"
                     "<PLATFORM>3.0.0.2</PLATFORM><FPGA>01.14</FPGA>"
                     "<CONTROLLER>01.22</CONTROLLER></VERSION></GP>",
    "BOARDINFO":     "<GP><MSG>Board Info</MSG></GP>",
    "BOARDINFO_EXT": "<GP><MSG>Board Info Extended</MSG></GP>",
    "GUICONTROL":    "<GP><MSG>GUI Control Executed</MSG></GP>",
    "DATETIME":      "<GP><SYS><DATETIME>12,00,01,01,2025</DATETIME></SYS></GP>",
    "LOADLAB":       "<GP><LOADLAB>label\\sample.txt</LOADLAB></GP>",
    "FONTLIST":      "<GP><FONTLIST><FACE>a7x5</FACE><FACE>a15x11</FACE>"
                     "<FACE>a32x22</FACE></FONTLIST></GP>",
    "START":         "<GP><MSG>Print started</MSG></GP>",
    "STOP":          "<GP><MSG>Print stopped</MSG></GP>",
    "DEFAULT":       "<GP><MESSAGE>OK</MESSAGE></GP>",
    "SAVEFILE":      "<GP><MESSAGE>File saved</MESSAGE></GP>",
}

def mock_response_for(command):
    cmd_upper = command.upper()
    for key, resp in MOCK_RESPONSES.items():
        if key in cmd_upper:
            return resp
    return MOCK_RESPONSES["DEFAULT"]

# ─── TCP-Proxy ────────────────────────────────────────────────────────────────
class TCPProxy:
    """Lauscht auf einem Port, leitet an Drucker weiter und loggt alles mit."""

    def __init__(self, listen_port, target_ip, target_port, on_data):
        self.listen_port = listen_port
        self.target_ip   = target_ip
        self.target_port = target_port
        self.on_data     = on_data
        self._server     = None
        self._running    = False

    def start(self):
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("", self.listen_port))
        self._server.listen(5)
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def stop(self):
        self._running = False
        try:
            self._server.close()
        except Exception:
            pass

    def _accept_loop(self):
        while self._running:
            try:
                self._server.settimeout(1.0)
                client, addr = self._server.accept()
                threading.Thread(
                    target=self._handle, args=(client, addr), daemon=True).start()
            except socket.timeout:
                continue
            except Exception:
                break

    def _handle(self, client_sock, addr):
        self.on_data(f"[Neue Verbindung von {addr[0]}:{addr[1]}]\n".encode(), "info")
        try:
            target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target.settimeout(5)
            target.connect((self.target_ip, self.target_port))
        except Exception as e:
            self.on_data(f"[Drucker nicht erreichbar: {e}]\n".encode(), "error")
            client_sock.close()
            return

        def relay(src, dst, direction):
            """Leitet src→dst weiter. Schließt nur src; signalisiert dst via shutdown."""
            try:
                while True:
                    data = src.recv(4096)
                    if not data:
                        break
                    self.on_data(data, direction)
                    dst.sendall(data)
            except Exception:
                pass
            finally:
                try:
                    src.close()
                except Exception:
                    pass
                try:
                    # EOF-Signal an Gegenseite – löst dort das recv()==b"" aus
                    dst.shutdown(socket.SHUT_WR)
                except Exception:
                    pass

        t1 = threading.Thread(target=relay, args=(client_sock, target,      "->"), daemon=True)
        t2 = threading.Thread(target=relay, args=(target,      client_sock, "<-"), daemon=True)
        t1.start()
        t2.start()

# ─── Mock-Drucker ─────────────────────────────────────────────────────────────
class MockPrinter:
    """Simulierter Drucker für Tests ohne echtes Gerät."""

    def __init__(self, port, on_data):
        self.port     = port
        self.on_data  = on_data
        self._server  = None
        self._running = False

    def start(self):
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", self.port))
        self._server.listen(5)
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def stop(self):
        self._running = False
        try:
            self._server.close()
        except Exception:
            pass

    def _accept_loop(self):
        while self._running:
            try:
                self._server.settimeout(1.0)
                client, addr = self._server.accept()
                threading.Thread(target=self._handle, args=(client,), daemon=True).start()
            except socket.timeout:
                continue
            except Exception:
                break

    def _handle(self, client):
        welcome = b"<GP><MESSAGE>Connection Accepted</MESSAGE></GP>"
        client.sendall(welcome)
        self.on_data(welcome.decode(), "mock_send")
        buf = b""
        try:
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break
                buf += chunk
                self.on_data(chunk.decode("utf-8", errors="replace"), "mock_recv")
                if b"</GP>" in buf:
                    resp = mock_response_for(buf.decode("utf-8", errors="replace"))
                    client.sendall(resp.encode("utf-8"))
                    self.on_data(resp, "mock_send")
                    buf = b""
        except Exception:
            pass
        finally:
            client.close()

# ─── Mock FTP-Server ──────────────────────────────────────────────────────────
class MockFTPServer:
    """Simulierter FTP-Server für Tests — alphaJET-Verzeichnisstruktur."""

    def __init__(self, port, root_dir, on_log):
        self.port     = port
        self.root_dir = root_dir
        self.on_log   = on_log
        self._server  = None
        self._running = False

    def start(self):
        from pyftpdlib.handlers    import FTPHandler
        from pyftpdlib.servers     import FTPServer
        from pyftpdlib.authorizers import DummyAuthorizer
        import logging
        logging.getLogger("pyftpdlib").setLevel(logging.WARNING)

        on_log = self.on_log

        class _Handler(FTPHandler):
            def on_connect(self):
                on_log(f"Verbindung von {self.remote_ip}", "info")
            def on_disconnect(self):
                on_log(f"Verbindung getrennt ({self.remote_ip})", "info")
            def on_login(self, username):
                on_log(f"Login: {username} ({self.remote_ip})", "info")
            def on_file_received(self, file):
                on_log(f"⬆  Upload:   {os.path.relpath(file, self.authorizer.get_home_dir('test'))}", "info")
            def on_file_sent(self, file):
                on_log(f"⬇  Download: {os.path.relpath(file, self.authorizer.get_home_dir('test'))}", "info")

        auth = DummyAuthorizer()
        auth.add_user("test", "test", self.root_dir, perm="elradfmwMT")
        auth.add_anonymous(self.root_dir, perm="elr")

        _Handler.authorizer         = auth
        _Handler.passive_ports      = range(60000, 60020)
        _Handler.masquerade_address = "127.0.0.1"

        self._server  = FTPServer(("127.0.0.1", self.port), _Handler)
        self._running = True
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        try:
            self._server.serve_forever(timeout=0.5)
        except Exception:
            pass

    def stop(self):
        self._running = False
        if self._server:
            try:
                self._server.close_all()
            except Exception:
                pass
            self._server = None

def _create_mock_ftp_files(root):
    """Legt eine alphaJET-ähnliche Ordnerstruktur mit Testdateien an."""
    for sub in ("labels", "logos", "configs", "printctl"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)

    p = os.path.join(root, "labels", "sample_label.gp")
    if not os.path.exists(p):
        with open(p, "w", encoding="utf-8") as f:
            f.write(
                '<GP><LABEL WIDTH="120" HEIGHT="40">'
                '<TEXT X="5" Y="10" FONT="0" FONTSIZE="6" TEXT="K&amp;B TEST LABEL"/>'
                '<BARCODE X="5" Y="20" TYPE="CODE128" HEIGHT="15" TEXT="12345678"/>'
                '</LABEL></GP>')

    p = os.path.join(root, "logos", "kb_logo.svg")
    if not os.path.exists(p):
        with open(p, "w", encoding="utf-8") as f:
            f.write(
                '<?xml version="1.0"?>\n'
                '<svg xmlns="http://www.w3.org/2000/svg"'
                ' width="32" height="16" viewBox="0 0 32 16">\n'
                '  <rect x="1" y="2"  width="3" height="12" fill="black"/>\n'
                '  <rect x="5" y="2"  width="3" height="5"  fill="black"/>\n'
                '  <rect x="5" y="9"  width="3" height="5"  fill="black"/>\n'
                '  <rect x="8" y="6"  width="3" height="4"  fill="black"/>\n'
                '  <rect x="14" y="2" width="3" height="12" fill="black"/>\n'
                '  <rect x="17" y="2" width="3" height="5"  fill="black"/>\n'
                '  <rect x="20" y="2" width="4" height="3"  fill="black"/>\n'
                '  <rect x="17" y="9" width="3" height="5"  fill="black"/>\n'
                '  <rect x="20" y="9" width="4" height="3"  fill="black"/>\n'
                '</svg>\n')

    p = os.path.join(root, "logos", "checkerboard.mlg")
    if not os.path.exists(p):
        W, H = 16, 8
        data = bytearray([0x00, 0x00, H])
        for col in range(W):
            byte = 0xAA if col % 2 == 0 else 0x55
            data.append(byte)
        with open(p, "wb") as f:
            f.write(data)

    p = os.path.join(root, "configs", "printer_test.pcf")
    if not os.path.exists(p):
        with open(p, "w", encoding="utf-8") as f:
            f.write(
                '<GP><SYSCOMM>'
                '<ADR>192.168.1.100</ADR><PORT>3000</PORT>'
                '<NAME>TEST_DRUCKER</NAME><DHCP>0</DHCP>'
                '</SYSCOMM></GP>')

    p = os.path.join(root, "printctl", "default.ctl")
    if not os.path.exists(p):
        with open(p, "w", encoding="utf-8") as f:
            f.write(
                '<GP><PRINTCTRL>'
                '<TRIGGER>EXT</TRIGGER><REPEAT>1</REPEAT><SPEED>100</SPEED>'
                '</PRINTCTRL></GP>')

# ─── Monitor Tab ──────────────────────────────────────────────────────────────
class MonitorTab(tk.Frame):
    def __init__(self, parent, run_cmd, log, config_data):
        super().__init__(parent, bg=C["bg"])
        self._run_cmd    = run_cmd
        self._log        = log
        self._proxy      = None
        self._mock       = None
        self._mock_ftp   = None
        self.config_data = config_data
        self._build()

    # ── Öffentliche API für FTPTab ─────────────────────────────────────────────
    def ensure_mock_ftp_running(self, port):
        """Startet den Mock-FTP-Server falls noch nicht aktiv. Gibt True bei Erfolg zurück."""
        if self._mock_ftp and self._mock_ftp._running:
            return True

        # ① Port bereits belegt? → externen Server als verfügbar behandeln
        try:
            probe = socket.create_connection(("127.0.0.1", port), timeout=0.3)
            probe.close()
            # Etwas hört bereits – kein eigenes MockFTPServer-Objekt nötig
            self._mock_ftp_btn.config(text="  FTP-Server stoppen", style="Red.TButton")
            self._mock_ftp_status.config(
                text=f"● Externer FTP-Server auf 127.0.0.1:{port}", fg=C["green"])
            self._monitor_log(
                f"[Port {port} bereits belegt – als FTP-Server verwendet]\n", "info")
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            pass  # Port frei → normal starten

        # ② Eigenen MockFTPServer starten
        try:
            _ensure(("pyftpdlib", "pyftpdlib"))
            _create_mock_ftp_files(MOCK_FTP_DIR)
            srv = MockFTPServer(port, MOCK_FTP_DIR, self._mock_ftp_log)
            srv.start()   # bindet Socket synchron in start() – kein sleep nötig
            self._mock_ftp = srv
            self._mock_ftp_btn.config(text="  FTP-Server stoppen", style="Red.TButton")
            self._mock_ftp_status.config(
                text=f"● Läuft auf 127.0.0.1:{port}", fg=C["green"])
            self._monitor_log(f"[Mock FTP-Server gestartet]  127.0.0.1:{port}\n", "info")
            return True
        except Exception as e:
            self._monitor_log(f"[Mock FTP-Server Fehler: {e}]\n", "err")
            return False

    def _build(self):
        outer = tk.Frame(self, bg=C["surface"])
        outer.pack(fill="both", expand=True, padx=14, pady=14)

        top = tk.Frame(outer, bg=C["surface"])
        top.pack(fill="x", pady=(0, 10))

        # ── TCP-Proxy ──
        pf = ttk.LabelFrame(top, text="  TCP-Proxy  (Steuerung → PC → Drucker)")
        pf.pack(side="left", fill="x", expand=True, padx=(0, 8))

        tk.Label(pf,
            text="Drucker-Port auf 3002 umstellen → Proxy auf 3000 starten → "
                 "Am Controller nur die IP auf diese PC-IP ändern (Port 3000 bleibt).",
            bg=C["surface"], fg=C["subtext"], font=("Segoe UI", 8),
            wraplength=400, justify="left").pack(anchor="w", padx=10, pady=(6, 2))

        tk.Label(pf,
            text="⚙  Netzwerk-Tab: Drucker-Port auf 3002 setzen  |  Drucker selbst: Port 3000 → 3002",
            bg=C["surface"], fg=C["yellow"], font=("Segoe UI", 7),
            wraplength=400, justify="left").pack(anchor="w", padx=10, pady=(0, 4))

        row1 = tk.Frame(pf, bg=C["surface"])
        row1.pack(fill="x", padx=10, pady=4)
        tk.Label(row1, text="Lausch-Port (dieser PC):", bg=C["surface"], fg=C["text"],
                 font=("Segoe UI", 9)).pack(side="left")
        self._proxy_port_var = tk.StringVar(value=str(self.config_data.get("proxy_port", 3000)))
        ttk.Entry(row1, textvariable=self._proxy_port_var, width=8).pack(side="left", padx=(8, 20))
        tk.Label(row1, text="Weiterleitung an:", bg=C["surface"], fg=C["text"],
                 font=("Segoe UI", 9)).pack(side="left")
        tk.Label(row1,
            text=f"{self.config_data.get('ip','?')}:{self.config_data.get('port',3002)}",
            bg=C["surface"], fg=C["accent"], font=("Segoe UI", 9, "bold")).pack(side="left", padx=6)

        row2 = tk.Frame(pf, bg=C["surface"])
        row2.pack(fill="x", padx=10, pady=(0, 8))
        self._proxy_btn = ttk.Button(row2, text="  Proxy starten", style="Green.TButton",
                                     command=self._toggle_proxy)
        self._proxy_btn.pack(side="left", padx=(0, 8))
        ToolTip(self._proxy_btn,
            "Startet den TCP-Proxy.\n"
            "Der PC lauscht auf dem eingestellten Port und leitet alle Pakete "
            "an den Drucker weiter — beide Richtungen werden im Log angezeigt.\n\n"
            "Voraussetzung: Drucker-Port im Netzwerk-Tab auf 3002 gesetzt, "
            "Drucker selbst auf Port 3002 umgestellt.")
        self._proxy_status = tk.Label(row2, text="● Gestoppt",
                                      bg=C["surface"], fg=C["red"],
                                      font=("Segoe UI", 9, "bold"))
        self._proxy_status.pack(side="left")

        # ── Mock-Drucker ──
        mf = ttk.LabelFrame(top, text="  Mock-Drucker  (Testen ohne echtes Gerät)")
        mf.pack(side="left", fill="x", expand=True, padx=(8, 0))

        tk.Label(mf,
            text="Simulierter Drucker auf 127.0.0.1. IP im Netzwerk-Tab auf 127.0.0.1 setzen zum Testen.",
            bg=C["surface"], fg=C["subtext"], font=("Segoe UI", 8),
            wraplength=380, justify="left").pack(anchor="w", padx=10, pady=(6, 4))

        row3 = tk.Frame(mf, bg=C["surface"])
        row3.pack(fill="x", padx=10, pady=4)
        tk.Label(row3, text="Port:", bg=C["surface"], fg=C["text"],
                 font=("Segoe UI", 9)).pack(side="left")
        self._mock_port_var = tk.StringVar(value=str(self.config_data.get("mock_port", 3002)))
        ttk.Entry(row3, textvariable=self._mock_port_var, width=8).pack(side="left", padx=8)
        tk.Label(row3, text="→ Im Netzwerk-Tab: IP=127.0.0.1, Port=",
                 bg=C["surface"], fg=C["subtext"], font=("Segoe UI", 8)).pack(side="left")
        tk.Label(row3, textvariable=self._mock_port_var,
                 bg=C["surface"], fg=C["yellow"], font=("Segoe UI", 8, "bold")).pack(side="left")

        row4 = tk.Frame(mf, bg=C["surface"])
        row4.pack(fill="x", padx=10, pady=(0, 8))
        self._mock_btn = ttk.Button(row4, text="  Mock starten", style="Yellow.TButton",
                                    command=self._toggle_mock)
        self._mock_btn.pack(side="left", padx=(0, 8))
        ToolTip(self._mock_btn,
            "Startet einen simulierten alphaJET-Drucker auf 127.0.0.1.\n"
            "Netzwerk-Tab: IP auf 127.0.0.1 und Port auf den Mock-Port setzen.\n"
            "Nützlich zum Testen ohne echtes Gerät.")
        self._mock_status = tk.Label(row4, text="● Gestoppt",
                                     bg=C["surface"], fg=C["red"],
                                     font=("Segoe UI", 9, "bold"))
        self._mock_status.pack(side="left")

        # ── Mock FTP-Server ──
        ftp_row = tk.Frame(outer, bg=C["surface"])
        ftp_row.pack(fill="x", pady=(0, 10))

        ff = ttk.LabelFrame(ftp_row, text="  Mock FTP-Server  (FTP-Tab ohne echtes Gerät testen)")
        ff.pack(fill="x")

        tk.Label(ff,
            text=(
                "Simulierter alphaJET FTP-Server mit vorbefüllten Testdateien "
                "(Labels, Logos, Configs, PrintControls).  "
                "Im FTP-Tab: IP = 127.0.0.1  ·  Port = 2121  ·  "
                "User = test  ·  PW = test"),
            bg=C["surface"], fg=C["subtext"],
            font=("Segoe UI", 8), wraplength=900, justify="left",
            anchor="w").pack(anchor="w", padx=10, pady=(6, 4))

        ftp_ctrl = tk.Frame(ff, bg=C["surface"])
        ftp_ctrl.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(ftp_ctrl, text="Port:", bg=C["surface"],
                 fg=C["text"], font=("Segoe UI", 9)).pack(side="left")
        self._mock_ftp_port_var = tk.StringVar(value="2121")
        ttk.Entry(ftp_ctrl, textvariable=self._mock_ftp_port_var, width=7).pack(side="left", padx=8)

        self._mock_ftp_btn = ttk.Button(
            ftp_ctrl, text="  FTP-Server starten",
            style="Yellow.TButton", command=self._toggle_mock_ftp)
        self._mock_ftp_btn.pack(side="left", padx=(0, 8))
        ToolTip(self._mock_ftp_btn,
            "Startet einen simulierten FTP-Server mit alphaJET-Testdateien.\n"
            "FTP-Tab: IP auf 127.0.0.1 setzen um den Mock zu nutzen.")

        self._mock_ftp_status = tk.Label(
            ftp_ctrl, text="● Gestoppt",
            bg=C["surface"], fg=C["red"],
            font=("Segoe UI", 9, "bold"))
        self._mock_ftp_status.pack(side="left")

        ttk.Button(
            ftp_ctrl, text="📁  Testordner öffnen",
            style="Blue.TButton",
            command=lambda: os.startfile(MOCK_FTP_DIR)
                    if os.path.exists(MOCK_FTP_DIR) else None
        ).pack(side="left", padx=(20, 0))

        # ── Log-Bereich ──
        nb_inner = ttk.Notebook(outer)
        nb_inner.pack(fill="both", expand=True)

        self._tab_xml = ttk.Frame(nb_inner)
        self._tab_raw = ttk.Frame(nb_inner)
        nb_inner.add(self._tab_xml, text="  G-PRINT XML (lesbar)  ")
        nb_inner.add(self._tab_raw, text="  Raw TCP (Bytes)       ")

        self.monitor_xml = scrolledtext.ScrolledText(
            self._tab_xml, bg=C["header"], fg=C["text"],
            insertbackground=C["text"], font=("Consolas", 9),
            relief="flat", bd=0, selectbackground=C["overlay"])
        self.monitor_xml.pack(fill="both", expand=True, padx=4, pady=4)
        self.monitor_xml.tag_config("out",       foreground=C["accent"])
        self.monitor_xml.tag_config("in",        foreground=C["green"])
        self.monitor_xml.tag_config("info",      foreground=C["purple"])
        self.monitor_xml.tag_config("err",       foreground=C["red"])
        self.monitor_xml.tag_config("mock_send", foreground=C["yellow"])
        self.monitor_xml.tag_config("mock_recv", foreground=C["orange"])

        self.monitor_raw = scrolledtext.ScrolledText(
            self._tab_raw, bg=C["header"], fg=C["green"],
            insertbackground=C["text"], font=("Consolas", 9),
            relief="flat", bd=0, selectbackground=C["overlay"])
        self.monitor_raw.pack(fill="both", expand=True, padx=4, pady=4)

        btn_mon = tk.Frame(outer, bg=C["surface"])
        btn_mon.pack(fill="x", pady=(6, 0))
        ttk.Button(btn_mon, text="  Log leeren", style="Red.TButton",
                   command=self._clear_monitor).pack(side="left", padx=(0, 6))

    def _toggle_proxy(self):
        if self._proxy and self._proxy._running:
            self._proxy.stop()
            self._proxy = None
            self._proxy_btn.config(text="  Proxy starten", style="Green.TButton")
            self._proxy_status.config(text="● Gestoppt", fg=C["red"])
            self._monitor_log("[Proxy gestoppt]\n", "info")
        else:
            try:
                port = int(self._proxy_port_var.get())
                ip   = self.config_data.get("ip", "192.168.1.100")
                tgt  = int(self.config_data.get("port", 3000))
                self._proxy = TCPProxy(port, ip, tgt, self._proxy_data)
                self._proxy.start()
                self._proxy_btn.config(text="  Proxy stoppen", style="Red.TButton")
                self._proxy_status.config(text=f"● Läuft auf Port {port}", fg=C["green"])
                self._monitor_log(
                    f"[Proxy gestartet] Lauscht auf :{port} → Weiterleitung an {ip}:{tgt}\n", "info")
            except Exception as e:
                messagebox.showerror("Fehler", f"Proxy konnte nicht gestartet werden:\n{e}")

    def _toggle_mock(self):
        if self._mock and self._mock._running:
            self._mock.stop()
            self._mock = None
            self._mock_btn.config(text="  Mock starten", style="Yellow.TButton")
            self._mock_status.config(text="● Gestoppt", fg=C["red"])
            self._monitor_log("[Mock-Drucker gestoppt]\n", "info")
        else:
            try:
                port = int(self._mock_port_var.get())
                self._mock = MockPrinter(port, self._mock_data)
                self._mock.start()
                self._mock_btn.config(text="  Mock stoppen", style="Red.TButton")
                self._mock_status.config(text=f"● Läuft auf 127.0.0.1:{port}", fg=C["green"])
                self._monitor_log(
                    f"[Mock-Drucker gestartet] 127.0.0.1:{port}\n"
                    f"→ Im Netzwerk-Tab: IP = 127.0.0.1, Port = {port}\n", "info")
            except Exception as e:
                messagebox.showerror("Fehler", f"Mock konnte nicht gestartet werden:\n{e}")

    def _toggle_mock_ftp(self):
        if self._mock_ftp and self._mock_ftp._running:
            self._mock_ftp.stop()
            self._mock_ftp = None
            self._mock_ftp_btn.config(text="  FTP-Server starten", style="Yellow.TButton")
            self._mock_ftp_status.config(text="● Gestoppt", fg=C["red"])
            self._monitor_log("[Mock FTP-Server gestoppt]\n", "info")
        else:
            try:
                port = int(self._mock_ftp_port_var.get())
                if not self.ensure_mock_ftp_running(port):
                    messagebox.showerror(
                        "FTP-Server Fehler",
                        "Server konnte nicht gestartet werden.\n\n"
                        "Hinweis: pyftpdlib wird automatisch installiert.")
                else:
                    self._monitor_log(
                        f"[Mock FTP-Server gestartet]  127.0.0.1:{port}\n"
                        f"  → FTP-Tab:  IP = 127.0.0.1  ·  Port = {port}"
                        f"  ·  Gerät = Mock  ·  User = test  ·  PW = test\n"
                        f"  → Testdateien:  {MOCK_FTP_DIR}\n", "info")
            except Exception as e:
                messagebox.showerror("FTP-Server Fehler",
                                     f"Server konnte nicht gestartet werden:\n{e}")

    def _mock_ftp_log(self, msg, kind="info"):
        ts   = time.strftime("%H:%M:%S")
        line = f"[{ts}]  FTP  {msg}\n"
        self.after(0, lambda: self._monitor_log(line, kind))

    def _proxy_data(self, data, direction):
        if isinstance(data, bytes):
            text = data.decode("utf-8", errors="replace")
        else:
            text = str(data)
        ts    = time.strftime("%H:%M:%S")
        arrow = "→ Steuerung→Drucker" if direction == "->" else "← Drucker→Steuerung"
        tag   = "out" if direction == "->" else "in"
        try:
            pretty = pretty_xml(text.strip()) if "<GP>" in text else text
        except Exception:
            pretty = text
        xml_line = f"[{ts}] {arrow}\n{pretty}\n{'─'*50}\n"
        raw_line = f"[{ts}] {arrow}\n{repr(data if isinstance(data, bytes) else data.encode())}\n\n"
        self.after(0, lambda x=xml_line, t=tag: self._monitor_log(x, t))
        self.after(0, lambda r=raw_line: self._monitor_raw_log(r))

    def _mock_data(self, text, direction):
        ts    = time.strftime("%H:%M:%S")
        arrow = "← Mock sendet" if direction == "mock_send" else "→ Mock empfängt"
        tag   = direction
        try:
            pretty = pretty_xml(text.strip()) if "<GP>" in text else text
        except Exception:
            pretty = text
        self.after(0, lambda x=f"[{ts}] {arrow}\n{pretty}\n{'─'*50}\n", t=tag:
                   self._monitor_log(x, t))
        self.after(0, lambda r=f"[{ts}] {arrow}\n{repr(text.encode())}\n\n":
                   self._monitor_raw_log(r))

    def _monitor_log(self, text, tag="info"):
        self.monitor_xml.insert("end", text, tag)
        self.monitor_xml.see("end")

    def _monitor_raw_log(self, text):
        self.monitor_raw.insert("end", text)
        self.monitor_raw.see("end")

    def _clear_monitor(self):
        self.monitor_xml.delete("1.0", "end")
        self.monitor_raw.delete("1.0", "end")
