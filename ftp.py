import os
import ftplib
import shutil
import tempfile
import zipfile
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from utils import (C, ToolTip, _ensure,
                   LABELS_DIR, CONFIGS_DIR, PRINTCTL_DIR, LOGOS_DIR, MOCK_FTP_DIR,
                   DEVICE_FTP, LABEL_EXTS, CONFIG_EXTS, PRINTCTL_EXTS,
                   validate_ip, validate_port, validate_local_path,
                   security_log)

# ─── FTP Tab ──────────────────────────────────────────────────────────────────
class FTPTab(tk.Frame):
    """
    FTP-Verbindungs-Tab.

    Benötigte Parameter:
      log              – App._log Callable
      config_data      – App.config_data dict
      label_editor_ref – LabelEditorTab-Instanz
      logo_editor_ref  – LogoEditorTab-Instanz
      file_refresh_cb  – App._file_refresh(folder, list_attr, exts)
      switch_tab_cb    – App._switch_to_tab(tab_text)
      cfg_name_var     – App.cfg_name_var (StringVar)
      cfg_editor       – App.cfg_editor (ScrolledText)
      ctl_name_var     – App.ctl_name_var (StringVar)
      ctl_editor       – App.ctl_editor (ScrolledText)
      monitor_tab      – MonitorTab-Instanz (optional, für Mock-FTP-Auto-Start)
    """

    def __init__(self, parent, log, config_data,
                 label_editor_ref,
                 logo_editor_ref,
                 file_refresh_cb,
                 switch_tab_cb,
                 cfg_name_var,
                 cfg_editor,
                 ctl_name_var,
                 ctl_editor,
                 monitor_tab=None):
        super().__init__(parent, bg=C["bg"])
        self._log           = log
        self.config_data    = config_data
        self._label_editor  = label_editor_ref
        self._logo_editor   = logo_editor_ref
        self._file_refresh  = file_refresh_cb
        self._switch_to_tab = switch_tab_cb
        self.cfg_name_var   = cfg_name_var
        self.cfg_editor     = cfg_editor
        self.ctl_name_var   = ctl_name_var
        self.ctl_editor     = ctl_editor
        self._monitor_tab   = monitor_tab
        self._ftp              = None
        self._ftp_lock         = threading.Lock()  # schützt self._ftp vor Race Conditions
        self._ftp_keepalive_on = False
        self._ftp_keepalive_id = None   # after-ID → verhindert doppelte Loops
        self._build()

    def _build(self):
        f = self   # Tab-Frame ist self

        # ── Header: Verbindung ──
        hdr = tk.Frame(f, bg=C["header"])
        hdr.pack(fill="x", padx=0, pady=0)

        tk.Label(hdr, text="  FTP — Drucker-Verbindung",
                 bg=C["header"], fg=C["accent"],
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=8, pady=8)

        conn_row = tk.Frame(hdr, bg=C["header"])
        conn_row.pack(side="left", padx=8, pady=6)

        def lbl(text):
            tk.Label(conn_row, text=text, bg=C["header"], fg=C["subtext"],
                     font=("Segoe UI", 9)).pack(side="left", padx=(0, 3))

        lbl("Gerät:")
        self._ftp_dev_var = tk.StringVar(value=self.config_data.get("device", "AJD"))
        dev_cb = ttk.Combobox(conn_row, textvariable=self._ftp_dev_var,
                              values=list(DEVICE_FTP.keys()), width=6, state="readonly")
        dev_cb.pack(side="left", padx=(0, 12))
        dev_cb.bind("<<ComboboxSelected>>", lambda e: self._ftp_fill_creds())

        lbl("IP:")
        self._ftp_ip_var = tk.StringVar(value=self.config_data.get("ip", ""))
        ttk.Entry(conn_row, textvariable=self._ftp_ip_var, width=15).pack(side="left", padx=(0, 12))

        lbl("Port:")
        self._ftp_port_var = tk.StringVar(value="21")
        ttk.Entry(conn_row, textvariable=self._ftp_port_var, width=5).pack(side="left", padx=(0, 12))

        lbl("User:")
        self._ftp_user_var = tk.StringVar()
        ttk.Entry(conn_row, textvariable=self._ftp_user_var, width=9).pack(side="left", padx=(0, 6))

        lbl("PW:")
        self._ftp_pass_var = tk.StringVar()
        ttk.Entry(conn_row, textvariable=self._ftp_pass_var, width=11,
                  show="*").pack(side="left", padx=(0, 12))

        self._ftp_conn_btn = ttk.Button(conn_row, text="  Verbinden",
                                        style="Green.TButton",
                                        command=self._ftp_connect)
        self._ftp_conn_btn.pack(side="left", padx=(0, 8))
        ToolTip(self._ftp_conn_btn,
                "Verbindet oder trennt die FTP-Verbindung zum Drucker.\n"
                "Benutzername/Passwort leer lassen wenn kein Login nötig.")

        self._ftp_status = tk.Label(conn_row, text="● Getrennt",
                                    bg=C["header"], fg=C["red"],
                                    font=("Segoe UI", 9, "bold"))
        self._ftp_status.pack(side="left")

        tk.Label(hdr,
                 text="⚠  FTP überträgt Daten unverschlüsselt – nur in gesichertem Netzwerk verwenden (CRA Art. 13)",
                 bg=C["header"], fg=C["yellow"],
                 font=("Segoe UI", 8)).pack(side="left", padx=(16, 0), pady=(0, 6))

        self._ftp_fill_creds()

        # ── Haupt-Bereich: Baum + Aktionen ──
        body = tk.Frame(f, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=10, pady=8)

        # Dateibaum (links)
        tree_frame = tk.Frame(body, bg=C["surface"], bd=0)
        tree_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tree_hdr = tk.Frame(tree_frame, bg=C["surface2"])
        tree_hdr.pack(fill="x")
        tk.Label(tree_hdr, text="  Drucker-Dateisystem",
                 bg=C["surface2"], fg=C["accent"],
                 font=("Segoe UI", 9, "bold")).pack(side="left", pady=6, padx=6)
        ttk.Button(tree_hdr, text="⟳  Aktualisieren",
                   style="Blue.TButton",
                   command=self._ftp_refresh).pack(side="right", padx=6, pady=4)

        self._ftp_progress = tk.Label(
            tree_frame, text="", bg=C["surface"], fg=C["subtext"],
            font=("Segoe UI", 8), anchor="w")
        self._ftp_progress.pack(fill="x", padx=6)

        tv_frame = tk.Frame(tree_frame, bg=C["surface"])
        tv_frame.pack(fill="both", expand=True)

        vsb = ttk.Scrollbar(tv_frame, orient="vertical")
        hsb = ttk.Scrollbar(tv_frame, orient="horizontal")

        self._ftp_tree = ttk.Treeview(
            tv_frame, columns=("size", "date"),
            yscrollcommand=vsb.set, xscrollcommand=hsb.set,
            selectmode="browse")
        vsb.config(command=self._ftp_tree.yview)
        hsb.config(command=self._ftp_tree.xview)

        _s = ttk.Style()
        _s.configure("Ftp.Treeview",
                     background=C["surface2"], foreground=C["text"],
                     fieldbackground=C["surface2"], rowheight=22,
                     font=("Segoe UI", 9), borderwidth=0)
        _s.configure("Ftp.Treeview.Heading",
                     background=C["overlay"], foreground=C["accent"],
                     font=("Segoe UI", 9, "bold"), relief="flat")
        _s.map("Ftp.Treeview",
               background=[("selected", C["accent"])],
               foreground=[("selected", C["header"])])
        self._ftp_tree.configure(style="Ftp.Treeview")

        self._ftp_tree.heading("#0",   text="  Name", anchor="w")
        self._ftp_tree.heading("size", text="Größe",  anchor="w")
        self._ftp_tree.heading("date", text="Datum",  anchor="w")
        self._ftp_tree.column("#0",    width=260, minwidth=160, stretch=True)
        self._ftp_tree.column("size",  width=80,  minwidth=60,  stretch=False)
        self._ftp_tree.column("date",  width=120, minwidth=80,  stretch=False)

        hsb.pack(side="bottom", fill="x")
        vsb.pack(side="right",  fill="y")
        self._ftp_tree.pack(fill="both", expand=True)
        self._ftp_tree.bind("<<TreeviewOpen>>",  self._ftp_expand)
        self._ftp_tree.bind("<Double-Button-1>", self._ftp_dblclick)

        # Aktionen (rechts)
        right = tk.Frame(body, bg=C["surface"], width=220)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        def section(text):
            tk.Frame(right, bg=C["border"], height=1).pack(fill="x", padx=8, pady=(8, 0))
            tk.Label(right, text=text, bg=C["surface"], fg=C["accent"],
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(4, 2))

        def btn(text, style, cmd, tip=""):
            b = ttk.Button(right, text=text, style=style, command=cmd)
            b.pack(fill="x", padx=8, pady=2)
            if tip:
                ToolTip(b, tip)

        section("Allgemein")
        btn("⬇  Download → lokal",     "Green.TButton",  self._ftp_download,
            "Lädt die ausgewählte Datei vom Drucker\nauf diesen PC herunter.")
        btn("⬆  Dateien hochladen",     "Orange.TButton", self._ftp_upload,
            "Wählt eine oder mehrere Dateien vom PC\nund lädt sie auf den Drucker hoch.")
        btn("⬆  Ordner hochladen",      "Orange.TButton", self._ftp_upload_folder,
            "Lädt einen ganzen Ordner mit allen Inhalten\nauf den Drucker hoch.")
        btn("🗑  Datei löschen",        "Red.TButton",    self._ftp_delete,
            "Löscht die ausgewählte Datei oder den Ordner\n(inkl. Inhalt) auf dem Drucker.")

        section("Backup")
        btn("📦  Alles als ZIP sichern","Purple.TButton", self._ftp_backup,
            "Lädt alle Dateien vom Drucker herunter\nund speichert sie als ZIP-Archiv.")

        section("Labels")
        btn("💾  Lokal speichern",      "Green.TButton",  self._ftp_save_label,
            "Speichert das ausgewählte Label\nin den lokalen Labels-Ordner.")
        btn("✏  Im Label Editor öffnen","Blue.TButton",   self._ftp_open_in_editor,
            "Öffnet das ausgewählte Label direkt\nim Label Editor zum Bearbeiten.")

        section("Logos (.mlg / .svg)")
        btn("💾  Lokal speichern",         "Green.TButton", self._ftp_save_logo,
            "Speichert das ausgewählte Logo\nin den lokalen Logos-Ordner.")
        btn("🎨  Im Logo Editor öffnen",   "Blue.TButton",  self._ftp_open_in_logo_editor,
            "Öffnet das ausgewählte Logo direkt\nim Logo Editor zum Bearbeiten.")

        section("Configs")
        btn("💾  Lokal speichern",         "Green.TButton", self._ftp_save_config,
            "Speichert die ausgewählte Config-Datei\nin den lokalen Configs-Ordner.")
        btn("✏  Im Config Editor öffnen",  "Blue.TButton",  self._ftp_open_in_config,
            "Öffnet die Config-Datei direkt\nim Config Editor zum Bearbeiten.")

        section("PrintControls (.ctl)")
        btn("💾  Lokal speichern",           "Green.TButton", self._ftp_save_printctl,
            "Speichert die ausgewählte PrintControl-Datei\nin den lokalen PrintControls-Ordner.")
        btn("✏  Im PrintCtl Editor öffnen", "Blue.TButton",  self._ftp_open_in_printctl,
            "Öffnet die PrintControl-Datei direkt\nim PrintControls Editor zum Bearbeiten.")

    # ── Verbindungs-Hilfsmethoden ──────────────────────────────────────────────

    def _ftp_ok(self):
        if not self._ftp:
            self._log("FTP: Keine aktive Verbindung.", "error")
            return False
        return True

    def _ftp_retr(self, remote_path, local_path):
        """Sicherer Download mit 120s Timeout."""
        old = self._ftp.sock.gettimeout()
        self._ftp.sock.settimeout(120)
        try:
            with open(local_path, "wb") as fp:
                self._ftp.retrbinary(f"RETR {remote_path}", fp.write)
            return True
        finally:
            self._ftp.sock.settimeout(old)

    def _ftp_stor(self, local_path, remote_path):
        """Sicherer Upload mit 120s Timeout."""
        old = self._ftp.sock.gettimeout()
        self._ftp.sock.settimeout(120)
        try:
            with open(local_path, "rb") as fp:
                self._ftp.storbinary(f"STOR {remote_path}", fp)
            return True
        finally:
            self._ftp.sock.settimeout(old)

    def _ftp_fill_creds(self):
        dev  = self._ftp_dev_var.get()
        cred = DEVICE_FTP.get(dev, DEVICE_FTP["AJD"])
        self._ftp_user_var.set(cred["user"])
        self._ftp_pass_var.set(cred["pass"])
        self._ftp_port_var.set(str(cred["port"]))
        host = cred.get("host", "")
        if host:
            self._ftp_ip_var.set(host)
        else:
            # Kein fester Host (AJD/AJ5) → aktuelle gespeicherte Drucker-IP eintragen
            self._ftp_ip_var.set(self.config_data.get("ip", ""))
        self.config_data["device"] = dev

    def _ftp_connect(self):
        if self._ftp:
            self._ftp_keepalive_on = False
            if self._ftp_keepalive_id:
                self.after_cancel(self._ftp_keepalive_id)
                self._ftp_keepalive_id = None
            with self._ftp_lock:
                ftp, self._ftp = self._ftp, None
            try:
                ftp.quit()
            except Exception:
                pass
            self._ftp_conn_btn.config(text="  Verbinden", style="Green.TButton")
            self._ftp_status.config(text="● Getrennt", fg=C["red"])
            self._ftp_tree.delete(*self._ftp_tree.get_children())
            self._ftp_set_progress("")
            return

        ip       = self._ftp_ip_var.get().strip()
        port_str = self._ftp_port_var.get().strip() or "21"
        user = self._ftp_user_var.get()
        pw   = self._ftp_pass_var.get()

        if not validate_ip(ip):
            messagebox.showerror("Ungültige Eingabe",
                f"'{ip}' ist keine gültige IPv4-Adresse.")
            return
        if not validate_port(port_str):
            messagebox.showerror("Ungültige Eingabe",
                "FTP-Port muss zwischen 1 und 65535 liegen.")
            return
        port = int(port_str)

        # Mock-Gerät: Server automatisch starten falls noch nicht aktiv
        if self._ftp_dev_var.get() == "Mock":
            if self._monitor_tab:
                if not self._monitor_tab.ensure_mock_ftp_running(port):
                    messagebox.showerror(
                        "Mock FTP-Server",
                        "Server konnte nicht gestartet werden.\n\n"
                        "Tipp: pyftpdlib wird automatisch installiert.")
                    return
            else:
                messagebox.showerror("Mock FTP-Server",
                                     "Monitor-Tab nicht verfügbar.")
                return

        self._ftp_status.config(text="● Verbinde...", fg=C["yellow"])
        self.update_idletasks()

        def connect():
            try:
                ftp = ftplib.FTP()
                ftp.connect(ip, port, timeout=30)
                ftp.login(user, pw)
                ftp.set_pasv(True)
                with self._ftp_lock:
                    self._ftp = ftp
                security_log("FTP_CONNECT", f"{ip}:{port}", "ok")
                self.after(0, self._ftp_on_connected)
            except Exception as e:
                err = str(e)
                security_log("FTP_CONNECT", f"{ip}:{port}", "error")
                self.after(0, lambda: self._ftp_on_error(err))

        threading.Thread(target=connect, daemon=True).start()

    def _ftp_on_connected(self):
        self._ftp_conn_btn.config(text="  Trennen", style="Red.TButton")
        self._ftp_status.config(text="● Verbunden", fg=C["green"])
        self._log(f"FTP verbunden: {self._ftp_ip_var.get()}", "info")
        self._ftp_keepalive_on = True
        self._ftp_keepalive_id = self.after(10000, self._ftp_keepalive_loop)
        self._ftp_refresh()

    def _ftp_on_error(self, err):
        self._ftp_keepalive_on = False
        self._ftp = None
        self._ftp_status.config(text="● Fehler", fg=C["red"])
        self._log(f"FTP-Fehler: {err}", "error")
        messagebox.showerror("FTP-Fehler", err)

    def _ftp_keepalive_loop(self):
        if not self._ftp_keepalive_on:
            self._ftp_keepalive_id = None
            return
        def check():
            with self._ftp_lock:
                ftp = self._ftp   # lokale Kopie – sicher auch wenn self._ftp wechselt
            if not ftp:
                return
            try:
                ftp.voidcmd("NOOP")
                def _ok():
                    self._ftp_status.config(text="● Verbunden", fg=C["green"])
                self.after(0, _ok)
            except Exception:
                self.after(0, self._ftp_on_kicked)
        threading.Thread(target=check, daemon=True).start()
        self._ftp_keepalive_id = self.after(10000, self._ftp_keepalive_loop)

    def _ftp_on_kicked(self):
        self._ftp_keepalive_on = False
        self._ftp_keepalive_id = None
        self._ftp = None
        self._ftp_conn_btn.config(text="  Verbinden", style="Green.TButton")
        self._ftp_status.config(text="● Offline", fg=C["red"])
        self._ftp_tree.delete(*self._ftp_tree.get_children())
        self._ftp_set_progress("")
        self._log("FTP: Verbindung verloren.", "error")

    # ── Dateibaum ─────────────────────────────────────────────────────────────

    def _ftp_refresh(self):
        if not self._ftp:
            return
        self._ftp_tree.delete(*self._ftp_tree.get_children())
        self._ftp_list_dir("/", "")

    def _ftp_list_dir(self, path, parent_id):
        def do_list():
            if not self._ftp:
                return
            old = self._ftp.sock.gettimeout()
            self._ftp.sock.settimeout(30)
            try:
                entries = list(self._ftp.mlsd(path))
                self._ftp.sock.settimeout(old)
                self.after(0, lambda: self._ftp_populate_mlsd(path, parent_id, entries))
                return
            except Exception:
                pass

            if not self._ftp:
                return

            # LIST fallback: parses ls-l / Windows DIR output → type info available
            try:
                lines = []
                self._ftp.retrlines(f"LIST {path}", lines.append)
                self._ftp.sock.settimeout(old)
                entries = self._parse_list_lines(lines)
                if entries:
                    self.after(0, lambda: self._ftp_populate_mlsd(path, parent_id, entries))
                    return
            except Exception:
                pass

            # Last resort: NLST, no type info
            try:
                names = self._ftp.nlst(path)
                self._ftp.sock.settimeout(old)
                self.after(0, lambda: self._ftp_populate_nlst(path, parent_id, names))
            except Exception as e2:
                try:
                    self._ftp.sock.settimeout(old)
                except Exception:
                    pass
                err = str(e2)
                self.after(0, lambda: self._log(f"FTP dir error: {err}", "error"))

        threading.Thread(target=do_list, daemon=True).start()

    @staticmethod
    def _parse_list_lines(lines):
        """Convert raw LIST output to mlsd-compatible (name, facts) tuples."""
        entries = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Unix/VxWorks: drwxr-xr-x [cols...] name
            # Column count varies by server (8–9 typical); take last token as name.
            if line[0] in ('d', '-', 'l'):
                parts = line.split()
                if len(parts) >= 4:
                    name = parts[-1]
                    etype = "dir" if line[0] == 'd' else "file"
                    size = next((p for p in parts[1:] if p.isdigit()), "0")
                    entries.append((name, {"type": etype, "size": size}))
            # Windows: 01-01-2024  12:00AM  <DIR>  dirname
            elif "<DIR>" in line:
                entries.append((line.split()[-1], {"type": "dir", "size": "0"}))
            # Windows file: 01-01-2024  12:00AM  1234  filename
            else:
                parts = line.split()
                if len(parts) >= 4:
                    size = parts[2] if parts[2].isdigit() else "0"
                    entries.append((parts[-1], {"type": "file", "size": size}))
        return entries

    @staticmethod
    def _ftp_file_icon(name):
        ext = os.path.splitext(name)[1].lower()
        return {
            ".txt": "📝", ".xml": "📝", ".gp": "📝",
            ".pcf": "⚙",
            ".ctl": "🖨",
            ".mlg": "🖼", ".bmp": "🖼", ".png": "🖼", ".jpg": "🖼",
        }.get(ext, "📄")

    def _ftp_populate_mlsd(self, path, parent_id, entries):
        for name, facts in sorted(entries,
                key=lambda e: (e[1].get("type", "file").lower() not in
                               ("dir", "cdir", "pdir"), e[0].lower())):
            if name in (".", ".."):
                continue
            full_path = path.rstrip("/") + "/" + name
            is_dir    = facts.get("type", "file").lower() in ("dir", "cdir", "pdir")
            size_raw  = facts.get("size", "")
            modify    = facts.get("modify", "")
            date_str  = f"{modify[6:8]}.{modify[4:6]}.{modify[:4]}" if len(modify) >= 8 else ""
            if is_dir:
                node = self._ftp_tree.insert(
                    parent_id, "end", text=f"📁  {name}",
                    values=("<Ordner>", date_str), open=False)
                self._ftp_tree.insert(node, "end", text="...", tags=("placeholder",))
                self._ftp_tree.item(node, tags=("dir", full_path))
            else:
                icon    = self._ftp_file_icon(name)
                size_kb = f"{int(size_raw)//1024} KB" if size_raw.isdigit() else size_raw
                self._ftp_tree.insert(
                    parent_id, "end", text=f"{icon}  {name}",
                    values=(size_kb, date_str), tags=("file", full_path))

    def _ftp_populate_nlst(self, path, parent_id, names):
        for name in sorted(names, key=lambda n: n.lower()):
            name = name.split("/")[-1]
            if not name or name in (".", ".."):
                continue
            full_path = path.rstrip("/") + "/" + name
            self._ftp_tree.insert(
                parent_id, "end", text=f"{self._ftp_file_icon(name)}  {name}",
                values=("", ""), tags=("file", full_path))

    def _ftp_expand(self, event):
        node = self._ftp_tree.focus()
        tags = self._ftp_tree.item(node, "tags")
        if not tags or tags[0] != "dir":
            return
        children = self._ftp_tree.get_children(node)
        if len(children) == 1 and self._ftp_tree.item(children[0], "text") == "...":
            self._ftp_tree.delete(children[0])
            path = tags[1] if len(tags) > 1 else "/"
            self._ftp_list_dir(path, node)

    def _ftp_selected_path(self):
        node = self._ftp_tree.focus()
        if not node:
            return None, None
        tags = self._ftp_tree.item(node, "tags")
        if len(tags) >= 2:
            return tags[0], tags[1]
        return None, None

    def _ftp_dblclick(self, _event):
        ftype, fpath = self._ftp_selected_path()
        if ftype == "file" and fpath:
            self._ftp_open_in_editor()

    def _ftp_set_progress(self, text):
        self._ftp_progress.config(text=f"  {text}" if text else "")

    # ── Download ──────────────────────────────────────────────────────────────

    def _ftp_download(self):
        if not self._ftp_ok():
            return
        ftype, fpath = self._ftp_selected_path()
        if not fpath:
            messagebox.showinfo("Hinweis", "Bitte eine Datei oder einen Ordner auswählen.")
            return

        if ftype == "dir":
            dest_dir = filedialog.askdirectory(
                title="Ordner speichern nach...",
                initialdir=os.path.expanduser("~"))
            if not dest_dir:
                return
            local_dir = os.path.join(dest_dir, os.path.basename(fpath))
            def do_dl_folder():
                try:
                    count = self._ftp_download_recursive(fpath, local_dir)
                    self.after(0, lambda: self._log(
                        f"Ordner-Download OK: {fpath} → {local_dir} ({count} Dateien)", "info"))
                    self.after(0, lambda: self._ftp_set_progress(""))
                except Exception as e:
                    err = str(e)
                    self.after(0, lambda: self._log(f"FTP Ordner-Download Fehler: {err}", "error"))
                    self.after(0, lambda: self._ftp_set_progress(""))
            threading.Thread(target=do_dl_folder, daemon=True).start()
        else:
            fn   = os.path.basename(fpath)
            dest = filedialog.asksaveasfilename(
                title="Lokal speichern als...",
                initialfile=fn,
                defaultextension="",
                initialdir=os.path.expanduser("~"),
                filetypes=[("Alle Dateien", "*.*")])
            if not dest:
                return
            def do_dl():
                if not self._ftp:
                    return
                try:
                    self._ftp_retr(fpath, dest)
                    self.after(0, lambda: self._log(f"Download OK: {fpath} → {dest}", "info"))
                except Exception as e:
                    err = str(e)
                    self.after(0, lambda: self._log(f"FTP Download Fehler: {err}", "error"))
            threading.Thread(target=do_dl, daemon=True).start()

    def _ftp_download_recursive(self, remote_path, local_dir, _depth=0):
        if _depth > 20:   # Schutz vor Symlink-Loops und pathologischen Strukturen
            return 0
        os.makedirs(local_dir, exist_ok=True)
        count = 0
        entries = list(self._ftp.mlsd(remote_path))
        for name, facts in entries:
            if name in (".", ".."):
                continue
            # Dateinamen mit Pfadtrennzeichen ablehnen (Path-Traversal-Schutz)
            if "/" in name or "\\" in name:
                self.after(0, lambda n=name: self._log(
                    f"FTP: Verdächtiger Dateiname übersprungen: {n}", "warn"))
                continue
            r_full = remote_path.rstrip("/") + "/" + name
            l_full = os.path.join(local_dir, name)
            # Sicherstellen dass der lokale Pfad innerhalb von local_dir bleibt
            if not validate_local_path(l_full, local_dir):
                self.after(0, lambda n=name: self._log(
                    f"FTP: Pfad-Traversal blockiert: {n}", "warn"))
                continue
            is_dir = facts.get("type", "file").lower() in ("dir", "cdir", "pdir")
            if is_dir:
                count += self._ftp_download_recursive(r_full, l_full, _depth + 1)
            else:
                self.after(0, lambda n=name: self._ftp_set_progress(f"⬇ {n}"))
                self._ftp_retr(r_full, l_full)
                count += 1
        return count

    # ── Backup ────────────────────────────────────────────────────────────────

    def _ftp_backup(self):
        if not self._ftp_ok():
            return
        ip         = self._ftp_ip_var.get().strip().replace(".", "-")
        dest = filedialog.asksaveasfilename(
            title="Backup speichern als...",
            initialfile=f"backup_{ip}.zip",
            defaultextension=".zip",
            initialdir=os.path.expanduser("~"),
            filetypes=[("ZIP-Archiv", "*.zip"), ("Alle Dateien", "*.*")])
        if not dest:
            return

        def do_backup():
            if not self._ftp:
                return
            tmp_dir = tempfile.mkdtemp(prefix="alphajet_backup_")
            try:
                self.after(0, lambda: self._ftp_set_progress("📦 Backup läuft..."))
                count = self._ftp_download_recursive("/", tmp_dir)
                self.after(0, lambda: self._ftp_set_progress(
                    f"📦 Packe {count} Dateien als ZIP..."))
                with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
                    for root, dirs, files in os.walk(tmp_dir):
                        for fn in files:
                            abs_path = os.path.join(root, fn)
                            zf.write(abs_path, os.path.relpath(abs_path, tmp_dir))
                self.after(0, lambda: self._log(
                    f"✅ Backup gespeichert: {dest}  ({count} Dateien)", "info"))
                self.after(0, lambda: self._ftp_set_progress(
                    f"✅ Backup gespeichert: {os.path.basename(dest)}"))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._log(f"Backup Fehler: {err}", "error"))
                self.after(0, lambda: self._ftp_set_progress("❌ Backup fehlgeschlagen"))
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        threading.Thread(target=do_backup, daemon=True).start()

    # ── Upload ────────────────────────────────────────────────────────────────

    def _ftp_remote_dir(self):
        ftype, fpath = self._ftp_selected_path()
        if ftype == "dir":
            return fpath
        if ftype == "file":
            return "/".join(fpath.split("/")[:-1]) or "/"
        return "/"

    def _ftp_mkd_safe(self, path):
        try:
            self._ftp.mkd(path)
        except ftplib.error_perm as e:
            # Verschiedene FTP-Server-Codes für "Verzeichnis existiert bereits":
            # 550 (vsftpd/alphaJET), 521 (PureFTPd), 553 (ProFTPd)
            code = str(e)[:3]
            if code not in ("550", "521", "553") and "exists" not in str(e).lower():
                raise

    def _ftp_upload(self):
        if not self._ftp_ok():
            return
        srcs = filedialog.askopenfilenames(
            title="Dateien auf Drucker hochladen",
            initialdir=os.path.expanduser("~"),
            filetypes=[("Alle Dateien", "*.*"),
                       ("Label/Config/PrintControl", "*.txt *.xml *.gp *.pcf *.ctl")])
        if not srcs:
            return
        remote_dir = self._ftp_remote_dir()
        def do_ul():
            if not self._ftp:
                return
            ok = 0
            for src in srcs:
                fn          = os.path.basename(src)
                remote_path = remote_dir.rstrip("/") + "/" + fn
                try:
                    self.after(0, lambda n=fn: self._ftp_set_progress(f"⬆ {n}"))
                    self._ftp_stor(src, remote_path)
                    ok += 1
                except Exception as e:
                    err = str(e)
                    self.after(0, lambda n=fn, er=err: self._log(
                        f"Upload Fehler ({n}): {er}", "error"))
            self.after(0, lambda: self._log(
                f"Upload abgeschlossen: {ok}/{len(srcs)} Dateien → {remote_dir}", "info"))
            self.after(0, lambda: self._ftp_set_progress(""))
            self.after(0, self._ftp_refresh)
        threading.Thread(target=do_ul, daemon=True).start()

    def _ftp_upload_folder(self):
        if not self._ftp_ok():
            return
        src_dir = filedialog.askdirectory(
            title="Ordner auf Drucker hochladen",
            initialdir=os.path.expanduser("~"))
        if not src_dir:
            return
        remote_base = self._ftp_remote_dir().rstrip("/") + "/" + os.path.basename(src_dir)
        def do_ul():
            if not self._ftp:
                return
            try:
                count = self._ftp_upload_recursive(src_dir, remote_base)
                self.after(0, lambda: self._log(
                    f"Ordner-Upload OK: {src_dir} → {remote_base} ({count} Dateien)", "info"))
                self.after(0, lambda: self._ftp_set_progress(""))
                self.after(0, self._ftp_refresh)
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._log(f"Ordner-Upload Fehler: {err}", "error"))
                self.after(0, lambda: self._ftp_set_progress(""))
        threading.Thread(target=do_ul, daemon=True).start()

    def _ftp_upload_recursive(self, local_dir, remote_dir):
        self._ftp_mkd_safe(remote_dir)
        count = 0
        for entry in sorted(os.scandir(local_dir),
                             key=lambda e: (not e.is_dir(), e.name.lower())):
            # Versteckte Dateien und Einträge mit Pfadzeichen überspringen
            if entry.name.startswith('.') or '/' in entry.name or '\\' in entry.name:
                continue
            r_path = remote_dir.rstrip("/") + "/" + entry.name
            if entry.is_dir():
                count += self._ftp_upload_recursive(entry.path, r_path)
            else:
                self.after(0, lambda n=entry.name: self._ftp_set_progress(f"⬆ {n}"))
                self._ftp_stor(entry.path, r_path)
                count += 1
        return count

    # ── Löschen ───────────────────────────────────────────────────────────────

    def _ftp_delete(self):
        if not self._ftp_ok():
            return
        ftype, fpath = self._ftp_selected_path()
        if not fpath:
            messagebox.showinfo("Hinweis", "Bitte eine Datei oder einen Ordner auswählen.")
            return
        is_dir = (ftype == "dir")
        label  = "Ordner (inkl. Inhalt)" if is_dir else "Datei"
        if not messagebox.askyesno("Löschen", f"{label} auf dem Drucker löschen?\n{fpath}"):
            return
        def do_del():
            if not self._ftp:
                return
            try:
                if is_dir:
                    self._ftp_rmdir_recursive(fpath)
                else:
                    self._ftp.delete(fpath)
                self.after(0, lambda: self._log(f"FTP gelöscht: {fpath}", "info"))
                self.after(0, self._ftp_refresh)
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._log(f"FTP Löschen Fehler: {err}", "error"))
        threading.Thread(target=do_del, daemon=True).start()

    def _ftp_rmdir_recursive(self, path):
        try:
            entries = list(self._ftp.mlsd(path))
        except Exception:
            entries = [(n, {}) for n in self._ftp.nlst(path)
                       if n not in (".", "..")]
        for name, facts in entries:
            if name in (".", ".."):
                continue
            full   = path.rstrip("/") + "/" + name
            is_dir = facts.get("type", "file").lower() in ("dir", "cdir", "pdir")
            if is_dir:
                self._ftp_rmdir_recursive(full)
            else:
                self._ftp.delete(full)
        self._ftp.rmd(path)

    # ── Lokal speichern ───────────────────────────────────────────────────────

    def _ftp_save_label(self):
        self._ftp_save_to(LABELS_DIR, "Label")

    def _ftp_save_config(self):
        self._ftp_save_to(CONFIGS_DIR, "Config")

    def _ftp_save_printctl(self):
        self._ftp_save_to(PRINTCTL_DIR, "PrintControl")

    def _ftp_save_logo(self):
        self._ftp_save_to(LOGOS_DIR, "Logo")

    def _ftp_save_to(self, dest_dir, kind):
        if not self._ftp_ok():
            return
        ftype, fpath = self._ftp_selected_path()
        if ftype != "file" or not fpath:
            messagebox.showinfo("Hinweis", "Bitte eine Datei auswählen.")
            return
        fn   = os.path.basename(fpath)
        dest = os.path.join(dest_dir, fn)
        if os.path.exists(dest):
            if not messagebox.askyesno("Überschreiben",
                                       f"'{fn}' existiert bereits lokal.\nÜberschreiben?"):
                return

        def do_dl():
            if not self._ftp:
                return
            try:
                self._ftp_retr(fpath, dest)
                self.after(0, lambda: self._log(
                    f"{kind} gespeichert: {fpath} → {dest}", "info"))
                if kind == "Label":
                    self.after(0, lambda: self._file_refresh(LABELS_DIR, "label_list", LABEL_EXTS))
                elif kind == "PrintControl":
                    self.after(0, lambda: self._file_refresh(PRINTCTL_DIR, "ctl_list", PRINTCTL_EXTS))
                elif kind == "Config":
                    self.after(0, lambda: self._file_refresh(CONFIGS_DIR, "cfg_list", CONFIG_EXTS))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._log(f"FTP Fehler: {err}", "error"))

        threading.Thread(target=do_dl, daemon=True).start()

    # ── In Editor öffnen ──────────────────────────────────────────────────────

    def _ftp_open_in_editor(self):
        if not self._ftp_ok():
            return
        ftype, fpath = self._ftp_selected_path()
        if ftype != "file" or not fpath:
            messagebox.showinfo("Hinweis", "Bitte eine Datei auswählen.")
            return
        fn  = os.path.basename(fpath)
        tmp = os.path.join(LABELS_DIR, fn)
        def do_dl():
            if not self._ftp:
                return
            try:
                self._ftp_retr(fpath, tmp)
                self.after(0, lambda: self._load_into_label_editor(tmp, fn))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._log(f"FTP Fehler: {err}", "error"))
        threading.Thread(target=do_dl, daemon=True).start()

    def _load_into_label_editor(self, path, fn):
        if not self._label_editor:
            self._log("Label Editor nicht verfügbar.", "error")
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fp:
                content = fp.read()
            from label_editor import parse_gprint_xml
            ed = self._label_editor
            ed.objects  = parse_gprint_xml(content)
            ed.selected = None
            ed.filename = fn
            ed._file_lbl.config(text=f"  {fn}")
            ed._refresh_list()
            ed._show_empty_props()
            ed._auto_detect_mode()
            ed._redraw()
            self._file_refresh(LABELS_DIR, "label_list", LABEL_EXTS)
            self._switch_to_tab("Label Editor")
            self._log(f"Label im Editor geöffnet: {fn}", "info")
        except Exception as e:
            self._log(f"Editor-Fehler: {e}", "error")

    def _ftp_open_in_logo_editor(self):
        if not self._ftp_ok():
            return
        ftype, fpath = self._ftp_selected_path()
        if ftype != "file" or not fpath:
            messagebox.showinfo("Hinweis", "Bitte eine Datei auswählen.")
            return
        fn  = os.path.basename(fpath)
        tmp = os.path.join(LOGOS_DIR, fn)
        def do_dl():
            if not self._ftp:
                return
            try:
                self._ftp_retr(fpath, tmp)
                self.after(0, lambda: self._load_into_logo_editor(tmp, fn))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._log(f"FTP Fehler: {err}", "error"))
        threading.Thread(target=do_dl, daemon=True).start()

    def _load_into_logo_editor(self, path, fn):
        if not self._logo_editor:
            self._log("Logo Editor nicht verfügbar.", "error")
            return
        try:
            ok = self._logo_editor.load_from_path(path)
            if ok:
                self._switch_to_tab("Logo Editor")
                self._log(f"Logo im Editor geöffnet: {fn}", "info")
        except Exception as e:
            self._log(f"Logo-Editor-Fehler: {e}", "error")

    def _ftp_open_in_config(self):
        if not self._ftp_ok():
            return
        ftype, fpath = self._ftp_selected_path()
        if ftype != "file" or not fpath:
            messagebox.showinfo("Hinweis", "Bitte eine Datei auswählen.")
            return
        fn  = os.path.basename(fpath)
        tmp = os.path.join(CONFIGS_DIR, fn)
        def do_dl():
            if not self._ftp:
                return
            try:
                self._ftp_retr(fpath, tmp)
                self.after(0, lambda: self._load_into_config_editor(tmp, fn))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._log(f"FTP Fehler: {err}", "error"))
        threading.Thread(target=do_dl, daemon=True).start()

    def _load_into_config_editor(self, path, fn):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fp:
                content = fp.read()
            self.cfg_name_var.set(fn)
            self.cfg_editor.delete("1.0", "end")
            self.cfg_editor.insert("end", content)
            self._file_refresh(CONFIGS_DIR, "cfg_list", CONFIG_EXTS)
            self._switch_to_tab("Configs")
            self._log(f"Config im Editor: {fn}", "info")
        except Exception as e:
            self._log(f"Fehler: {e}", "error")

    def _ftp_open_in_printctl(self):
        if not self._ftp_ok():
            return
        ftype, fpath = self._ftp_selected_path()
        if ftype != "file" or not fpath:
            messagebox.showinfo("Hinweis", "Bitte eine Datei auswählen.")
            return
        fn  = os.path.basename(fpath)
        tmp = os.path.join(PRINTCTL_DIR, fn)
        def do_dl():
            if not self._ftp:
                return
            try:
                self._ftp_retr(fpath, tmp)
                self.after(0, lambda: self._load_into_printctl_editor(tmp, fn))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._log(f"FTP Fehler: {err}", "error"))
        threading.Thread(target=do_dl, daemon=True).start()

    def _load_into_printctl_editor(self, path, fn):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fp:
                content = fp.read()
            self.ctl_name_var.set(fn)
            self.ctl_editor.delete("1.0", "end")
            self.ctl_editor.insert("end", content)
            self._file_refresh(PRINTCTL_DIR, "ctl_list", PRINTCTL_EXTS)
            self._switch_to_tab("PrintControls")
            self._log(f"PrintControl im Editor: {fn}", "info")
        except Exception as e:
            self._log(f"Fehler: {e}", "error")
