"""
alphaJET LabelEditor -- Marvin Köllner --
Steuerprogramm fuer Koenig & Bauer alphaJET Tintenstrahldrucker
Protokoll: G-PR(INT) V3.0.0
"""

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox, filedialog, simpledialog, scrolledtext
import xml.etree.ElementTree as ET
import xml.dom.minidom
import datetime
import hashlib
import os
import sys
import ctypes
import shutil
import utils
from utils import C, ToolTip, FONTS_DIR

# ─── Pfade ────────────────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Konstanten ───────────────────────────────────────────────────────────────
PRINT_MODES = {"pm05": 5, "pm07": 7, "pm15": 15, "pm24": 24, "pm32": 32, "pm48": 48}

# (height_px, approx_char_width_strokes, tk_family_name)
FONT_INFO = {
    "a7x5":    (7,   5,  "a7x5"),
    "a9x5":    (9,   6,  "a9x5"),
    "a9x6":    (9,   7,  "a9x6"),
    "a15x11":  (15,  12, "a15x11"),
    "a16x12":  (16,  13, "a16x12"),
    "a24x15":  (24,  16, "a24x15"),
    "a32x22":  (32,  23, "a32x22"),
    "m5":      (5,   5,  "m5"),
    "m5t":     (5,   5,  "m5t"),
    "m7x5":    (7,   5,  "m7x5"),
    "m7x5t":   (7,   5,  "m7x5t"),
    "m15":     (15,  11, "m15"),
    "m23":     (23,  17, "m23"),
    "m32x24":  (32,  24, "m32x24"),
    "ocr11x7": (11,  8,  "ocr11x7"),
    "default": (7,   6,  "default"),
    "Arial":   (9,  7,  "Arial"),
}
AVAILABLE_FONTS = list(FONT_INFO.keys())

BARCODE_TYPES = [
    "code128", "code128a", "code128b", "code128c",
    "ean128",  "code39",   "code93",   "qr",
    "matrix",  "dotcode",  "ean8",     "ean13",
    "upca",    "upce",     "i2of5",    "itf14",
    "codabar", "pharma",
]

# DataMatrix Groessen → (cols, rows, max_alphanum_chars)
DMC_SIZES = {
    "10x10":  (10, 10,  3),  "12x12":  (12, 12,  5),
    "14x14":  (14, 14,  8),  "16x16":  (16, 16, 12),
    "18x18":  (18, 18, 18),  "20x20":  (20, 20, 22),
    "22x22":  (22, 22, 31),  "24x24":  (24, 24, 36),
    "26x26":  (26, 26, 44),  "32x32":  (32, 32, 60),
    "36x36":  (36, 36, 80),  "40x40":  (40, 40,100),
    "8x18":   (8,  18,  5),  "8x32":   (8,  32, 11),
    "12x26":  (12, 26, 14),  "16x36":  (16, 36, 24),
}

TIME_FORMATS = [
    "%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d/%m/%Y",
    "%d.%m.%Y %H:%M", "%H:%M", "%H:%M:%S",
    "%a, %d.%m.%Y", "%a, %d.%m.%Y %H:%M",
]

# Hintergrund-Optionen: (fill, grid_step_printer_px, grid_color)
BG_OPTIONS = {
    "Weiss":             ("#ffffff", 0,  ""),
    "Raster 10px":       ("#ffffff", 10, "#e0e0e0"),
    "Raster 5px":        ("#ffffff", 5,  "#d0d0d0"),
    "Raster 2px":        ("#ffffff", 2,  "#c0c0c0"),
    "1px (Pixel-Raster)":("#ffffff", 1,  "#b8b8b8"),
    "Dunkel + 5px":      ("#1a1a2e", 5,  "#2a2a4e"),
}

OBJ_COLORS = {
    "text":    "#5a9fd4", "time":    "#52a06e",
    "counter": "#c08040", "matrix":  "#8878c0",
    "qr":      "#8878c0", "barcode": "#8878c0",
    "line":    "#3a3a3a", "rect":    "#3a3a3a",
    "ellipse": "#3a3a3a", "logo":    "#3a7a54",
}

CANVAS_PAD = 8    # top + left/right padding (kein unterer Rand)
RULER_W    = 32   # ruler width in px

# ─── Font-Pfad-Auflösung ──────────────────────────────────────────────────────

def _resolve_font_path(font_name):
    """Sucht eine TTF-Datei: erst lokaler fonts-Ordner, dann System-Fonts.
    Gibt den Pfad zurück oder None wenn nicht gefunden."""
    fonts_dir = FONTS_DIR

    # 1. Lokaler fonts-Ordner (exakt + lowercase)
    for fname in [f"{font_name}.ttf", f"{font_name.lower()}.ttf"]:
        p = os.path.join(fonts_dir, fname)
        if os.path.isfile(p):
            return p

    # 2. Windows System-Fonts
    win_root = os.environ.get("SystemRoot", r"C:\Windows")
    win_fonts = os.path.join(win_root, "Fonts")
    if os.path.isdir(win_fonts):
        for fname in [f"{font_name}.ttf", f"{font_name.lower()}.ttf",
                      f"{font_name}bd.ttf",   # z.B. arialbd.ttf
                      f"{font_name}mt.ttf"]:  # z.B. ArialMT.ttf
            p = os.path.join(win_fonts, fname)
            if os.path.isfile(p):
                return p
        # Fuzzy: erste Datei die den Namen enthält
        try:
            for fn in os.listdir(win_fonts):
                if font_name.lower() in fn.lower() and fn.lower().endswith(".ttf"):
                    return os.path.join(win_fonts, fn)
        except OSError:
            pass

    # 3. Linux/macOS System-Fonts
    for base_dir in ["/usr/share/fonts", "/usr/local/share/fonts",
                     os.path.expanduser("~/.fonts"),
                     "/Library/Fonts", "/System/Library/Fonts"]:
        if not os.path.isdir(base_dir):
            continue
        try:
            for root, _, files in os.walk(base_dir):
                for fn in files:
                    if fn.lower() == f"{font_name.lower()}.ttf":
                        return os.path.join(root, fn)
        except OSError:
            pass

    return None   # Nicht gefunden → Fallback auf Tkinter

# ─── Font-Loading ─────────────────────────────────────────────────────────────

def load_printer_fonts():
    fonts_dir = FONTS_DIR
    if not os.path.isdir(fonts_dir):
        return
    loaded = 0
    for fn in os.listdir(fonts_dir):
        if fn.lower().endswith(".ttf"):
            try:
                if ctypes.windll.gdi32.AddFontResourceW(os.path.join(fonts_dir, fn)):
                    loaded += 1
            except Exception:
                pass
    if loaded:
        try:
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x001D, 0, 0)
        except Exception:
            pass

# ─── XML-Hilfsfunktionen ──────────────────────────────────────────────────────

def _xe(text):
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))

# ─── LabelObject ──────────────────────────────────────────────────────────────

class LabelObject:
    _counter = 0

    def __init__(self, otype="text"):
        LabelObject._counter += 1
        self.id           = LabelObject._counter
        self.otype        = otype
        self.x            = 0
        self.y            = 0
        self.sw           = 1
        self.ss           = 0
        self.mag          = 1
        self.neg          = 0
        self.bwd          = 0
        self.angle        = 0
        self.idx          = None
        self.field_type   = "static"
        self.prompt_name  = ""
        self.placeholder_txt = ""
        self.text         = "Text"
        self.font_face    = "m7x5"
        self.font_size    = 7
        self.font_bold    = False
        self.font_italic  = False
        self.font_ul      = False
        self.font_gap     = 0
        self.time_fmt     = "%d.%m.%Y"
        self.exp_days     = 0
        self.exp_months   = 0
        self.exp_years    = 0
        self.rem_ldz      = 0
        self.min_clk      = 0
        self.cws_fw       = 0
        self.numb_start          = 0
        self.numb_end            = 2147483647
        self.numb_step           = 1
        self.numb_rep            = 1
        self.numb_count          = 0
        self.numb_format         = 2    # 1=Führende Leerzeichen, 2=Linksbündig
        self.numb_autostop       = 0
        self.numb_resetable      = 0
        self.numb_represetable   = 0
        self.numb_ac_enab        = 0    # Alpha-Code
        self.numb_start_pc       = 0    # Start=PC
        self.numb_use_glob_cnt   = 0    # Globalen Zähler verwenden
        self.numb_p              = 0    # Prompted (aP)
        self.numb_pvn            = ""   # Variablenname (aPvn)
        self.numb_cur_num        = 0
        self.numb_cur_rep        = 0
        self.numb_timedreset_hh  = 0
        self.numb_timedreset_mm  = 0
        self.numb_timedreset_mask = "0x0000"
        # Legacy / Vorschau
        self.numb_digits  = 4
        self.numb_fill    = "0"
        self.numb_preview = ""
        self.dmc_size     = "10x10"
        self.x2           = 60
        self.y2           = 10
        self.lw           = 1
        self.fill         = 0
        self.logo_file    = ""
        self.logo_w       = 10
        self.logo_h       = 10

    @property
    def prompted(self):
        return self.field_type == "prompted"

    def char_width(self):
        return FONT_INFO.get(self.font_face, (self.font_size, 6, self.font_face))[1]

    def char_height(self):
        # font_size aus XML (aSize) hat Vorrang — stimmt für alle Fonts,
        # auch Arial/Systemfonts wo aSize die echte Druckerhöhe in px ist.
        if self.font_size and self.font_size > 0:
            return self.font_size
        return FONT_INFO.get(self.font_face, (7, 6, "a7x5"))[0]

    def approx_width(self):
        """Breite in Strokes. cw = Zeichen inkl. Abstand. Letzter Char hat keinen Abstand."""
        cw  = self.char_width()
        gap = self.font_gap        # extra Zeichenabstand (Standard=0)
        mag = max(1, self.mag)

        def _text_w(n):
            if n <= 0:
                return 1
            # Jedes Zeichen: cw Pixel + 1 Stroke Zeichenabstand (+ optional gap).
            # Letzter Zeichenabstand entfällt (-1). Dann horizontal mit MAG gestreckt.
            return max(1, n * (cw + gap + 1) - 1) * mag

        if self.otype == "time":
            try:
                sample = datetime.datetime.now().strftime(self.time_fmt)
                return _text_w(len(sample))
            except Exception:
                return 80
        if self.otype == "counter":
            # Breite aus der Länge des Endwerts schätzen
            return _text_w(len(str(self.numb_end)))
        if self.otype in ("line", "rect", "ellipse"):
            return max(abs(self.x2 - self.x), 4)
        if self.otype == "matrix":
            return DMC_SIZES.get(self.dmc_size, (16, 16, 12))[0]
        if self.otype == "logo":
            return max(1, self.logo_w)
        if self.otype in BARCODE_TYPES:
            return max(30, len(self.text) * 4 + 20)
        return _text_w(max(1, len(self.text)))

    def approx_height(self):
        if self.otype in ("line", "rect", "ellipse"):
            return max(abs(self.y2 - self.y), 2)
        if self.otype == "matrix":
            return DMC_SIZES.get(self.dmc_size, (16, 16, 12))[1]
        if self.otype == "logo":
            return max(1, self.logo_h)
        return self.char_height()

    def dmc_overflow(self):
        if self.otype != "matrix":
            return False
        if self.field_type != "static":
            return False
        cap = DMC_SIZES.get(self.dmc_size, (16, 16, 12))[2]
        return len(self.text) > cap

    def canvas_preview_text(self):
        if self.otype == "time":
            try:
                return datetime.datetime.now().strftime(self.time_fmt)
            except Exception:
                return self.time_fmt
        if self.otype == "counter":
            return str(self.numb_start)
        if self.field_type == "datafield":
            return f"[{self.idx}]"
        if self.field_type == "prompted":
            return f"<{self.prompt_name}>"
        return self.text[:24] or "(leer)"

    def display_label(self):
        ft = {"static": "S", "datafield": f"D{self.idx}", "prompted": "P"}.get(
            self.field_type, "?")
        if self.otype == "time":
            return f"[{ft}] Datum  {self.time_fmt}"
        if self.otype == "counter":
            return f"[{ft}] Zaehler  {self.numb_start}–{self.numb_end}"
        if self.otype == "matrix":
            return f"[{ft}] DMC {self.dmc_size}  {self.text[:10]}"
        if self.otype in BARCODE_TYPES:
            return f"[{ft}] {self.otype}  {self.text[:10]}"
        if self.otype in ("line", "rect", "ellipse"):
            return f"  {self.otype}  ({self.x},{self.y})→({self.x2},{self.y2})"
        if self.otype == "logo":
            return f"  Logo  {self.logo_file or '(kein)'} {self.logo_w}×{self.logo_h}"
        return f"[{ft}]  {self.canvas_preview_text()[:20]}"

    def to_xml_lines(self):
        ln = []
        ln.append("    <OBJ>")
        real_type = "text" if self.otype in ("time", "counter") else self.otype
        ln.append(f"      <TYPE>{real_type}</TYPE>")
        ln.append(f"      <X>{self.x}</X>")
        ln.append(f"      <Y>{self.y}</Y>")
        ln.append(f"      <SW>{self.sw}</SW>")
        ln.append(f"      <SS>{self.ss}</SS>")
        ln.append(f"      <MAG>{self.mag}</MAG>")
        ln.append(f"      <NEG>{self.neg}</NEG>")
        ln.append(f"      <BWD>{self.bwd}</BWD>")
        ln.append(f"      <ANGLE>{self.angle}</ANGLE>")
        if self.idx is not None:
            ln.append(f"      <IDX>{self.idx}</IDX>")

        if self.otype == "time":
            ln.append("      <TIME>")
            ln.append(f"        <FORMAT>{_xe(self.time_fmt)}</FORMAT>")
            ln.append(f"        <EXPDAYS>{self.exp_days}</EXPDAYS>")
            ln.append(f"        <EXPMONTHS>{self.exp_months}</EXPMONTHS>")
            ln.append(f"        <EXPYEARS>{self.exp_years}</EXPYEARS>")
            ln.append(f"        <REMLDZ>{self.rem_ldz}</REMLDZ>")
            ln.append(f"        <MINCLK>{self.min_clk}</MINCLK>")
            ln.append(f"        <CWSFW>{self.cws_fw}</CWSFW>")
            ln.append("      </TIME>")
        elif self.otype == "counter":
            numb_attrs = ""
            if self.numb_p:
                numb_attrs = (f' aP="1" aPvn="{_xe(self.numb_pvn)}"'
                              f' aCurNum="{self.numb_cur_num}" aCurRep="{self.numb_cur_rep}"')
            ln.append(f"      <NUMB{numb_attrs}>")
            ln.append(f"        <FORMAT>{self.numb_format}</FORMAT>")
            ln.append(f"        <AUTOSTOP>{self.numb_autostop}</AUTOSTOP>")
            ln.append(f"        <RESETABLE>{self.numb_resetable}</RESETABLE>")
            ln.append(f"        <REPRESETABLE>{self.numb_represetable}</REPRESETABLE>")
            ln.append(f'        <START aStartPC="{self.numb_start_pc}" '
                      f'aUseGlobCnt="{self.numb_use_glob_cnt}">'
                      f'{self.numb_start}</START>')
            ln.append(f"        <END>{self.numb_end}</END>")
            ln.append(f"        <STEP>{self.numb_step}</STEP>")
            ln.append(f"        <REP>{self.numb_rep}</REP>")
            ln.append(f"        <COUNT>{self.numb_count}</COUNT>")
            ln.append(f'        <AC aEnab="{self.numb_ac_enab}"/>')
            ln.append(f'        <TIMEDRESET aHH="{self.numb_timedreset_hh}"'
                      f' aMM="{self.numb_timedreset_mm}"'
                      f' aMask="{self.numb_timedreset_mask}"/>')
            ln.append("      </NUMB>")
        elif self.otype == "logo":
            ln.append(f"      <TEXT>{_xe(self.logo_file)}</TEXT>")
            ln.append(f"      <LWIDTH>{self.logo_w}</LWIDTH>")
            ln.append(f"      <LHEIGHT>{self.logo_h}</LHEIGHT>")
        elif self.otype not in ("line", "rect", "ellipse"):
            if self.field_type == "prompted":
                ln.append(f'      <TEXT aP="1" aPvn="{_xe(self.prompt_name)}">{_xe(self.text)}</TEXT>')
            else:
                ln.append(f"      <TEXT>{_xe(self.text)}</TEXT>")

        # FONT
        if self.otype not in ("line", "rect", "ellipse", "logo"):
            fa = f'aFace="{self.font_face}" aSize="{self.font_size}"'
            if self.font_bold:   fa += ' aBld="1"'
            if self.font_italic: fa += ' aIt="1"'
            if self.font_ul:     fa += ' aUl="1"'
            if self.font_gap:    fa += f' aGap="{self.font_gap}"'
            ln.append(f"      <FONT {fa}/>")
            # DMC-spezifisch
            if self.otype == "matrix":
                c, r, _ = DMC_SIZES.get(self.dmc_size, (16, 16, 12))
                ln.append(f"      <MXCOLS>{c}</MXCOLS>")
                ln.append(f"      <MXROWS>{r}</MXROWS>")
        else:
            ln.append(f"      <X2>{self.x2}</X2>")
            ln.append(f"      <Y2>{self.y2}</Y2>")
            ln.append(f"      <LW>{self.lw}</LW>")
            ln.append(f"      <FILL>{self.fill}</FILL>")

        ln.append("    </OBJ>")
        return ln


def objects_to_gprint_xml(objects):
    lines = ["<GP>", "  <LAB>"]
    for obj in objects:
        lines.extend(obj.to_xml_lines())
    lines += ["  </LAB>", "</GP>"]
    return "\n".join(lines)


def parse_gprint_xml(xml_string):
    objects = []
    root = ET.fromstring(xml_string.strip())
    lab  = root.find("LAB") if root.tag == "GP" else root
    if lab is None:
        lab = root
    for oe in lab.findall("OBJ"):
        obj       = LabelObject()
        otype_raw = (oe.findtext("TYPE") or "text").lower()
        obj.otype = otype_raw
        obj.x     = int(oe.findtext("X") or 0)
        obj.y     = int(oe.findtext("Y") or 0)
        obj.sw    = int(oe.findtext("SW") or 1)
        obj.ss    = int(oe.findtext("SS") or 0)
        obj.mag   = int(oe.findtext("MAG") or 1)
        obj.neg   = int(oe.findtext("NEG") or 0)
        obj.bwd   = int(oe.findtext("BWD") or 0)
        obj.angle = int(oe.findtext("ANGLE") or 0)
        idx_text  = oe.findtext("IDX")
        if idx_text:
            obj.idx        = int(idx_text)
            obj.field_type = "datafield"

        te = oe.find("TIME")
        if te is not None:
            obj.otype      = "time"
            obj.time_fmt   = te.findtext("FORMAT") or "%d.%m.%Y"
            obj.exp_days   = int(te.findtext("EXPDAYS")   or 0)
            obj.exp_months = int(te.findtext("EXPMONTHS") or 0)
            obj.exp_years  = int(te.findtext("EXPYEARS")  or 0)
            obj.rem_ldz    = int(te.findtext("REMLDZ")    or 0)
            obj.min_clk    = int(te.findtext("MINCLK")    or 0)
            obj.cws_fw     = int(te.findtext("CWSFW")     or 0)

        ne = oe.find("NUMB")
        if ne is not None:
            obj.otype = "counter"
            # Prompted-Attribute am NUMB-Tag
            obj.numb_p       = int(ne.get("aP",       0))
            obj.numb_pvn     = ne.get("aPvn",  "")
            obj.numb_cur_num = int(ne.get("aCurNum", 0))
            obj.numb_cur_rep = int(ne.get("aCurRep", 0))
            # Child-Elemente (neues Format vom Gerät)
            fmt_e = ne.find("FORMAT")
            if fmt_e is not None:
                obj.numb_format       = int(fmt_e.text or 2)
                obj.numb_autostop     = int((ne.findtext("AUTOSTOP")    or "0"))
                obj.numb_resetable    = int((ne.findtext("RESETABLE")   or "0"))
                obj.numb_represetable = int((ne.findtext("REPRESETABLE") or "0"))
                start_e = ne.find("START")
                if start_e is not None:
                    obj.numb_start        = int(start_e.text or 0)
                    obj.numb_start_pc     = int(start_e.get("aStartPC",    0))
                    obj.numb_use_glob_cnt = int(start_e.get("aUseGlobCnt", 0))
                obj.numb_end   = int(ne.findtext("END")   or 2147483647)
                obj.numb_step  = int(ne.findtext("STEP")  or 1)
                obj.numb_rep   = int(ne.findtext("REP")   or 1)
                obj.numb_count = int(ne.findtext("COUNT") or 0)
                ac_e = ne.find("AC")
                if ac_e is not None:
                    obj.numb_ac_enab = int(ac_e.get("aEnab", 0))
                tr_e = ne.find("TIMEDRESET")
                if tr_e is not None:
                    obj.numb_timedreset_hh   = int(tr_e.get("aHH",  0))
                    obj.numb_timedreset_mm   = int(tr_e.get("aMM",  0))
                    obj.numb_timedreset_mask = tr_e.get("aMask", "0x0000")
            else:
                # Legacy-Attribut-Format (Rückwärtskompatibilität)
                obj.numb_start  = int(ne.get("aStart", 0))
                obj.numb_end    = int(ne.get("aEnd",   2147483647))
                obj.numb_step   = int(ne.get("aStep",  1))
                obj.numb_digits = int(ne.get("aDig",   4))

        txe = oe.find("TEXT")
        if txe is not None and obj.otype not in ("time", "counter"):
            obj.text = txe.text or ""
            if txe.get("aP") == "1":
                obj.field_type  = "prompted"
                obj.prompt_name = txe.get("aPvn", "")

        fe = oe.find("FONT")
        if fe is not None:
            obj.font_face   = fe.get("aFace", "a7x5")
            obj.font_size   = int(fe.get("aSize", 7))
            obj.font_bold   = fe.get("aBld", "0") == "1"
            obj.font_italic = fe.get("aIt",  "0") == "1"
            obj.font_ul     = fe.get("aUl",  "0") == "1"
            obj.font_gap    = int(fe.get("aGap", 0))

        # DMC-Groesse aus MXCOLS/MXROWS
        if obj.otype == "matrix":
            mc = oe.findtext("MXCOLS")
            mr = oe.findtext("MXROWS")
            if mc and mr:
                key = f"{mc}x{mr}"
                if key in DMC_SIZES:
                    obj.dmc_size = key

        if obj.otype == "logo":
            txe2 = oe.find("TEXT")
            if txe2 is not None:
                obj.logo_file = txe2.text or ""
            obj.logo_w = int(oe.findtext("LWIDTH")  or 32)
            obj.logo_h = int(oe.findtext("LHEIGHT") or 16)

        if obj.otype in ("line", "rect", "ellipse"):
            obj.x2   = int(oe.findtext("X2")   or 60)
            obj.y2   = int(oe.findtext("Y2")   or 10)
            obj.lw   = int(oe.findtext("LW")   or 1)
            obj.fill = int(oe.findtext("FILL") or 0)

        objects.append(obj)
    return objects


# ─── Dialog: Feld-Typ wählen ─────────────────────────────────────────────────

class FieldTypeDialog(tk.Toplevel):
    """Erscheint beim Hinzufuegen eines Objekts: Statisch / Datenfeld / Prompted."""

    def __init__(self, parent, suggest_idx=1, show_for=None):
        super().__init__(parent)
        self.title("Feld-Typ waehlen")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(bg=utils.C["surface"])
        self.result = None

        self.geometry(
            f"+{parent.winfo_rootx()+parent.winfo_width()//2-200}"
            f"+{parent.winfo_rooty()+parent.winfo_height()//2-140}")

        tk.Label(self, text="  Feld-Typ des Objekts",
                 bg=utils.C["header"], fg=utils.C["accent"],
                 font=("Segoe UI", 11, "bold"),
                 anchor="w").pack(fill="x", ipady=8)

        body = tk.Frame(self, bg=utils.C["surface"])
        body.pack(fill="both", padx=14, pady=10)

        self._type_var = tk.StringVar(value="static")
        options = [
            ("static",    "Statisch",   "Fester Inhalt — aendert sich nie"),
            ("datafield", "Datenfeld",  "Wird per DSET-Befehl befuellt"),
            ("prompted",  "Prompted",   "Beim Laden wird nach dem Inhalt gefragt"),
        ]

        for val, name, desc in options:
            row = tk.Frame(body, bg=utils.C["surface"])
            row.pack(fill="x", pady=3)
            tk.Radiobutton(
                row, variable=self._type_var, value=val,
                bg=utils.C["surface"], fg=utils.C["text"],
                activebackground=utils.C["surface"], selectcolor=utils.C["border"],
                command=self._refresh_sub).pack(side="left")
            tk.Label(row, text=name, bg=utils.C["surface"], fg=utils.C["text"],
                     font=("Segoe UI", 10, "bold"), width=12,
                     anchor="w").pack(side="left")
            tk.Label(row, text=desc, bg=utils.C["surface"], fg=utils.C["subtext"],
                     font=("Segoe UI", 9), anchor="w").pack(side="left")

        self._sub = tk.Frame(body, bg=utils.C["surface2"])
        self._sub.pack(fill="x", pady=(8, 0), ipady=6)

        self._idx_var  = tk.StringVar(value=str(suggest_idx))
        self._name_var = tk.StringVar(value=f"Variable_{suggest_idx}")
        self._refresh_sub()

        btn_row = tk.Frame(self, bg=utils.C["surface"])
        btn_row.pack(fill="x", padx=14, pady=(0, 12))
        tk.Button(btn_row, text="  Hinzufuegen",
                  bg=utils.C["green"], fg=utils.C["header"],
                  font=("Segoe UI", 9, "bold"),
                  relief="flat", padx=14, pady=6, cursor="hand2",
                  command=self._ok).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="  Abbrechen",
                  bg=utils.C["border"], fg=utils.C["text"],
                  font=("Segoe UI", 9), relief="flat", padx=14, pady=6,
                  cursor="hand2", command=self.destroy).pack(side="left")

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.wait_window()

    def _refresh_sub(self):
        for w in self._sub.winfo_children():
            w.destroy()
        t = self._type_var.get()
        if t == "static":
            tk.Label(self._sub,
                     text="  Kein Index, kein Name erforderlich.",
                     bg=utils.C["surface2"], fg=utils.C["subtext"],
                     font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=4)
        elif t == "datafield":
            row = tk.Frame(self._sub, bg=utils.C["surface2"])
            row.pack(fill="x", padx=10, pady=4)
            tk.Label(row, text="Feld-Index:", bg=utils.C["surface2"], fg=utils.C["text"],
                     font=("Segoe UI", 9)).pack(side="left", padx=(0, 8))
            ttk.Entry(row, textvariable=self._idx_var, width=5).pack(side="left")
            tk.Label(row, text="(automatisch; bearbeitbar)",
                     bg=utils.C["surface2"], fg=utils.C["subtext"],
                     font=("Segoe UI", 8)).pack(side="left", padx=8)
        elif t == "prompted":
            row = tk.Frame(self._sub, bg=utils.C["surface2"])
            row.pack(fill="x", padx=10, pady=4)
            tk.Label(row, text="Variablenname:", bg=utils.C["surface2"], fg=utils.C["text"],
                     font=("Segoe UI", 9)).pack(side="left", padx=(0, 8))
            ttk.Entry(row, textvariable=self._name_var, width=20).pack(side="left")

    def _ok(self):
        try:
            idx = int(self._idx_var.get())
        except ValueError:
            idx = 1
        self.result = {
            "type": self._type_var.get(),
            "idx":  idx,
            "name": self._name_var.get().strip() or "Variable",
        }
        self.destroy()


# ─── Label Editor Tab ─────────────────────────────────────────────────────────

class LabelEditorTab:
    def __init__(self, parent, labels_dir, run_cmd_fn, log_fn):
        self.parent     = parent
        self.labels_dir = labels_dir
        self.run_cmd    = run_cmd_fn
        self.log        = log_fn

        self.objects    = []
        self.selected   = None
        self.filename   = ""
        self._drag_data = None
        self._resize_mode = False
        self._next_idx  = 1
        self._undo_stack    = []
        self._redo_stack    = []
        self._restoring     = False
        self._render_cache: dict = {}   # (fp, cell_h, preview, mag, mode, color) → PhotoImage

        import threading as _threading
        _threading.Thread(target=load_printer_fonts, daemon=True).start()
        self._build()
        self._push_undo()

    def _build(self):
        f = self.parent

        tb = tk.Frame(f, bg=utils.C["header"])
        tb.pack(fill="x")
        self._build_toolbar(tb)

        main = tk.Frame(f, bg=utils.C["surface"])
        main.pack(fill="both", expand=True)

        left = tk.Frame(main, bg=utils.C["surface"], width=240)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        self._build_left(left)

        mid = tk.Frame(main, bg=utils.C["bg"])
        mid.pack(side="left", fill="both", expand=True)
        self._build_canvas(mid)

        right = tk.Frame(main, bg=utils.C["surface"], width=240)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        self._build_props_area(right)

        self._build_xml_bar(f)
        self._redraw()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_toolbar(self, tb):
        def lbl(text):
            tk.Label(tb, text=text, bg=utils.C["header"], fg=utils.C["subtext"],
                     font=("Segoe UI", 9)).pack(side="left", padx=(8, 3), pady=7)

        lbl("Printmode:")
        self._pm_var = tk.StringVar(value="pm32")
        pm = ttk.Combobox(tb, textvariable=self._pm_var,
                          values=list(PRINT_MODES.keys()), width=7, state="readonly")
        pm.pack(side="left", padx=(0, 8))
        pm.bind("<<ComboboxSelected>>", lambda e: self._redraw())

        lbl("Breite:")
        self._w_var = tk.StringVar(value="512")
        ttk.Entry(tb, textvariable=self._w_var, width=6).pack(side="left", padx=(0, 8))
        self._w_var.trace_add("write", lambda *_: self._redraw())

        lbl("Zoom:")
        self._zoom_var = tk.StringVar(value="4x")
        zc = ttk.Combobox(tb, textvariable=self._zoom_var,
                          values=["1x","2x","3x","4x","5x","6x","8x",
                                  "10x","12x","16x","20x","24x","32x"],
                          width=4, state="readonly")
        zc.pack(side="left", padx=(0, 8))
        zc.bind("<<ComboboxSelected>>", lambda e: self._redraw())

        lbl("Hintergrund:")
        self._bg_var = tk.StringVar(value="Raster 5px")
        bg_cb = ttk.Combobox(tb, textvariable=self._bg_var,
                             values=list(BG_OPTIONS.keys()), width=16, state="readonly")
        bg_cb.pack(side="left", padx=(0, 8))
        bg_cb.bind("<<ComboboxSelected>>", lambda e: self._redraw())

        ttk.Button(tb, text="↶", width=3, command=self._undo).pack(
            side="left", padx=(8, 1), pady=4)
        ttk.Button(tb, text="↷", width=3, command=self._redo).pack(
            side="left", padx=(1, 8), pady=4)

        for txt, style, cmd in [
            ("  Neu",                    "TButton",        self._new_label),
            ("  Oeffnen",               "Blue.TButton",   self._open_label),
            ("  Speichern",             "Green.TButton",  self._save_label),
        ]:
            ttk.Button(tb, text=txt, style=style, command=cmd).pack(
                side="left", padx=2, pady=4)

        self._file_lbl = tk.Label(tb, text="", bg=utils.C["header"],
                                   fg=utils.C["subtext"], font=("Segoe UI", 8))
        self._file_lbl.pack(side="left", padx=8)

    def _redraw(self):
        z  = self._zoom()
        ph = self._ph()
        pw = self._pw()
        bg_key  = self._bg_var.get() if hasattr(self, "_bg_var") else "Weiss"
        bg_fill, grid_step, grid_color = BG_OPTIONS.get(bg_key, ("#ffffff", 0, ""))

        # Cache leeren wenn Zoom geändert (cell_h wäre anders → alte Einträge nutzlos)
        if getattr(self, "_last_zoom", None) != z:
            self._render_cache.clear()
            self._last_zoom = z

        total_w = RULER_W + CANVAS_PAD * 2 + pw * z
        total_h = CANVAS_PAD + ph * z + CANVAS_PAD

        self._cv.delete("all")
        self._photo_refs = []
        self._cv.config(scrollregion=(0, 0, total_w + 20, total_h + 2))

        lx1 = RULER_W + CANVAS_PAD
        ly1 = CANVAS_PAD
        lx2 = lx1 + pw * z
        ly2 = ly1 + ph * z
        self._cv.create_rectangle(lx1, ly1, lx2, ly2,
                                   fill=bg_fill, outline="#888888", width=1)

        if grid_step > 0 and grid_color:
            for gx in range(0, pw + 1, grid_step):
                x = lx1 + gx * z
                self._cv.create_line(x, ly1, x, ly2, fill=grid_color, width=1)
            for gy in range(0, ph + 1, grid_step):
                y = ly2 - gy * z
                self._cv.create_line(lx1, y, lx2, y, fill=grid_color, width=1)

        for gy in range(0, ph + 1, max(1, 5 // z if z < 3 else 5)):
            y = ly2 - gy * z
            self._cv.create_line(RULER_W, y, lx1, y, fill="#555555", width=1)
            self._cv.create_text(RULER_W - 2, y, text=str(gy),
                                  fill="#888888", font=("Segoe UI", 7), anchor="e")

        for gx in range(0, pw + 1, 10):
            x = lx1 + gx * z
            self._cv.create_line(x, ly1, x, ly1 - 4, fill="#555555", width=1)
            self._cv.create_text(x, ly1 - 8, text=str(gx),
                                  fill="#888888", font=("Segoe UI", 7))

        for obj in self.objects:
            self._draw_obj(obj)

        if self.selected:
            self._cv.tag_raise(f"obj{self.selected.id}_s")

        self._update_xml()

    def _build_left(self, left):
        tk.Label(left, text="Objekt hinzufuegen",
                 bg=utils.C["surface"], fg=utils.C["accent"],
                 font=("Segoe UI", 9, "bold")).pack(padx=8, pady=(10, 4))

        add_btns = [
            ("T   Text",          "text"),
            ("    Datum / Zeit",   "time"),
            ("#   Zaehler",        "counter"),
            ("    DMC (Matrix)",   "matrix"),
            ("    Barcode / QR",   "barcode"),
            ("    Logo",           "logo"),
            ("--- Linie",          "line"),
            ("[_] Rechteck",       "rect"),
        ]
        for lbl, atype in add_btns:
            ttk.Button(left, text=lbl, width=20,
                       command=lambda t=atype: self._add_object(t)
                       ).pack(padx=8, pady=2, fill="x")

        tk.Frame(left, bg=utils.C["border"], height=1).pack(fill="x", pady=8, padx=8)

        tk.Label(left, text="Objekte",
                 bg=utils.C["surface"], fg=utils.C["accent"],
                 font=("Segoe UI", 9, "bold")).pack(padx=8, pady=(0, 4))

        self._obj_lb = tk.Listbox(
            left, bg=utils.C["surface2"], fg=utils.C["text"],
            selectbackground=utils.C["accent"], selectforeground=utils.C["header"],
            font=("Segoe UI", 8), activestyle="none",
            relief="flat", bd=0, highlightthickness=0)
        self._obj_lb.pack(padx=8, fill="both", expand=True)
        self._obj_lb.bind("<<ListboxSelect>>", self._on_list_select)

        btn_row = tk.Frame(left, bg=utils.C["surface"])
        btn_row.pack(fill="x", padx=8, pady=6)
        ttk.Button(btn_row, text="↑", width=3,
                   command=self._obj_up).pack(side="left", padx=(0, 2))
        ttk.Button(btn_row, text="↓", width=3,
                   command=self._obj_down).pack(side="left", padx=(0, 4))
        ttk.Button(btn_row, text="Loeschen", style="Red.TButton",
                   command=self._delete_obj).pack(side="left", fill="x", expand=True)

        # ── Objekt-Operationen ──
        tk.Frame(left, bg=utils.C["border"], height=1).pack(fill="x", pady=4, padx=8)
        tk.Label(left, text="Objekt-Operationen",
                 bg=utils.C["surface"], fg=utils.C["accent"],
                 font=("Segoe UI", 9, "bold")).pack(padx=8, pady=(0, 3))

        op_row1 = tk.Frame(left, bg=utils.C["surface"])
        op_row1.pack(fill="x", padx=8, pady=1)
        ttk.Button(op_row1, text="Duplizieren", width=12,
                   command=self._duplicate_obj).pack(side="left", padx=(0, 2))
        ttk.Button(op_row1, text="◄► Spiegeln", width=12,
                   command=self._mirror_obj).pack(side="left")

        op_row2 = tk.Frame(left, bg=utils.C["surface"])
        op_row2.pack(fill="x", padx=8, pady=1)
        tk.Label(op_row2, text="Breite:", bg=utils.C["surface"], fg=utils.C["subtext"],
                 font=("Segoe UI", 8)).pack(side="left")
        ttk.Button(op_row2, text="1×", width=4,
                   command=lambda: self._set_mag(1)).pack(side="left", padx=1)
        ttk.Button(op_row2, text="2×", width=4,
                   command=lambda: self._set_mag(2)).pack(side="left", padx=1)
        ttk.Button(op_row2, text="3×", width=4,
                   command=lambda: self._set_mag(3)).pack(side="left", padx=1)
        ttk.Button(op_row2, text="4×", width=4,
                   command=lambda: self._set_mag(4)).pack(side="left", padx=1)

        op_row3 = tk.Frame(left, bg=utils.C["surface"])
        op_row3.pack(fill="x", padx=8, pady=1)
        tk.Label(op_row3, text="Ausrichten:", bg=utils.C["surface"], fg=utils.C["subtext"],
                 font=("Segoe UI", 8)).pack(side="left")
        for sym, cmd in [("←", self._align_left), ("→", self._align_right),
                          ("↑", self._align_top),  ("↓", self._align_bottom)]:
            ttk.Button(op_row3, text=sym, width=3, command=cmd).pack(side="left", padx=1)

        op_row4 = tk.Frame(left, bg=utils.C["surface"])
        op_row4.pack(fill="x", padx=8, pady=1)
        ttk.Button(op_row4, text="H-Zentrieren", width=14,
                   command=self._center_h).pack(side="left", padx=(0, 2))
        ttk.Button(op_row4, text="V-Zentrieren", width=14,
                   command=self._center_v).pack(side="left")

        op_row5 = tk.Frame(left, bg=utils.C["surface"])
        op_row5.pack(fill="x", padx=8, pady=1)
        tk.Label(op_row5, text="Drehen:", bg=utils.C["surface"], fg=utils.C["subtext"],
                 font=("Segoe UI", 8)).pack(side="left")
        for lbl, deg in [("↺ 90°", 90), ("180°", 180), ("↻ 90°", -90), ("0°", 0)]:
            ttk.Button(op_row5, text=lbl, width=5,
                       command=lambda d=deg: self._rotate_obj(d)
                       ).pack(side="left", padx=1)

        # ── Objekt-Info-Box ──
        info_lf = ttk.LabelFrame(left, text="  Objekt-Info")
        info_lf.pack(fill="x", padx=8, pady=(4, 8))

        self._info_h = tk.Label(info_lf, text="H:  —",
                                 bg=utils.C["surface"], fg=utils.C["text"],
                                 font=("Consolas", 10, "bold"), anchor="w")
        self._info_h.pack(fill="x", padx=8, pady=(4, 1))

        self._info_w = tk.Label(info_lf, text="B:  —",
                                 bg=utils.C["surface"], fg=utils.C["text"],
                                 font=("Consolas", 10, "bold"), anchor="w")
        self._info_w.pack(fill="x", padx=8, pady=(1, 2))

        self._info_type = tk.Label(info_lf, text="",
                                    bg=utils.C["surface"], fg=utils.C["subtext"],
                                    font=("Segoe UI", 8), anchor="w")
        self._info_type.pack(fill="x", padx=8, pady=(0, 4))

    def _ensure_logo_in_dir(self, full_path):
        """Kopiert Logo-Datei in res/logos/ falls noch nicht dort. Gibt Ziel-Basename zurück."""
        logos_dir = os.path.join(BASE_DIR, "res", "logos")
        os.makedirs(logos_dir, exist_ok=True)
        dst = os.path.join(logos_dir, os.path.basename(full_path))
        try:
            if os.path.abspath(full_path) != os.path.abspath(dst):
                shutil.copy2(full_path, dst)
        except Exception as e:
            self.log(f"Logo kopieren fehlgeschlagen: {e}", "error")
        return os.path.basename(full_path)

    def _read_logo_dims(self, obj, full_path):
        """Liest Breite/Höhe aus einem Logo-File und setzt logo_w/logo_h."""
        ext = os.path.splitext(full_path)[1].lower()
        if ext == ".svg":
            try:
                import xml.etree.ElementTree as ET
                root = ET.parse(full_path).getroot()
                vb = root.get("viewBox", "")
                if vb:
                    p = vb.split()
                    obj.logo_w = max(1, int(float(p[2])))
                    obj.logo_h = max(1, int(float(p[3])))
                else:
                    w = root.get("width", ""); h = root.get("height", "")
                    if w: obj.logo_w = max(1, int(float(w.replace("px", ""))))
                    if h: obj.logo_h = max(1, int(float(h.replace("px", ""))))
            except Exception:
                pass
        elif ext == ".mlg":
            try:
                _, mlg_w, mlg_h = LogoEditorTab._mlg_decode(full_path, hint_h=self._ph())
                obj.logo_w = mlg_w
                obj.logo_h = mlg_h
            except Exception:
                pass
        else:
            try:
                from PIL import Image
                with Image.open(full_path) as img:
                    obj.logo_w = img.width
                    obj.logo_h = img.height
            except Exception:
                pass

    def _add_logo_object(self):
        """Dialog: Logo statisch oder Datenfeld."""
        dlg = tk.Toplevel(self.parent)
        dlg.title("Logo hinzufügen")
        dlg.resizable(False, False)
        dlg.transient(self.parent)
        dlg.grab_set()
        dlg.configure(bg=utils.C["surface"])
        dlg.geometry(
            f"+{self.parent.winfo_rootx()+self.parent.winfo_width()//2-210}"
            f"+{self.parent.winfo_rooty()+self.parent.winfo_height()//2-130}")

        tk.Frame(dlg, bg=utils.C["accent"], height=3).pack(fill="x")
        tk.Label(dlg, text="  Logo hinzufügen",
                 bg=utils.C["surface"], fg=utils.C["accent"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=(10, 6))

        result = {}

        def do_static():
            path = filedialog.askopenfilename(
                title="Logo-Datei wählen",
                initialdir=os.path.join(BASE_DIR, "res", "logos"),
                filetypes=[("Logo", "*.svg *.bmp *.png *.mlg"),
                           ("Alle", "*.*")])
            if not path:
                return
            result["type"]      = "static"
            result["logo_file"] = self._ensure_logo_in_dir(path)
            result["full_path"] = os.path.join(BASE_DIR, "res", "logos", os.path.basename(path))
            dlg.destroy()

        def do_datafield():
            result["type"]      = "datafield"
            result["logo_file"] = ""
            dlg.destroy()

        body = tk.Frame(dlg, bg=utils.C["surface"])
        body.pack(fill="both", padx=14, pady=6)
        ttk.Button(body, text="📁  Statisches Logo (Datei wählen)",
                   style="Green.TButton",
                   command=do_static).pack(fill="x", pady=4)
        ttk.Button(body, text="D   Datenfeld-Logo (Datei kommt per DSET)",
                   command=do_datafield).pack(fill="x", pady=4)
        ttk.Button(body, text="  Abbrechen",
                   command=dlg.destroy).pack(fill="x", pady=(8, 4))

        dlg.wait_window()
        if not result:
            return

        obj = LabelObject("logo")
        obj.logo_file = result.get("logo_file", "")
        obj.logo_w    = 32
        obj.logo_h    = self._ph()

        # Dimensionen aus Datei auslesen (SVG, PNG, BMP, ...)
        full = result.get("full_path", "")
        if full and os.path.exists(full):
            self._read_logo_dims(obj, full)

        if result["type"] == "datafield":
            obj.field_type = "datafield"
            used = {o.idx for o in self.objects if o.idx is not None}
            idx = 1
            while idx in used:
                idx += 1
            obj.idx = idx

        if self.objects:
            obj.x = self.objects[-1].x + 5
        self.objects.append(obj)
        self._refresh_list()
        self._select(obj)

    # ── Undo / Redo ────────────────────────────────────────────────────────────

    def _snapshot(self):
        """Serialisiert den aktuellen Objektzustand als XML-String."""
        return objects_to_gprint_xml(self.objects)

    def _push_undo(self):
        if self._restoring:
            return
        snap = self._snapshot()
        if self._undo_stack and self._undo_stack[-1] == snap:
            return
        self._undo_stack.append(snap)
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _undo(self, _=None):
        if len(self._undo_stack) < 2:
            return
        self._redo_stack.append(self._undo_stack.pop())
        self._restore(self._undo_stack[-1])

    def _redo(self, _=None):
        if not self._redo_stack:
            return
        snap = self._redo_stack.pop()
        self._undo_stack.append(snap)
        self._restore(snap)

    def _restore(self, snap):
        self._restoring = True
        try:
            self.objects  = parse_gprint_xml(snap)
            self.selected = None
            self._refresh_list()
            self._show_empty_props()
            self._redraw()
        except Exception:
            pass
        finally:
            self._restoring = False

    def _duplicate_obj(self):
        if not self.selected:
            return
        import copy
        new_obj = copy.deepcopy(self.selected)
        LabelObject._counter += 1
        new_obj.id = LabelObject._counter
        new_obj.x += 5
        new_obj.y = max(0, new_obj.y - 2)
        self.objects.append(new_obj)
        self._refresh_list()
        self._select(new_obj)
        self._push_undo()

    def _mirror_obj(self):
        if not self.selected:
            return
        obj = self.selected
        obj.bwd = 0 if obj.bwd else 1
        self._redraw()
        self._show_props(obj)

    def _set_mag(self, mag):
        if not self.selected:
            return
        obj = self.selected
        if obj.otype in ("line", "rect", "ellipse", "matrix"):
            return
        obj.mag = mag
        self._redraw()
        self._show_props(obj)

    def _align_left(self):
        if self.selected:
            self.selected.x = 0
            self._redraw(); self._sync_pos_fields()

    def _align_right(self):
        if self.selected:
            self.selected.x = max(0, self._pw() - self.selected.approx_width())
            self._redraw(); self._sync_pos_fields()

    def _align_top(self):
        if self.selected:
            ph = self._ph()
            self.selected.y = ph - self.selected.approx_height() - 1
            self._redraw(); self._sync_pos_fields()

    def _align_bottom(self):
        if self.selected:
            self.selected.y = 0
            self._redraw(); self._sync_pos_fields()

    def _rotate_obj(self, deg):
        if not self.selected:
            return
        obj = self.selected
        if deg == 0:
            obj.angle = 0
        else:
            obj.angle = (obj.angle + deg) % 360
        self._redraw()
        self._show_props(obj)

    def _center_h(self):
        if self.selected:
            self.selected.x = (self._pw() - self.selected.approx_width()) // 2
            self._redraw(); self._sync_pos_fields()

    def _center_v(self):
        if self.selected:
            ph = self._ph()
            self.selected.y = (ph - self.selected.approx_height()) // 2
            self._redraw(); self._sync_pos_fields()

    def _update_info_box(self, obj):
        if obj is None:
            self._info_h.config(text="H:  —")
            self._info_w.config(text="B:  —")
            self._info_type.config(text="")
            return
        h = obj.approx_height()
        w = obj.approx_width()
        self._info_h.config(text=f"H:  {h} px")
        self._info_w.config(text=f"B:  {w} Strokes")
        # Typ-Detail
        if obj.otype in FONT_INFO:
            detail = f"{obj.font_face}  ({h}x{obj.char_width()})"
        elif obj.otype == "matrix":
            c, r, _ = DMC_SIZES.get(obj.dmc_size, (16, 16, 12))
            detail = f"DMC {c}x{r} px"
        elif obj.otype in ("line", "rect", "ellipse"):
            detail = obj.otype
        else:
            detail = obj.font_face
        ft_map = {"static": "Statisch", "datafield": f"Datenfeld (D{obj.idx})",
                  "prompted": f"Prompted ({obj.prompt_name})"}
        self._info_type.config(text=f"{detail}  ·  {ft_map.get(obj.field_type,'')}")

    def _build_canvas(self, mid):
        # Scrollbars
        h_sb = ttk.Scrollbar(mid, orient="horizontal")
        h_sb.pack(side="bottom", fill="x")
        v_sb = ttk.Scrollbar(mid, orient="vertical")
        v_sb.pack(side="right", fill="y")

        self._cv = tk.Canvas(
            mid, bg=utils.C["bg"], highlightthickness=0,
            xscrollcommand=h_sb.set, yscrollcommand=v_sb.set,
            cursor="crosshair")
        self._cv.pack(fill="both", expand=True)
        h_sb.config(command=self._cv.xview)
        v_sb.config(command=self._cv.yview)

        self._cv.bind("<Button-1>",        self._cv_click)
        self._cv.bind("<B1-Motion>",       self._cv_drag)
        self._cv.bind("<ButtonRelease-1>", self._cv_release)
        self._cv.bind("<Double-Button-1>", self._cv_dblclick)
        self._cv.bind("<Motion>",          self._cv_hover)
        self._cv.bind("<Left>",  lambda e: self._arrow_move(-1,  0))
        self._cv.bind("<Right>", lambda e: self._arrow_move( 1,  0))
        self._cv.bind("<Up>",    lambda e: self._arrow_move( 0,  1))
        self._cv.bind("<Down>",  lambda e: self._arrow_move( 0, -1))
        self._cv.bind("<Button-1>", self._cv_click_focus, add=True)
        # Mausrad: vertikal scrollen, Shift+Mausrad: horizontal
        self._cv.bind("<MouseWheel>",
                      lambda e: self._cv.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        self._cv.bind("<Shift-MouseWheel>",
                      lambda e: self._cv.xview_scroll(-1 if e.delta > 0 else 1, "units"))
        # Strg+Mausrad: Zoom
        self._cv.bind("<Control-MouseWheel>", self._cv_zoom_wheel)
        # Löschen / Undo / Redo
        self._cv.bind("<Delete>",     lambda e: self._delete_obj())
        self._cv.bind("<BackSpace>",  lambda e: self._undo())
        self._cv.bind("<Control-z>",  self._undo)
        self._cv.bind("<Control-y>",  self._redo)
        self._cv.bind("<Control-Z>",  self._undo)
        self._cv.bind("<Control-Shift-Z>", self._redo)

    def _build_props_area(self, right):
        self._props_frame = right
        self._props_built = False
        # Nur der Header ist immer sichtbar; Canvas/Scrollbar werden lazy gebaut
        tk.Label(right, text="Eigenschaften",
                 bg=utils.C["surface"], fg=utils.C["accent"],
                 font=("Segoe UI", 9, "bold")).pack(padx=8, pady=(10, 4))

    def _ensure_props_built(self):
        """Baut Canvas + Scrollbar + Inner-Frame beim ersten Bedarf (lazy)."""
        if self._props_built:
            return
        right = self._props_frame
        self._props_canvas = tk.Canvas(right, bg=utils.C["surface"],
                                        highlightthickness=0)
        vsb = ttk.Scrollbar(right, orient="vertical",
                            command=self._props_canvas.yview)
        self._props_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._props_canvas.pack(side="left", fill="both", expand=True)

        self._props_inner = tk.Frame(self._props_canvas, bg=utils.C["surface"])
        self._props_win = self._props_canvas.create_window(
            (0, 0), window=self._props_inner, anchor="nw")

        def on_cfg(e):
            self._props_canvas.configure(
                scrollregion=self._props_canvas.bbox("all"))
            self._props_canvas.itemconfig(
                self._props_win, width=self._props_canvas.winfo_width())

        self._props_inner.bind("<Configure>", on_cfg)
        self._props_canvas.bind("<Configure>", on_cfg)

        def _scroll_props(event):
            self._props_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

        self._props_canvas.bind("<MouseWheel>", _scroll_props)
        self._props_inner.bind("<MouseWheel>", _scroll_props)

        def _bind_children(widget):
            widget.bind("<MouseWheel>", _scroll_props)
            for child in widget.winfo_children():
                _bind_children(child)

        self._props_inner.bind("<Configure>",
            lambda e: (on_cfg(e), _bind_children(self._props_inner)), add=True)

        self._props_built = True

    def _build_xml_bar(self, f):
        bar = tk.Frame(f, bg=utils.C["header"])
        bar.pack(fill="x")
        hdr = tk.Frame(bar, bg=utils.C["header"])
        hdr.pack(fill="x", padx=8, pady=(4, 0))
        tk.Label(hdr, text="G-PRINT XML (live)",
                 bg=utils.C["header"], fg=utils.C["accent"],
                 font=("Segoe UI", 9, "bold")).pack(side="left")

        # Groessen-Waehler
        self._xml_height_var = tk.StringVar(value="5")
        for h, lbl in [("3","S"), ("5","M"), ("9","L")]:
            tk.Button(hdr, text=lbl, bg=utils.C["border"], fg=utils.C["text"],
                      font=("Segoe UI", 8), relief="flat", padx=6,
                      command=lambda hh=h: self._set_xml_height(hh)
                      ).pack(side="right", padx=1, pady=2)
        tk.Label(hdr, text="Groesse:", bg=utils.C["header"], fg=utils.C["subtext"],
                 font=("Segoe UI", 8)).pack(side="right", padx=(6, 2))

        # Toggle
        self._xml_visible = True
        self._xml_toggle_btn = tk.Button(
            hdr, text="▼", bg=utils.C["header"], fg=utils.C["subtext"],
            font=("Segoe UI", 9), relief="flat", bd=0,
            command=self._toggle_xml)
        self._xml_toggle_btn.pack(side="right", padx=(12, 4))

        ttk.Button(hdr, text="Kopieren",
                   command=self._copy_xml).pack(side="right", pady=2)

        self._xml_txt = scrolledtext.ScrolledText(
            bar, height=5, bg=utils.C["header"], fg=utils.C["subtext"],
            font=("Consolas", 8), relief="flat", bd=0, state="disabled")
        self._xml_txt.pack(fill="x", padx=8, pady=(0, 6))

    def _toggle_xml(self):
        if self._xml_visible:
            self._xml_txt.pack_forget()
            self._xml_toggle_btn.config(text="▶")
        else:
            self._xml_txt.pack(fill="x", padx=8, pady=(0, 6))
            self._xml_toggle_btn.config(text="▼")
        self._xml_visible = not self._xml_visible

    def _set_xml_height(self, h):
        self._xml_txt.config(height=int(h))
        if not self._xml_visible:
            self._xml_txt.pack(fill="x", padx=8, pady=(0, 6))
            self._xml_toggle_btn.config(text="▼")
            self._xml_visible = True

    # ── Koordinaten: Y=0 = UNTEN ──────────────────────────────────────────────

    def _zoom(self):
        try:
            return int(self._zoom_var.get().replace("x", ""))
        except Exception:
            return 4

    def _ph(self):
        return PRINT_MODES.get(self._pm_var.get(), 32)

    def _pw(self):
        try:
            return max(10, int(self._w_var.get()))
        except Exception:
            return 512

    def _p2c(self, px, py):
        """Printer (px, py) → Canvas (cx, cy_top_of_1px_cell).
        Y=0 ist die unterste Reihe des Labels."""
        z  = self._zoom()
        ph = self._ph()
        cx = RULER_W + CANVAS_PAD + px * z
        # py=0 → unterste Zeile; umrechnen: cy_bottom = CANVAS_PAD + ph*z
        cy = CANVAS_PAD + (ph - py - 1) * z   # oberste Kante der Zelle bei py
        return (cx, cy)

    def _p2c_obj(self, obj):
        """Canvas-Rechteck (cx, cy_top, cx2, cy_bottom) fuer ein Objekt."""
        z  = self._zoom()
        ph = self._ph()
        # Für Formen: Bounding Box aus min/max von Start- und Endpunkt
        if obj.otype in ("line", "rect", "ellipse"):
            x1 = min(obj.x, obj.x2); x2 = max(obj.x, obj.x2)
            y1 = min(obj.y, obj.y2); y2 = max(obj.y, obj.y2)
            cx  = RULER_W + CANVAS_PAD + x1 * z
            cx2 = RULER_W + CANVAS_PAD + x2 * z
            cy_b = CANVAS_PAD + (ph - y1) * z - 1
            cy_t = CANVAS_PAD + (ph - y2) * z - 1
            return (cx, cy_t, cx2, cy_b)
        aw = max(obj.approx_width(), 1)
        ah = max(obj.approx_height(), 1)
        cx   = RULER_W + CANVAS_PAD + obj.x * z
        cy_b = CANVAS_PAD + (ph - obj.y) * z - 1
        cy_t = CANVAS_PAD + (ph - obj.y - ah) * z - 1
        return (cx, cy_t, cx + aw * z, cy_b)

    def _c2p(self, cx, cy):
        """Canvas (cx, cy) → Printer (px, py). py=0 unten."""
        z  = self._zoom()
        ph = self._ph()
        px = (cx - RULER_W - CANVAS_PAD) // z
        # cy = CANVAS_PAD + (ph - py - 1)*z  →  py = ph - 1 - (cy-CANVAS_PAD)//z
        py = ph - 1 - (cy - CANVAS_PAD) // z
        return (px, py)

    # ── Canvas Rendering ──────────────────────────────────────────────────────

    def _draw_obj(self, obj):
        z   = self._zoom()
        ph  = self._ph()
        sel = obj is self.selected
        cx, cy_t, cx2, cy_b = self._p2c_obj(obj)
        aw  = cx2 - cx
        ah  = cy_b - cy_t
        tag = f"obj{obj.id}"
        color = OBJ_COLORS.get(
            obj.otype if obj.otype in OBJ_COLORS else "text", "#89b4fa")

        # ── DMC ──
        if obj.otype == "matrix":
            overflow = obj.dmc_overflow()
            outline  = utils.C["red"] if overflow else color
            self._cv.create_rectangle(cx, cy_t, cx2, cy_b,
                                       fill="", outline=outline,
                                       width=3 if overflow else (2 if sel else 1),
                                       tags=tag)
            self._draw_dmc_pattern(cx, cy_t, aw, ah, obj, tag)
            if overflow:
                self._cv.create_text(cx + aw//2, cy_b + 10,
                                      text="OVERFLOW!", fill=utils.C["red"],
                                      font=("Segoe UI", 7, "bold"), tags=tag)

        # ── Linie ──
        elif obj.otype == "line":
            # Direkte Koordinatenberechnung (cy_t wäre falsch - das ist Bounding-Box-Oberkante)
            lx1 = RULER_W + CANVAS_PAD + obj.x  * z
            ly1 = CANVAS_PAD + (ph - obj.y)  * z - 1
            lx2 = RULER_W + CANVAS_PAD + obj.x2 * z
            ly2 = CANVAS_PAD + (ph - obj.y2) * z - 1
            lw  = max(2, obj.lw * max(1, z // 3))
            self._cv.create_line(lx1, ly1, lx2, ly2,
                                  fill=color, width=lw, tags=tag)
            # Endpunkt-Marker
            for px, py in [(lx1, ly1), (lx2, ly2)]:
                self._cv.create_oval(px-3, py-3, px+3, py+3,
                                      fill=color, outline="", tags=tag)

        # ── Rechteck / Ellipse ──
        elif obj.otype in ("rect", "ellipse"):
            rx1 = RULER_W + CANVAS_PAD + min(obj.x, obj.x2) * z
            rx2 = RULER_W + CANVAS_PAD + max(obj.x, obj.x2) * z
            ry1 = CANVAS_PAD + (ph - max(obj.y, obj.y2)) * z - 1
            ry2 = CANVAS_PAD + (ph - min(obj.y, obj.y2)) * z - 1
            fn  = (self._cv.create_rectangle if obj.otype == "rect"
                   else self._cv.create_oval)
            fn(rx1, ry1, rx2, ry2,
               fill=color if obj.fill else "",
               outline=color, width=2 if sel else 1, tags=tag)

        # ── Logo ──
        elif obj.otype == "logo":
            # Rahmen (transparent - nur Umrandung, kein weisser Fill)
            self._cv.create_rectangle(cx, cy_t, cx2, cy_b,
                                       fill="", outline=color,
                                       width=2 if sel else 1, tags=tag)
            rendered_logo = False
            if obj.logo_file:
                logo_path = obj.logo_file
                if not os.path.isabs(logo_path):
                    logo_path = os.path.join(BASE_DIR, "res", "logos", logo_path)
                if os.path.exists(logo_path):
                    try:
                        photo = self._render_logo(logo_path, aw, ah, obj.logo_h)
                        if photo:
                            if not hasattr(self, "_photo_refs"):
                                self._photo_refs = []
                            self._photo_refs.append(photo)
                            self._cv.create_image(cx, cy_t, image=photo,
                                                   anchor="nw", tags=tag)
                            rendered_logo = True
                    except Exception as _logo_err:
                        self.log(f"Logo-Render Fehler ({os.path.basename(logo_path)}): {_logo_err}", "error")
            if not rendered_logo:
                self._cv.create_line(cx, cy_t, cx2, cy_b, fill=color, width=1, tags=tag)
                self._cv.create_line(cx2, cy_t, cx, cy_b, fill=color, width=1, tags=tag)
                fname = os.path.basename(obj.logo_file) if obj.logo_file else "(kein)"
                self._cv.create_text(cx + aw//2, cy_t + ah//2,
                                      text=f"LOGO\n{fname}",
                                      fill=color, font=("Segoe UI", 7),
                                      justify="center", tags=tag)

        # ── Barcode ──
        elif obj.otype in [t for t in BARCODE_TYPES if t != "matrix"]:
            self._cv.create_rectangle(cx, cy_t, cx2, cy_b,
                                       fill="#eeeeff", outline=color,
                                       width=2 if sel else 1, tags=tag)
            bw = max(1, z // 2)
            for i in range(0, int(aw) - 2, bw * 2):
                self._cv.create_line(cx + i + 1, cy_t + 2,
                                      cx + i + 1, cy_b - 2,
                                      fill=color, width=bw, tags=tag)
            self._cv.create_text(cx + aw//2, cy_b + 8,
                                  text=f"{obj.otype}",
                                  fill=color, font=("Segoe UI", 7), tags=tag)

        # ── Text / Zeit / Zaehler ──
        else:
            # Datenfeld ohne Platzhalter → rot hervorheben
            df_no_placeholder = (obj.field_type == "datafield"
                                  and not obj.placeholder_txt)
            if df_no_placeholder:
                bg_fill = "#3a0a0a"
                fg_text = utils.C["red"]
                outline_color = utils.C["red"]
            elif obj.neg:
                bg_fill = "#111111"; fg_text = "#ffffff"; outline_color = color
            else:
                bg_fill = ""; fg_text = "#000000"; outline_color = color

            outline_w = 2 if (df_no_placeholder or sel) else 0
            self._cv.create_rectangle(cx, cy_t, cx2, cy_b,
                                       fill=bg_fill, outline=outline_color,
                                       width=outline_w, tags=tag)

            # Pixel-genaue Font-Darstellung
            finfo    = FONT_INFO.get(obj.font_face, (obj.font_size, 6, obj.font_face))
            tk_fam   = finfo[2]
            char_h   = obj.font_size if obj.font_size > 0 else finfo[0]
            px_size  = -(char_h * z)
            weight   = "bold"   if obj.font_bold   else "normal"
            slant    = "italic" if obj.font_italic else "roman"
            used_font = (tk_fam, px_size, weight, slant)

            preview = (obj.placeholder_txt
                       if obj.field_type == "datafield" and obj.placeholder_txt
                       else obj.canvas_preview_text())
            if obj.bwd:
                preview = preview[::-1]

            mag = max(1, obj.mag)
            rendered = False

            # ── Render-Cache: PIL-Rendering überspringen wenn nichts geändert ──
            # Cache wird in _redraw() bei Zoom-Änderung geleert (s.u.)
            if len(self._render_cache) > 300:
                self._render_cache.clear()

            if mag > 1 and preview:
                # PIL: Text bei voller Zellenhöhe rendern, dann NUR horizontal um MAG strecken
                try:
                    from PIL import Image, ImageDraw, ImageFont, ImageTk
                    cell_h = max(2, finfo[0] * z)          # Zeichenhöhe in Canvas-Px
                    fp     = _resolve_font_path(tk_fam)
                    if not fp:
                        raise FileNotFoundError(f"Font nicht gefunden: {tk_fam}")
                    _ck = ("bitmap", fp, cell_h, preview, mag, fg_text)
                    photo = self._render_cache.get(_ck)
                    if photo is None:
                        pil_fnt = ImageFont.truetype(fp, size=cell_h)
                        tmp = Image.new("RGBA", (4, 4))
                        bb  = ImageDraw.Draw(tmp).textbbox((0, 0), preview, font=pil_fnt)
                        nat_w = max(1, bb[2] - bb[0])
                        nat_h = max(1, bb[3] - bb[1])
                        img = Image.new("RGBA", (nat_w, nat_h), (0, 0, 0, 0))
                        drw = ImageDraw.Draw(img)
                        r = int(fg_text[1:3], 16)
                        g = int(fg_text[3:5], 16)
                        b = int(fg_text[5:7], 16)
                        drw.text((-bb[0], -bb[1]), preview, font=pil_fnt, fill=(r, g, b, 255))
                        scaled = img.resize((nat_w * mag, cell_h), Image.NEAREST)
                        photo  = ImageTk.PhotoImage(scaled)
                        self._render_cache[_ck] = photo
                    self._photo_refs.append(photo)
                    self._cv.create_image(cx, cy_b, image=photo,
                                           anchor="sw", tags=tag)
                    rendered = True
                except Exception:
                    rendered = False

            # PIL-Fallback für alle Fonts (lokal + System wie Arial)
            if not rendered and preview:
                fp = _resolve_font_path(tk_fam)
                if fp:
                    try:
                        from PIL import Image, ImageDraw, ImageFont, ImageTk
                        cell_h  = max(2, (obj.font_size if obj.font_size > 0 else finfo[0]) * z)
                        _ck = ("fallback", fp, cell_h, preview, mag, fg_text)
                        photo = self._render_cache.get(_ck)
                        if photo is None:
                            pil_fnt = ImageFont.truetype(fp, size=cell_h)
                            tmp = Image.new("RGBA", (4, 4))
                            bb  = ImageDraw.Draw(tmp).textbbox((0, 0), preview, font=pil_fnt)
                            nat_w = max(1, bb[2] - bb[0])
                            nat_h = max(1, bb[3] - bb[1])
                            img = Image.new("RGBA", (nat_w * mag, cell_h), (0, 0, 0, 0))
                            drw = ImageDraw.Draw(img)
                            r = int(fg_text[1:3], 16)
                            g = int(fg_text[3:5], 16)
                            b = int(fg_text[5:7], 16)
                            drw.text((-bb[0], -bb[1]), preview, font=pil_fnt,
                                     fill=(r, g, b, 255))
                            if mag > 1:
                                img = img.resize((nat_w * mag, cell_h), Image.NEAREST)
                            photo = ImageTk.PhotoImage(img)
                            self._render_cache[_ck] = photo
                        self._photo_refs.append(photo)
                        self._cv.create_image(cx, cy_b, image=photo,
                                              anchor="sw", tags=tag)
                        rendered = True
                    except Exception:
                        rendered = False

            if not rendered:
                self._cv.create_text(
                    cx, cy_t + ah // 2,
                    text=preview,
                    fill=fg_text, font=used_font,
                    angle=obj.angle,
                    anchor="w", tags=tag)
                if mag > 1:
                    self._cv.create_text(
                        cx + 1, cy_t + 1, text=f"{mag}×(Pillow?)",
                        fill=utils.C["orange"], font=("Segoe UI", 6, "bold"),
                        anchor="nw", tags=tag)

            # Badge oben rechts
            if df_no_placeholder:
                badge = "!"; badge_fg = utils.C["red"]
            elif obj.field_type == "datafield":
                badge = f"D{obj.idx}"; badge_fg = utils.C["green"]
            elif obj.field_type == "prompted":
                badge = "P"; badge_fg = "#5a3a8a"
            else:
                badge = None
            if badge:
                bx = cx2 - 2; by = cy_t + 2
                self._cv.create_text(bx, by, text=badge,
                                      fill=badge_fg,
                                      font=("Segoe UI", 6, "bold"),
                                      anchor="ne", tags=tag)

            # Info-Zeile unter dem Objekt wenn kein Platzhalter
            if df_no_placeholder:
                self._cv.create_text(
                    cx, cy_b + 2,
                    text="Datenfeld nicht befüllt",
                    fill=utils.C["red"], font=("Segoe UI", 6),
                    anchor="nw", tags=tag)

            # MAG / BWD Badges unten links
            extra_badges = []
            if obj.mag > 1:
                extra_badges.append(f"{obj.mag}×")
            if obj.bwd:
                extra_badges.append("◄BWD")
            if extra_badges:
                self._cv.create_text(
                    cx + 1, cy_t + 1,
                    text=" ".join(extra_badges),
                    fill=utils.C["orange"], font=("Segoe UI", 6, "bold"),
                    anchor="nw", tags=tag)

        # ── Kollisions-Indikator: Rahmen orange wenn Objekt ein anderes überlappt ──
        collides = self._obj_collides(obj)
        if collides and not sel:
            # Auch unselektierte überlappende Objekte bekommen orangen Rahmen
            self._cv.create_rectangle(
                cx - 1, cy_t - 1, cx2 + 1, cy_b + 1,
                outline=utils.C["orange"], width=2,
                tags=tag + "_c")

        # ── Auswahl-Rahmen: nur bei Klick ──
        if sel:
            frame_color = utils.C["orange"] if collides else utils.C["accent"]
            self._cv.create_rectangle(
                cx - 2, cy_t - 2, cx2 + 2, cy_b + 2,
                outline=frame_color, width=2 if collides else 1, dash=(4, 3),
                tags=tag + "_s")
            # Resize-Handle oben rechts (kleines oranges Quadrat)
            self._cv.create_rectangle(
                cx2 - 5, cy_t - 5, cx2 + 5, cy_t + 5,
                fill=utils.C["orange"], outline=utils.C["header"], width=1,
                tags=tag + "_s")
            # Koordinaten- und Größen-Badge mit dunklem Hintergrund
            h_val     = obj.approx_height()
            w_val     = obj.approx_width()
            coord_txt = f" X:{obj.x}  Y:{obj.y}  H:{h_val}  L:{w_val} "
            badge_w   = len(coord_txt) * 5 + 4
            self._cv.create_rectangle(
                cx, cy_t - 16, cx + badge_w, cy_t - 1,
                fill="#1e1e2e", outline="", tags=tag + "_s")
            self._cv.create_text(
                cx + 3, cy_t - 9,
                text=coord_txt.strip(),
                fill="#a6e3a1", font=("Segoe UI", 7, "bold"),
                anchor="w", tags=tag + "_s")

        # tag_bind entfernt: _cv_click() (canvas-weites Binding) übernimmt
        # Objekt-Selektion bereits via _hit_test() → kein doppeltes _select()/_redraw()

    def _render_logo(self, path, canvas_w, canvas_h, printer_h=None):
        """SVG, MLG oder Bitmap-Logo als PhotoImage rendern."""
        from PIL import Image, ImageTk, ImageDraw
        ext = os.path.splitext(path)[1].lower()
        w = max(1, int(canvas_w))
        h = max(1, int(canvas_h))

        if ext == ".mlg":
            # alphaJET MLG: Column-major Bit-packed Binary
            pixels, mlg_w, mlg_h = LogoEditorTab._mlg_decode(path, hint_h=printer_h)
            src = Image.new("RGBA", (mlg_w, mlg_h), (0, 0, 0, 0))
            px  = src.load()
            for (c2, r2) in pixels:
                if 0 <= c2 < mlg_w and 0 <= r2 < mlg_h:
                    px[c2, r2] = (0, 0, 0, 255)
            img = src.resize((w, h), Image.NEAREST)
            return ImageTk.PhotoImage(img)

        if ext == ".svg":
            import xml.etree.ElementTree as ET
            root = ET.parse(path).getroot()
            vb = root.get("viewBox", "")
            if vb:
                parts = vb.split()
                svg_w, svg_h = float(parts[2]), float(parts[3])
            else:
                svg_w = float(root.get("width", canvas_w) or canvas_w)
                svg_h = float(root.get("height", canvas_h) or canvas_h)
            svg_w = max(1, svg_w); svg_h = max(1, svg_h)
            # Transparenter Hintergrund (RGBA), nur schwarze Pixel werden gezeichnet
            img = Image.new("RGBA", (int(canvas_w), int(canvas_h)), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            sx = canvas_w / svg_w
            sy = canvas_h / svg_h
            for elem in root.iter():
                tag_n = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                if tag_n != "rect":
                    continue
                fill = elem.get("fill", "")
                if fill.lower() not in ("black", "#000000", "#000"):
                    continue
                x  = float(elem.get("x", 0))
                y  = float(elem.get("y", 0))
                rw = float(elem.get("width",  1))
                rh = float(elem.get("height", 1))
                draw.rectangle([x*sx, y*sy, (x+rw)*sx, (y+rh)*sy], fill=(0, 0, 0, 255))
        else:
            # Bitmap: weisse Pixel transparent machen
            w = max(1, int(canvas_w))
            h = max(1, int(canvas_h))
            src = Image.open(path)
            src.load()          # vollständig in Speicher laden (kein lazy open)
            src = src.convert("RGBA")
            src = src.resize((w, h), Image.NEAREST)
            px  = src.load()
            for yy in range(src.height):
                for xx in range(src.width):
                    r, g, b, a = px[xx, yy]
                    if r > 200 and g > 200 and b > 200:
                        px[xx, yy] = (255, 255, 255, 0)
            img = src
        return ImageTk.PhotoImage(img)

    def _draw_dmc_pattern(self, cx, cy_t, aw, ah, obj, tag):
        """Zeichnet ein vereinfachtes Data-Matrix-Muster."""
        cols, rows, _ = DMC_SIZES.get(obj.dmc_size, (16, 16, 12))
        cw = aw / cols
        rh = ah / rows
        # Deterministisch aus Text-Inhalt
        h = hashlib.md5(obj.text.encode()).digest()
        bit_idx = 0

        for r in range(rows):
            for c in range(cols):
                px = cx + c * cw
                py = cy_t + r * rh
                filled = False

                # Finder-Pattern: linke Spalte (immer schwarz)
                if c == 0:
                    filled = True
                # Finder-Pattern: untere Zeile (immer schwarz)
                elif r == rows - 1:
                    filled = True
                # Timing: rechte Spalte (abwechselnd)
                elif c == cols - 1:
                    filled = (r % 2 == 0)
                # Timing: oberste Zeile (abwechselnd)
                elif r == 0:
                    filled = (c % 2 == 0)
                else:
                    # Datenbereich: Pseudozufaellig aus Hash
                    byte_i = bit_idx // 8
                    bit_i  = bit_idx % 8
                    filled = bool(h[byte_i % len(h)] & (1 << bit_i))
                    bit_idx += 1

                if filled:
                    self._cv.create_rectangle(
                        px, py, px + cw, py + rh,
                        fill="#111111", outline="",
                        tags=tag)

    # ── Canvas Events ─────────────────────────────────────────────────────────

    def _obj_bbox_printer(self, obj):
        """Bounding-Box eines Objekts in Drucker-Koordinaten (x1, y1, x2, y2)."""
        if obj.otype in ("line", "rect", "ellipse"):
            x1 = min(obj.x, obj.x2); x2 = max(obj.x, obj.x2)
            y1 = min(obj.y, obj.y2); y2 = max(obj.y, obj.y2)
        else:
            x1 = obj.x
            x2 = obj.x + max(1, obj.approx_width())
            y1 = obj.y
            y2 = obj.y + max(1, obj.approx_height())
        return (x1, y1, x2, y2)

    def _obj_collides(self, obj):
        """True wenn obj sich mit einem anderen Objekt überlappt.
        NEG=1 Objekte (Hintergrundboxen) überlappen absichtlich → ignorieren."""
        if obj.neg:
            return False
        ax1, ay1, ax2, ay2 = self._obj_bbox_printer(obj)
        for other in self.objects:
            if other is obj or other.neg:   # NEG-Objekte als Kollisionspartner auch ignorieren
                continue
            bx1, by1, bx2, by2 = self._obj_bbox_printer(other)
            if ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1:
                return True
        return False

    def _hit_test(self, cx, cy):
        z  = self._zoom()
        ph = self._ph()
        for obj in reversed(self.objects):
            ox, cy_t, ox2, cy_b = self._p2c_obj(obj)
            if ox <= cx <= ox2 and cy_t <= cy <= cy_b:
                return obj
        return None

    def _cv_click_focus(self, event):
        self._cv.focus_set()

    def _cv_hover(self, event):
        """Cursor ändern wenn über dem Resize-Handle des selektierten Objekts."""
        if not self.selected:
            return
        cx = self._cv.canvasx(event.x)
        cy = self._cv.canvasy(event.y)
        ox, oy_t, ox2, oy_b = self._p2c_obj(self.selected)
        if abs(cx - ox2) <= 8 and abs(cy - oy_t) <= 8:
            self._cv.config(cursor="sizing")
        else:
            self._cv.config(cursor="crosshair")

    def _cv_zoom_wheel(self, event):
        zooms = ["1x","2x","3x","4x","5x","6x","8x","10x","12x","16x","20x","24x","32x"]
        cur   = self._zoom_var.get()
        idx   = zooms.index(cur) if cur in zooms else 3
        idx   = max(0, min(len(zooms)-1, idx + (1 if event.delta > 0 else -1)))
        self._zoom_var.set(zooms[idx])
        self._redraw()

    def _arrow_move(self, dx, dy):
        if not self.selected:
            return
        self.selected.x += dx
        self.selected.y += dy
        self._redraw()
        self._sync_pos_fields()

    def _cv_click(self, event):
        cx  = self._cv.canvasx(event.x)
        cy  = self._cv.canvasy(event.y)
        # Resize-Handle prüfen (Ecke oben rechts des selektierten Objekts)
        if self.selected:
            ox, oy_t, ox2, oy_b = self._p2c_obj(self.selected)
            if abs(cx - ox2) <= 8 and abs(cy - oy_t) <= 8:
                self._resize_mode = True
                self._drag_data   = (cx, cy,
                                     self.selected.x, self.selected.y,
                                     self.selected.x2 if hasattr(self.selected, "x2") else 0,
                                     self.selected.y2 if hasattr(self.selected, "y2") else 0,
                                     self.selected.logo_w if self.selected.otype == "logo" else 0,
                                     self.selected.mag)
                return
        self._resize_mode = False
        obj = self._hit_test(cx, cy)
        self._select(obj)
        if obj:
            self._drag_data = (cx, cy, obj.x, obj.y,
                               obj.x2 if hasattr(obj, "x2") else 0,
                               obj.y2 if hasattr(obj, "y2") else 0,
                               0, obj.mag)

    def _cv_drag(self, event):
        if not self._drag_data or not self.selected:
            return
        cx = self._cv.canvasx(event.x)
        cy = self._cv.canvasy(event.y)
        z  = self._zoom()
        obj = self.selected

        if getattr(self, "_resize_mode", False):
            # Breite ändern per Ziehen an der Ecke
            dx = int((cx - self._drag_data[0]) / z)
            if obj.otype in ("line", "rect", "ellipse"):
                obj.x2 = self._drag_data[4] + dx
            elif obj.otype == "logo":
                obj.logo_w = max(1, self._drag_data[6] + dx)
            else:
                # MAG erhöhen pro ~10 Strokes Ziehdistanz
                obj.mag = max(1, min(8, self._drag_data[7] + dx // 10))
        else:
            dx = int((cx - self._drag_data[0]) / z)
            dy = int((self._drag_data[1] - cy) / z)
            obj.x = self._drag_data[2] + dx
            obj.y = self._drag_data[3] + dy
            # Formen: auch Endpunkt verschieben
            if obj.otype in ("line", "rect", "ellipse"):
                obj.x2 = self._drag_data[4] + dx
                obj.y2 = self._drag_data[5] + dy

        self._redraw()
        self._sync_pos_fields()

    def _cv_release(self, _event):
        if self._drag_data:
            self._push_undo()   # Position/Größe nach Drag sichern
        self._drag_data   = None
        self._resize_mode = False

    def _cv_dblclick(self, event):
        cx  = self._cv.canvasx(event.x)
        cy  = self._cv.canvasy(event.y)
        obj = self._hit_test(cx, cy)
        if obj and obj.otype not in ("time", "counter", "line",
                                       "rect", "ellipse", "matrix"):
            val = simpledialog.askstring(
                "Text bearbeiten", "Inhalt:",
                initialvalue=obj.text, parent=self.parent)
            if val is not None:
                obj.text = val
                self._redraw()

    # ── Objekt-Verwaltung ─────────────────────────────────────────────────────

    def _add_object(self, otype):
        # Kein Dialog fuer Formen
        if otype == "logo":
            self._add_logo_object()
            return

        if otype in ("line", "rect", "ellipse"):
            obj = LabelObject(otype)
            obj.x2 = obj.x + 60
            obj.y2 = obj.y + self._ph() - 1
            if self.objects:
                last = self.objects[-1]
                obj.x = last.x + 5
            self.objects.append(obj)
            self._refresh_list()
            self._select(obj)
            self._push_undo()
            return

        # Naechsten verfuegbaren Index ermitteln
        used_idx = {o.idx for o in self.objects if o.idx is not None}
        suggest  = 1
        while suggest in used_idx:
            suggest += 1

        # Dialog
        dlg = FieldTypeDialog(self.parent, suggest_idx=suggest)
        if dlg.result is None:
            return

        obj = LabelObject(otype)
        ft  = dlg.result["type"]
        obj.field_type  = ft
        obj.prompt_name = dlg.result["name"]

        if ft == "datafield":
            obj.idx  = dlg.result["idx"]
            obj.text = f"[Feld {obj.idx}]"
        elif ft == "prompted":
            obj.text = dlg.result["name"]
        else:
            if otype == "time":
                obj.text = ""
            elif otype == "counter":
                obj.text = ""
            elif otype == "matrix":
                obj.text = "Inhalt"
            else:
                obj.text = "Text"

        if otype == "matrix":
            obj.dmc_size = "16x16"
        elif otype == "barcode":
            obj.otype = "code128"
            obj.text  = obj.text or "12345"

        # Position: leicht versetzt nach dem letzten Objekt
        if self.objects:
            last = self.objects[-1]
            obj.x = last.x + 5
            obj.y = last.y

        self.objects.append(obj)
        self._refresh_list()
        self._select(obj)
        self._push_undo()

    def _delete_obj(self):
        if not self.selected:
            return
        self.objects.remove(self.selected)
        self.selected = None
        self._refresh_list()
        self._show_empty_props()
        self._redraw()
        self._push_undo()

    def _obj_up(self):
        if not self.selected:
            return
        i = self.objects.index(self.selected)
        if i > 0:
            self.objects[i], self.objects[i-1] = self.objects[i-1], self.objects[i]
            self._refresh_list()
            self._redraw()

    def _obj_down(self):
        if not self.selected:
            return
        i = self.objects.index(self.selected)
        if i < len(self.objects) - 1:
            self.objects[i], self.objects[i+1] = self.objects[i+1], self.objects[i]
            self._refresh_list()
            self._redraw()

    def _on_list_select(self, _=None):
        sel = self._obj_lb.curselection()
        if sel and 0 <= sel[0] < len(self.objects):
            self._select(self.objects[sel[0]])

    def _select(self, obj):
        xpos = self._cv.xview()
        ypos = self._cv.yview()
        self.selected = obj
        self._refresh_list()
        self._redraw()
        self._update_info_box(obj)
        if obj:
            self._show_props(obj)
        else:
            self._show_empty_props()
        # Props-Panel neu aufbauen lässt Entry-Widgets den Fokus stehlen →
        # tkinter scrollt den Canvas nach oben. Nach dem Event-Loop wiederherstellen.
        self._cv.after(0, lambda: self._cv.xview_moveto(xpos[0]))
        self._cv.after(0, lambda: self._cv.yview_moveto(ypos[0]))

    def _refresh_list(self):
        self._obj_lb.delete(0, "end")
        for i, obj in enumerate(self.objects):
            prefix = "► " if obj is self.selected else "  "
            self._obj_lb.insert("end", f"{prefix}{i+1}. {obj.display_label()}")
        if self.selected and self.selected in self.objects:
            self._obj_lb.selection_set(self.objects.index(self.selected))

    # ── Properties Panel ──────────────────────────────────────────────────────

    def _show_empty_props(self):
        if not self._props_built:
            return  # Panel noch nicht gebaut → nichts zu leeren
        for w in self._props_inner.winfo_children():
            w.destroy()
        tk.Label(self._props_inner,
                 text="Kein Objekt ausgewaehlt.\n\nKlicke auf ein Objekt\nim Canvas.",
                 bg=utils.C["surface"], fg=utils.C["subtext"],
                 font=("Segoe UI", 9), justify="center").pack(pady=24)

    def _show_props(self, obj):
        self._ensure_props_built()
        for w in self._props_inner.winfo_children():
            w.destroy()
        self._fill_props(self._props_inner, obj)

    def _fill_props(self, f, obj):
        row = [0]

        def sep():
            tk.Frame(f, bg=utils.C["border"], height=1).grid(
                row=row[0], column=0, columnspan=2, sticky="ew", pady=5, padx=4)
            row[0] += 1

        def heading(text):
            tk.Label(f, text=text, bg=utils.C["surface"], fg=utils.C["accent"],
                     font=("Segoe UI", 8, "bold")).grid(
                row=row[0], column=0, columnspan=2, sticky="w", padx=4, pady=(4, 2))
            row[0] += 1

        def lbl_entry(label, var, width=10):
            tk.Label(f, text=label, bg=utils.C["surface"], fg=utils.C["subtext"],
                     font=("Segoe UI", 8)).grid(
                row=row[0], column=0, sticky="w", padx=(4, 2), pady=2)
            e = ttk.Entry(f, textvariable=var, width=width)
            e.grid(row=row[0], column=1, sticky="ew", padx=(0, 4), pady=2)
            row[0] += 1
            return e

        def lbl_check(label, var, cmd):
            tk.Label(f, text=label, bg=utils.C["surface"], fg=utils.C["subtext"],
                     font=("Segoe UI", 8)).grid(
                row=row[0], column=0, sticky="w", padx=(4, 2), pady=2)
            ttk.Checkbutton(f, variable=var, command=cmd).grid(
                row=row[0], column=1, sticky="w", pady=2)
            row[0] += 1

        def lbl_combo(label, var, values, cmd=None, width=12):
            tk.Label(f, text=label, bg=utils.C["surface"], fg=utils.C["subtext"],
                     font=("Segoe UI", 8)).grid(
                row=row[0], column=0, sticky="w", padx=(4, 2), pady=2)
            cb = ttk.Combobox(f, textvariable=var, values=values,
                               width=width, state="readonly")
            cb.grid(row=row[0], column=1, sticky="ew", padx=(0, 4), pady=2)
            if cmd:
                cb.bind("<<ComboboxSelected>>", lambda e: cmd())
            row[0] += 1
            return cb

        f.columnconfigure(1, weight=1)

        # ── Typ-Anzeige ──
        type_names = {"text": "Text", "time": "Datum/Zeit", "counter": "Zaehler",
                      "matrix": "DMC", "line": "Linie", "rect": "Rechteck"}
        tname = type_names.get(obj.otype, obj.otype)
        tk.Label(f, text=f"Typ: {tname}",
                 bg=utils.C["surface"], fg=utils.C["accent"],
                 font=("Segoe UI", 9, "bold")).grid(
            row=row[0], column=0, columnspan=2,
            sticky="w", padx=4, pady=(6, 8))
        row[0] += 1

        # ── Feld-Typ (Statisch / Datenfeld / Prompted) ──
        if obj.otype not in ("line", "rect", "ellipse"):
            heading("Feld-Typ")
            FT_LABELS = {"static": "Statisch", "datafield": "Datenfeld", "prompted": "Prompted"}
            FT_VALUES = list(FT_LABELS.keys())
            FT_DISPLAY = list(FT_LABELS.values())
            ft_disp_var = tk.StringVar(value=FT_LABELS.get(obj.field_type, "Statisch"))
            ft_cb = ttk.Combobox(f, textvariable=ft_disp_var,
                                  values=FT_DISPLAY, state="readonly", width=13)
            ft_cb.grid(row=row[0], column=0, columnspan=2,
                       sticky="ew", padx=4, pady=3)
            def _on_ft_select(e=None):
                chosen = ft_disp_var.get()
                val = FT_VALUES[FT_DISPLAY.index(chosen)] if chosen in FT_DISPLAY else "static"
                self._change_field_type(obj, val)
            ft_cb.bind("<<ComboboxSelected>>", _on_ft_select)
            row[0] += 1

            # Subfelder je nach Typ
            if obj.field_type == "datafield":
                idx_var = tk.StringVar(value=str(obj.idx or 1))
                def upd_idx(*_):
                    try:
                        obj.idx = int(idx_var.get())
                        self._refresh_list()
                        self._redraw()
                    except Exception:
                        pass
                idx_var.trace_add("write", upd_idx)
                lbl_entry("Feld-Index:", idx_var, width=5)

                # Platzhalter-Option
                has_ph = tk.BooleanVar(value=bool(obj.placeholder_txt))
                ph_txt_var = tk.StringVar(value=obj.placeholder_txt)

                ph_frame = tk.Frame(f, bg=utils.C["surface2"])
                ph_frame.grid(row=row[0], column=0, columnspan=2,
                              sticky="ew", padx=4, pady=3)
                row[0] += 1

                def _refresh_ph_ui():
                    for w in ph_frame.winfo_children():
                        w.destroy()
                    tk.Label(ph_frame, text="Platzhalter:", bg=utils.C["surface2"],
                             fg=utils.C["subtext"], font=("Segoe UI", 8)
                             ).grid(row=0, column=0, sticky="w", padx=(6, 4), pady=4)
                    ttk.Checkbutton(ph_frame, variable=has_ph,
                                    command=lambda: (
                                        setattr(obj, "placeholder_txt",
                                                ph_txt_var.get() if has_ph.get() else ""),
                                        _refresh_ph_ui(),
                                        self._redraw())
                                    ).grid(row=0, column=1, sticky="w", pady=4)
                    if has_ph.get():
                        tk.Label(ph_frame, text="Text:", bg=utils.C["surface2"],
                                 fg=utils.C["subtext"], font=("Segoe UI", 8)
                                 ).grid(row=1, column=0, sticky="w", padx=(6, 4), pady=2)
                        e = ttk.Entry(ph_frame, textvariable=ph_txt_var, width=14)
                        e.grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=2)
                        def _upd_ph(*_):
                            obj.placeholder_txt = ph_txt_var.get()
                            self._redraw()
                        ph_txt_var.trace_add("write", _upd_ph)
                    else:
                        tk.Label(ph_frame,
                                 text="  ⚠ Datenfeld nicht befüllt",
                                 bg=utils.C["surface2"], fg=utils.C["red"],
                                 font=("Segoe UI", 8, "bold")
                                 ).grid(row=1, column=0, columnspan=2,
                                        sticky="w", padx=6, pady=2)
                    ph_frame.columnconfigure(1, weight=1)

                _refresh_ph_ui()

            elif obj.field_type == "prompted":
                pn_var = tk.StringVar(value=obj.prompt_name)
                def upd_pn(*_):
                    obj.prompt_name = pn_var.get()
                    self._redraw()
                pn_var.trace_add("write", upd_pn)
                lbl_entry("Variablenname:", pn_var, width=14)

            sep()

        # ── Position ──
        heading("Position  (Y=0 = Unterkante)")
        self._px_var = tk.StringVar(value=str(obj.x))
        self._py_var = tk.StringVar(value=str(obj.y))

        def upd_x(*_):
            try: obj.x = int(self._px_var.get()); self._redraw()
            except: pass
        def upd_y(*_):
            try: obj.y = int(self._py_var.get()); self._redraw()
            except: pass

        self._px_var.trace_add("write", upd_x)
        self._py_var.trace_add("write", upd_y)
        lbl_entry("X (Strokes):", self._px_var)
        lbl_entry("Y (Pixel, 0=unten):", self._py_var)

        sw_var = tk.StringVar(value=str(obj.sw))
        def upd_sw(*_):
            try: obj.sw = int(sw_var.get()); self._redraw()
            except: pass
        sw_var.trace_add("write", upd_sw)
        lbl_entry("SW (Strichbr.):", sw_var)

        # Winkel
        ang_var = tk.StringVar(value=str(obj.angle))
        def upd_ang(*_):
            try: obj.angle = int(ang_var.get()) % 360; self._redraw()
            except: pass
        ang_var.trace_add("write", upd_ang)
        tk.Label(f, text="Winkel (°):", bg=utils.C["surface"], fg=utils.C["subtext"],
                 font=("Segoe UI", 8)).grid(
            row=row[0], column=0, sticky="w", padx=(4, 2), pady=2)
        ang_row = tk.Frame(f, bg=utils.C["surface"])
        ang_row.grid(row=row[0], column=1, sticky="ew", padx=(0, 4), pady=2)
        ttk.Entry(ang_row, textvariable=ang_var, width=5).pack(side="left", padx=(0, 2))
        for lbl, d in [("↺", 90), ("↻", -90), ("0", 0)]:
            ttk.Button(ang_row, text=lbl, width=3,
                       command=lambda dg=d, v=ang_var: (
                           v.set("0" if dg == 0 else str((int(v.get() or 0) + dg) % 360))
                       )).pack(side="left", padx=1)
        row[0] += 1

        neg_var = tk.BooleanVar(value=bool(obj.neg))
        lbl_check("Negativ:", neg_var,
                  lambda: (setattr(obj, "neg", 1 if neg_var.get() else 0), self._redraw()))
        bwd_var = tk.BooleanVar(value=bool(obj.bwd))
        lbl_check("Rueckwaerts:", bwd_var,
                  lambda: (setattr(obj, "bwd", 1 if bwd_var.get() else 0), self._redraw()))

        # MAG (Breiten-Streckung)
        if obj.otype not in ("line", "rect", "ellipse", "matrix"):
            tk.Label(f, text="Mag (Breite):", bg=utils.C["surface"], fg=utils.C["subtext"],
                     font=("Segoe UI", 8)).grid(
                row=row[0], column=0, sticky="w", padx=(4, 2), pady=2)
            mag_row = tk.Frame(f, bg=utils.C["surface"])
            mag_row.grid(row=row[0], column=1, sticky="w", pady=2)
            for m in (1, 2, 3, 4):
                style = "Green.TButton" if obj.mag == m else "TButton"
                ttk.Button(mag_row, text=f"{m}×", width=3, style=style,
                           command=lambda mv=m: self._set_mag(mv)
                           ).pack(side="left", padx=1)
            row[0] += 1

        sep()

        # ── Typ-spezifisch ──
        if obj.otype == "time":
            heading("Datum / Zeit")
            fmt_var = tk.StringVar(value=obj.time_fmt)
            def upd_fmt(*_):
                obj.time_fmt = fmt_var.get(); self._redraw()
            tk.Label(f, text="Format:", bg=utils.C["surface"], fg=utils.C["subtext"],
                     font=("Segoe UI", 8)).grid(
                row=row[0], column=0, sticky="w", padx=(4,2), pady=2)
            fc = ttk.Combobox(f, textvariable=fmt_var,
                               values=TIME_FORMATS, width=16)
            fc.grid(row=row[0], column=1, sticky="ew", padx=(0,4), pady=2)
            fc.bind("<<ComboboxSelected>>",
                    lambda e: (setattr(obj, "time_fmt", fmt_var.get()), self._redraw()))
            fmt_var.trace_add("write", upd_fmt)
            row[0] += 1
            for ltext, attr in [("+ Tage:", "exp_days"), ("+ Monate:", "exp_months"),
                                  ("+ Jahre:", "exp_years")]:
                var = tk.StringVar(value=str(getattr(obj, attr)))
                def mkupd(a=attr, v=var):
                    def u(*_):
                        try: setattr(obj, a, int(v.get())); self._redraw()
                        except: pass
                    return u
                var.trace_add("write", mkupd())
                lbl_entry(ltext, var, width=6)

        elif obj.otype == "counter":
            heading("Zaehler")
            # Grundwerte
            for lt, at in [("Start:", "numb_start"), ("Ende:", "numb_end"),
                            ("Schritt:", "numb_step"), ("Wiederholung:", "numb_rep"),
                            ("Zählerstand:", "numb_count")]:
                var = tk.StringVar(value=str(getattr(obj, at)))
                def mkupd(a=at, v=var):
                    def u(*_):
                        try: setattr(obj, a, int(v.get())); self._redraw()
                        except: pass
                    return u
                var.trace_add("write", mkupd())
                lbl_entry(lt, var, width=8)

            # Format
            FMT_LABELS = {1: "Führende Leerzeichen (1)", 2: "Linksbündig (2)"}
            fmt_var = tk.StringVar(value=FMT_LABELS.get(obj.numb_format, "Linksbündig (2)"))
            def _upd_fmt():
                val = 1 if "1" in fmt_var.get() else 2
                obj.numb_format = val
            lbl_combo("Format:", fmt_var, list(FMT_LABELS.values()), _upd_fmt, 18)

            sep()
            heading("Optionen")
            for lt, at in [("Autostop:", "numb_autostop"),
                            ("Rückstellbar:", "numb_resetable"),
                            ("Wiederh. rückstellbar:", "numb_represetable"),
                            ("Alpha-Code:", "numb_ac_enab"),
                            ("Start=PC:", "numb_start_pc"),
                            ("Globalen Zähler:", "numb_use_glob_cnt")]:
                bv = tk.BooleanVar(value=bool(getattr(obj, at)))
                lbl_check(lt, bv,
                          lambda a=at, v=bv: (setattr(obj, a, 1 if v.get() else 0),
                                              self._redraw()))

            sep()
            heading("Timed Reset")
            for lt, at in [("Stunden:", "numb_timedreset_hh"),
                            ("Minuten:", "numb_timedreset_mm")]:
                var = tk.StringVar(value=str(getattr(obj, at)))
                def mkupd2(a=at, v=var):
                    def u(*_):
                        try: setattr(obj, a, int(v.get()))
                        except: pass
                    return u
                var.trace_add("write", mkupd2())
                lbl_entry(lt, var, width=6)

            # Prompted-Zähler
            sep()
            heading("Prompted (Variablen-Zähler)")
            pv = tk.BooleanVar(value=bool(obj.numb_p))
            lbl_check("Prompted:", pv,
                      lambda: (setattr(obj, "numb_p", 1 if pv.get() else 0),
                               self._redraw()))
            pvn_var = tk.StringVar(value=obj.numb_pvn)
            def upd_pvn(*_):
                obj.numb_pvn = pvn_var.get()
            pvn_var.trace_add("write", upd_pvn)
            lbl_entry("Variablenname:", pvn_var, width=12)

        elif obj.otype == "matrix":
            heading("Data Matrix Code")
            sz_var = tk.StringVar(value=obj.dmc_size)
            def upd_sz():
                obj.dmc_size = sz_var.get(); self._redraw()
            lbl_combo("Groesse (Pixel):", sz_var, list(DMC_SIZES.keys()), upd_sz, 10)
            # Kapazitaet anzeigen
            cap = DMC_SIZES.get(obj.dmc_size, (16,16,12))[2]
            used = len(obj.text) if obj.field_type == "static" else 0
            cap_color = utils.C["red"] if used > cap else utils.C["green"]
            tk.Label(f, text=f"Kapazitaet: {used}/{cap} Zeichen",
                     bg=utils.C["surface"], fg=cap_color,
                     font=("Segoe UI", 8)).grid(
                row=row[0], column=0, columnspan=2,
                sticky="w", padx=4, pady=2)
            row[0] += 1
            if obj.field_type == "static":
                txt_var = tk.StringVar(value=obj.text)
                def upd_txt(*_):
                    obj.text = txt_var.get(); self._redraw()
                txt_var.trace_add("write", upd_txt)
                lbl_entry("Inhalt:", txt_var, width=14)

        elif obj.otype == "logo":
            heading("Logo")
            lf_var = tk.StringVar(value=obj.logo_file)
            def _upd_lf(*_):
                obj.logo_file = lf_var.get(); self._refresh_list(); self._redraw()
            lf_var.trace_add("write", _upd_lf)
            tk.Label(f, text="Dateiname:", bg=utils.C["surface"], fg=utils.C["subtext"],
                     font=("Segoe UI", 8)).grid(
                row=row[0], column=0, sticky="w", padx=(4, 2), pady=2)
            lf_row = tk.Frame(f, bg=utils.C["surface"])
            lf_row.grid(row=row[0], column=1, sticky="ew", padx=(0, 4), pady=2)
            ttk.Entry(lf_row, textvariable=lf_var, width=10).pack(side="left", fill="x", expand=True)
            def _pick_logo_file():
                path = filedialog.askopenfilename(
                    title="Logo-Datei wählen",
                    filetypes=[("Logo", "*.svg *.bmp *.mlg *.png *.jpg"),
                               ("Alle", "*.*")])
                if path:
                    lf_var.set(self._ensure_logo_in_dir(path))
                    dst = os.path.join(BASE_DIR, "res", "logos", os.path.basename(path))
                    self._read_logo_dims(obj, dst)
                    self._show_props(obj)
                    self._redraw()
            ttk.Button(lf_row, text="…", width=2,
                       command=_pick_logo_file).pack(side="left", padx=(2, 0))
            row[0] += 1
            for lt, at in [("Breite (px):", "logo_w"), ("Höhe (px):", "logo_h")]:
                v = tk.StringVar(value=str(getattr(obj, at)))
                def mkupd(a=at, vv=v):
                    def u(*_):
                        try: setattr(obj, a, int(vv.get())); self._redraw()
                        except: pass
                    return u
                v.trace_add("write", mkupd())
                lbl_entry(lt, v, width=6)

        elif obj.otype in ("line", "rect", "ellipse"):
            heading("Form — Startpunkt")
            for lt, at in [("X1 (Start):", "x"), ("Y1 (Start):", "y")]:
                var = tk.StringVar(value=str(getattr(obj, at)))
                def mkupd(a=at, v=var):
                    def u(*_):
                        try: setattr(obj, a, int(v.get())); self._redraw()
                        except: pass
                    return u
                var.trace_add("write", mkupd())
                lbl_entry(lt, var, width=8)
            heading("Form — Endpunkt")
            for lt, at in [("X2 (Ende):", "x2"), ("Y2 (Ende):", "y2")]:
                var = tk.StringVar(value=str(getattr(obj, at)))
                def mkupd(a=at, v=var):
                    def u(*_):
                        try: setattr(obj, a, int(v.get())); self._redraw()
                        except: pass
                    return u
                var.trace_add("write", mkupd())
                lbl_entry(lt, var, width=8)
            # Längen-Info
            dx = abs(obj.x2 - obj.x); dy = abs(obj.y2 - obj.y)
            tk.Label(f, text=f"Länge: {dx} × {dy} Strokes",
                     bg=utils.C["surface"], fg=utils.C["subtext"],
                     font=("Segoe UI", 8)).grid(
                row=row[0], column=0, columnspan=2, sticky="w", padx=4, pady=2)
            row[0] += 1
            sep()
            heading("Stil")
            lw_var = tk.StringVar(value=str(obj.lw))
            def upd_lw(*_):
                try: obj.lw = int(lw_var.get()); self._redraw()
                except: pass
            lw_var.trace_add("write", upd_lw)
            lbl_entry("Linienbreite:", lw_var, width=5)
            if obj.otype != "line":
                fill_var = tk.BooleanVar(value=bool(obj.fill))
                lbl_check("Gefuellt:", fill_var,
                          lambda: (setattr(obj, "fill", 1 if fill_var.get() else 0),
                                   self._redraw()))

        elif obj.otype in BARCODE_TYPES:
            heading("Barcode")
            bc_var = tk.StringVar(value=obj.otype)
            def upd_bc():
                obj.otype = bc_var.get(); self._redraw()
            lbl_combo("Typ:", bc_var, BARCODE_TYPES, upd_bc, 11)
            if obj.field_type == "static":
                txt_var = tk.StringVar(value=obj.text)
                def upd_txt(*_):
                    obj.text = txt_var.get(); self._redraw()
                txt_var.trace_add("write", upd_txt)
                lbl_entry("Inhalt:", txt_var, width=14)

        else:
            # Text-Inhalt (nur bei statisch)
            if obj.field_type == "static":
                heading("Text")
                txt_var = tk.StringVar(value=obj.text)
                def upd_txt(*_):
                    obj.text = txt_var.get(); self._redraw()
                txt_var.trace_add("write", upd_txt)
                lbl_entry("Inhalt:", txt_var, width=14)

        # ── Schrift ──
        if obj.otype not in ("line", "rect", "ellipse"):
            sep()
            heading("Schrift")
            face_var = tk.StringVar(value=obj.font_face)
            def upd_face():
                obj.font_face = face_var.get()
                obj.font_size = FONT_INFO.get(obj.font_face, (7,6,""))[0]
                self._redraw()
            lbl_combo("Schriftart:", face_var, AVAILABLE_FONTS, upd_face, 11)

            bold_var = tk.BooleanVar(value=obj.font_bold)
            lbl_check("Fett:", bold_var,
                      lambda: (setattr(obj, "font_bold", bold_var.get()), self._redraw()))
            it_var = tk.BooleanVar(value=obj.font_italic)
            lbl_check("Kursiv:", it_var,
                      lambda: (setattr(obj, "font_italic", it_var.get()), self._redraw()))

        sep()
        ttk.Button(f, text="  Anwenden", style="Green.TButton",
                   command=lambda: (self._redraw(), self._update_xml())).grid(
            row=row[0], column=0, columnspan=2, sticky="ew", padx=4, pady=4)

    def _change_field_type(self, obj, new_type):
        obj.field_type = new_type
        if new_type == "datafield" and obj.idx is None:
            used = {o.idx for o in self.objects if o.idx is not None}
            idx = 1
            while idx in used:
                idx += 1
            obj.idx = idx
        self._show_props(obj)
        self._redraw()

    def _sync_pos_fields(self):
        if not self.selected:
            return
        try:
            self._px_var.set(str(self.selected.x))
            self._py_var.set(str(self.selected.y))
        except Exception:
            pass

    # ── XML ───────────────────────────────────────────────────────────────────

    def _update_xml(self):
        xml = objects_to_gprint_xml(self.objects)
        self._xml_txt.config(state="normal")
        self._xml_txt.delete("1.0", "end")
        self._xml_txt.insert("end", xml)
        self._xml_txt.config(state="disabled")

    def _copy_xml(self):
        self.parent.clipboard_clear()
        self.parent.clipboard_append(objects_to_gprint_xml(self.objects))

    # ── Datei-Operationen ─────────────────────────────────────────────────────

    def _auto_detect_mode(self):
        if not self.objects:
            return
        max_bottom = max((obj.y + obj.approx_height() for obj in self.objects), default=0)
        if max_bottom <= 5:
            self._pm_var.set("pm05")
        elif max_bottom <= 7:
            self._pm_var.set("pm07")            
        elif max_bottom <= 15:
            self._pm_var.set("pm15")            
        elif max_bottom <= 25:
            self._pm_var.set("pm24")
        elif max_bottom <= 32:
            self._pm_var.set("pm32")
        else:
            self._pm_var.set("pm48")
        max_right = max((obj.x + obj.approx_width() for obj in self.objects), default=300)
        self._w_var.set(str(max(300, int(max_right) + 30)))

    def _new_label(self):
        if self.objects and not messagebox.askyesno("Neu", "Alle Objekte verwerfen?"):
            return
        self.objects  = []
        self.selected = None
        self.filename = ""
        self._file_lbl.config(text="")
        self._refresh_list()
        self._show_empty_props()
        self._redraw()

    def _open_label(self):
        path = filedialog.askopenfilename(
            title="Label oeffnen",
            initialdir=self.labels_dir,
            filetypes=[("Label-Dateien",
                        "*.txt *.TXT *.xml *.XML *.gp *.GP"),
                       ("Alle Dateien", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fp:
                content = fp.read()
            self.objects  = parse_gprint_xml(content)
            self.selected = None
            self.filename = os.path.basename(path)
            self._file_lbl.config(text=f"  {self.filename}")
            self._refresh_list()
            self._show_empty_props()
            self._auto_detect_mode()
            self._redraw()
            self.log(f"Label geladen: {self.filename}", "info")
        except Exception as e:
            messagebox.showerror("Fehler",
                                  f"Datei konnte nicht geladen werden:\n{e}")

    def _save_label(self):
        fn = self.filename
        if not fn:
            fn = simpledialog.askstring(
                "Speichern", "Dateiname:",
                initialvalue="label.txt", parent=self.parent)
            if not fn:
                return
            if not fn.lower().endswith((".txt", ".xml", ".gp")):
                fn += ".txt"
        path = os.path.join(self.labels_dir, fn)
        xml  = objects_to_gprint_xml(self.objects)
        with open(path, "w", encoding="utf-8") as fp:
            fp.write(xml)
        self.filename = fn
        self._file_lbl.config(text=f"  {fn}")
        self.log(f"Label gespeichert: {path}", "info")


# ─── Logo Editor Tab ──────────────────────────────────────────────────────────

class LogoEditorTab:
    """Einfacher Pixel-Logo-Editor (Paint-ähnlich). Speichert als SVG."""

    TOOLS = ["Stift", "Radierer", "Füllen", "Linie", "Rechteck"]
    

    def __init__(self, parent, run_cmd_fn=None, log_fn=None, logos_dir=None):
        self.parent    = parent
        self._run_cmd  = run_cmd_fn
        self._log      = log_fn or (lambda msg, *a: None)
        self._logos_dir = logos_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "res", "logos")
        os.makedirs(self._logos_dir, exist_ok=True)
        self._W       = 32
        self._H       = 10
        self._pixels  = set()          # (col, row) → schwarz
        self._cell    = 20             # canvas px pro Logopixel
        self._tool    = tk.StringVar(value="Stift")
        self._color   = "#000000"      # immer Schwarz (1-bit)
        self._drawing = False
        self._line_start = None        # für Linie/Rechteck-Tool
        self._temp_pixels = set()      # Vorschau-Pixel
        self._path    = ""
        self._build()

    def _build(self):
        p = self.parent

        # Toolbar
        tb = tk.Frame(p, bg=utils.C["header"])
        tb.pack(fill="x")
        self._build_toolbar(tb)

        # Canvas + Scrollbars
        cv_frame = tk.Frame(p, bg=utils.C["bg"])
        cv_frame.pack(fill="both", expand=True)

        h_sb = ttk.Scrollbar(cv_frame, orient="horizontal")
        h_sb.pack(side="bottom", fill="x")
        v_sb = ttk.Scrollbar(cv_frame, orient="vertical")
        v_sb.pack(side="right", fill="y")

        self._cv = tk.Canvas(cv_frame, bg=utils.C["bg"], highlightthickness=0,
                             xscrollcommand=h_sb.set, yscrollcommand=v_sb.set,
                             cursor="crosshair")
        self._cv.pack(fill="both", expand=True)
        h_sb.config(command=self._cv.xview)
        v_sb.config(command=self._cv.yview)

        self._cv.bind("<Button-1>",        self._on_press)
        self._cv.bind("<B1-Motion>",       self._on_drag)
        self._cv.bind("<ButtonRelease-1>", self._on_release)
        self._cv.bind("<Button-3>",        self._on_right)

        self._redraw()

    def _build_toolbar(self, tb):
        def lbl(t):
            tk.Label(tb, text=t, bg=utils.C["header"], fg=utils.C["subtext"],
                     font=("Segoe UI", 9)).pack(side="left", padx=(8, 3), pady=6)

        lbl("Breite:")
        self._w_var = tk.StringVar(value=str(self._W))
        ttk.Entry(tb, textvariable=self._w_var, width=4).pack(side="left", padx=(0, 4))
        lbl("Höhe:")
        self._h_var = tk.StringVar(value=str(self._H))
        ttk.Entry(tb, textvariable=self._h_var, width=4).pack(side="left", padx=(0, 4))
        ttk.Button(tb, text="Größe setzen", style="Orange.TButton",
                   command=self._apply_size).pack(side="left", padx=(0, 12))

        lbl("Zoom:")
        self._zoom_var = tk.StringVar(value="20")
        zc = ttk.Combobox(tb, textvariable=self._zoom_var,
                          values=["4","8","12","16","20","24","32"],
                          width=4, state="readonly")
        zc.pack(side="left", padx=(0, 8))
        zc.bind("<<ComboboxSelected>>",
                lambda e: (setattr(self, "_cell", int(self._zoom_var.get())),
                           self._redraw()))

        lbl("Werkzeug:")
        tc = ttk.Combobox(tb, textvariable=self._tool,
                          values=self.TOOLS, width=9, state="readonly")
        tc.pack(side="left", padx=(0, 12))

        ttk.Button(tb, text="Alles löschen", style="Red.TButton",
                   command=self._clear).pack(side="left", padx=2)
        ttk.Button(tb, text="Invertieren", style="Yellow.TButton",
                   command=self._invert).pack(side="left", padx=2)

        tk.Frame(tb, bg=utils.C["subtext"], width=1).pack(side="left", fill="y", padx=6, pady=4)

        ttk.Button(tb, text="Logo laden", style="Blue.TButton",
                   command=self._open_logo).pack(side="left", padx=2)
        ttk.Button(tb, text="Als MLG speichern", style="Green.TButton",
                   command=self._save_mlg).pack(side="left", padx=2)
        ttk.Button(tb, text="Als BMP speichern", style="Green.TButton",
                   command=self._save_bmp).pack(side="left", padx=2)
        ttk.Button(tb, text="Als PNG speichern", style="Green.TButton",
                   command=self._save_png).pack(side="left", padx=2)
        ttk.Button(tb, text="Als JPG speichern", style="Green.TButton",
                   command=self._save_jpg).pack(side="left", padx=2)

        self._pos_lbl = tk.Label(tb, text="", bg=utils.C["header"],
                                  fg=utils.C["subtext"], font=("Segoe UI", 8))
        self._pos_lbl.pack(side="right", padx=8)

    def _apply_size(self):
        try:
            w = max(1, min(256, int(self._w_var.get())))
            h = max(1, min(256, int(self._h_var.get())))
        except ValueError:
            return
        if (w != self._W or h != self._H):
            if self._pixels:
                if not messagebox.askyesno("Größe ändern",
                                           "Alle Pixel löschen und neue Größe setzen?"):
                    return
            self._W, self._H = w, h
            self._pixels.clear()
        self._redraw()

    def _cell_at(self, canvas_x, canvas_y):
        pad = 10
        c = int((canvas_x - pad) / self._cell)
        r = int((canvas_y - pad) / self._cell)
        if 0 <= c < self._W and 0 <= r < self._H:
            return (c, r)
        return None

    def _on_press(self, event):
        cx = self._cv.canvasx(event.x)
        cy = self._cv.canvasy(event.y)
        cell = self._cell_at(cx, cy)
        tool = self._tool.get()
        self._drawing = True
        self._line_start = cell

        if tool == "Stift" and cell:
            self._pixels.add(cell)
            self._redraw()
        elif tool == "Radierer" and cell:
            self._pixels.discard(cell)
            self._redraw()
        elif tool == "Füllen" and cell:
            self._flood_fill(cell, cell in self._pixels)
            self._redraw()

    def _on_drag(self, event):
        cx = self._cv.canvasx(event.x)
        cy = self._cv.canvasy(event.y)
        cell = self._cell_at(cx, cy)
        tool = self._tool.get()
        if cell:
            self._pos_lbl.config(text=f"X:{cell[0]}  Y:{cell[1]}")

        if not self._drawing:
            return

        if tool == "Stift" and cell:
            self._pixels.add(cell)
            self._redraw()
        elif tool == "Radierer" and cell:
            self._pixels.discard(cell)
            self._redraw()
        elif tool in ("Linie", "Rechteck") and self._line_start and cell:
            self._temp_pixels = self._preview_shape(self._line_start, cell, tool)
            self._redraw()

    def _on_release(self, event):
        if not self._drawing:
            return
        cx = self._cv.canvasx(event.x)
        cy = self._cv.canvasy(event.y)
        cell = self._cell_at(cx, cy)
        tool = self._tool.get()

        if tool in ("Linie", "Rechteck") and self._line_start and cell:
            self._pixels |= self._preview_shape(self._line_start, cell, tool)

        self._drawing = False
        self._line_start = None
        self._temp_pixels = set()
        self._redraw()

    def _on_right(self, event):
        cx = self._cv.canvasx(event.x)
        cy = self._cv.canvasy(event.y)
        cell = self._cell_at(cx, cy)
        if cell:
            self._pixels.discard(cell)
            self._redraw()

    def _preview_shape(self, start, end, tool):
        result = set()
        c0, r0 = start
        c1, r1 = end
        if tool == "Linie":
            # Bresenham
            dc = abs(c1 - c0); dr = abs(r1 - r0)
            sc = 1 if c1 > c0 else -1
            sr = 1 if r1 > r0 else -1
            c, r = c0, r0
            if dc > dr:
                err = dc // 2
                while c != c1:
                    result.add((c, r))
                    err -= dr
                    if err < 0:
                        r += sr; err += dc
                    c += sc
            else:
                err = dr // 2
                while r != r1:
                    result.add((c, r))
                    err -= dc
                    if err < 0:
                        c += sc; err += dr
                    r += sr
            result.add((c1, r1))
        elif tool == "Rechteck":
            min_c, max_c = min(c0, c1), max(c0, c1)
            min_r, max_r = min(r0, r1), max(r0, r1)
            for c in range(min_c, max_c + 1):
                result.add((c, min_r)); result.add((c, max_r))
            for r in range(min_r, max_r + 1):
                result.add((min_c, r)); result.add((max_c, r))
        return result

    def _flood_fill(self, start, erase):
        c0, r0 = start
        target = erase  # True = erase black, False = fill white
        if (c0, r0) in self._pixels != target:
            return
        stack = [(c0, r0)]
        visited = set()
        while stack:
            c, r = stack.pop()
            if (c, r) in visited or not (0 <= c < self._W and 0 <= r < self._H):
                continue
            if ((c, r) in self._pixels) != target:
                continue
            visited.add((c, r))
            if erase:
                self._pixels.discard((c, r))
            else:
                self._pixels.add((c, r))
            for dc, dr in ((1,0),(-1,0),(0,1),(0,-1)):
                stack.append((c+dc, r+dr))

    def _clear(self):
        if messagebox.askyesno("Löschen", "Alle Pixel löschen?"):
            self._pixels.clear()
            self._redraw()

    def _invert(self):
        all_cells = {(c, r) for c in range(self._W) for r in range(self._H)}
        self._pixels = all_cells - self._pixels
        self._redraw()

    def _redraw(self):
        pad  = 10
        cell = self._cell
        img_w = self._W * cell
        img_h = self._H * cell
        total_w = pad * 2 + img_w
        total_h = pad * 2 + img_h

        self._cv.delete("all")
        self._cv.config(scrollregion=(0, 0, total_w + 20, total_h + 20))

        # Äußerer Rahmen
        self._cv.create_rectangle(pad - 1, pad - 1,
                                   pad + img_w + 1, pad + img_h + 1,
                                   fill="", outline=utils.C["border"], width=1)

        try:
            from PIL import Image, ImageDraw, ImageTk

            # PIL-Bild in voller Canvas-Auflösung aufbauen
            img = Image.new("RGB", (img_w, img_h), (248, 248, 248))
            drw = ImageDraw.Draw(img)

            # Schachbrett-Hintergrund (zeigt Transparenz)
            tile = 8
            for gy in range(0, img_h, tile):
                for gx in range(0, img_w, tile):
                    if (gx // tile + gy // tile) % 2 == 0:
                        drw.rectangle([gx, gy, gx + tile - 1, gy + tile - 1],
                                       fill=(240, 240, 240))
                    else:
                        drw.rectangle([gx, gy, gx + tile - 1, gy + tile - 1],
                                       fill=(255, 255, 255))

            # Gitter-Linien (nur bei cell >= 4)
            if cell >= 4:
                gc = (210, 210, 210)
                for c in range(self._W + 1):
                    x = c * cell
                    drw.line([(x, 0), (x, img_h)], fill=gc, width=1)
                for r in range(self._H + 1):
                    y = r * cell
                    drw.line([(0, y), (img_w, y)], fill=gc, width=1)

            # Gesetzte Pixel — schwarz
            for (c, r) in self._pixels:
                x1 = c * cell + 1
                y1 = r * cell + 1
                x2 = x1 + cell - 2
                y2 = y1 + cell - 2
                drw.rectangle([x1, y1, x2, y2], fill=(20, 20, 20))

            # Vorschau-Pixel (Linie/Rechteck) — grau
            for (c, r) in self._temp_pixels:
                if (c, r) not in self._pixels:
                    x1 = c * cell + 1
                    y1 = r * cell + 1
                    x2 = x1 + cell - 2
                    y2 = y1 + cell - 2
                    drw.rectangle([x1, y1, x2, y2], fill=(120, 120, 120))

            photo = ImageTk.PhotoImage(img)
            if not hasattr(self, "_logo_photo_ref"):
                self._logo_photo_ref = None
            self._logo_photo_ref = photo
            self._cv.create_image(pad, pad, image=photo, anchor="nw")

        except ImportError:
            # Fallback ohne PIL — einzelne Rechtecke
            self._cv.create_rectangle(pad, pad, pad + img_w, pad + img_h,
                                       fill="#ffffff", outline="#888888")
            if cell >= 4:
                for c in range(self._W + 1):
                    x = pad + c * cell
                    self._cv.create_line(x, pad, x, pad + img_h,
                                          fill="#e0e0e0", width=1)
                for r in range(self._H + 1):
                    y = pad + r * cell
                    self._cv.create_line(pad, y, pad + img_w, y,
                                          fill="#e0e0e0", width=1)
            for (c, r) in self._pixels:
                x1 = pad + c * cell
                y1 = pad + r * cell
                self._cv.create_rectangle(x1, y1, x1 + cell, y1 + cell,
                                           fill="#141414", outline="")
            for (c, r) in self._temp_pixels:
                x1 = pad + c * cell
                y1 = pad + r * cell
                self._cv.create_rectangle(x1, y1, x1 + cell, y1 + cell,
                                           fill="#808080", outline="")

        # Info-Zeile oben links
        self._cv.create_text(pad, pad - 5,
                              text=f"{self._W} × {self._H} px  ·  {len(self._pixels)} Pixel gesetzt",
                              fill=utils.C["subtext"], font=("Segoe UI", 8), anchor="sw")

    def _save_mlg(self):
        path = filedialog.asksaveasfilename(
            title="Logo als MLG speichern",
            defaultextension=".mlg",
            filetypes=[("MLG-Dateien", "*.mlg"), ("Alle Dateien", "*.*")],
            initialdir=self._logos_dir,
            initialfile=os.path.splitext(os.path.basename(self._path))[0] + ".mlg"
            if self._path else "logo.mlg")
        if not path:
            return
        # cgrafic-Format (das die alphaJET-Drucker erwarten):
        #   11-Byte-Header  [Breite uint16 LE, Höhe uint16 LE, Signatur 00 00 01 00 01 00 00]
        #   Pixel spaltenweise, ceil(h/8) Bytes je Spalte, LSB-first, Zeile 0 = UNTEN.
        # Der Editor hält Pixel mit Zeile 0 = oben → beim Schreiben vertikal spiegeln.
        w, h = self._W, self._H
        bpc = (h + 7) // 8
        data = bytearray([w & 0xFF, (w >> 8) & 0xFF,
                          h & 0xFF, (h >> 8) & 0xFF,
                          0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00])
        for col in range(w):
            for bi in range(bpc):
                byte = 0
                for bit in range(8):
                    row = bi * 8 + bit
                    if row < h and (col, h - 1 - row) in self._pixels:
                        byte |= (1 << bit)
                data.append(byte)
        with open(path, "wb") as f:
            f.write(data)
        self._path = path
        messagebox.showinfo("Gespeichert",
                            f"MLG gespeichert (cgrafic-Format, {w}×{h}):\n{path}")

    def _save_bmp(self):
        try:
            from PIL import Image
        except ImportError:
            messagebox.showerror("Pillow fehlt",
                "BMP-Export benötigt Pillow.\nInstallation: pip install pillow")
            return
        path = filedialog.asksaveasfilename(
            title="Logo als BMP speichern",
            defaultextension=".bmp",
            filetypes=[("BMP-Dateien", "*.bmp *.BMP"), ("Alle Dateien", "*.*")],
            initialdir=self._logos_dir,
            initialfile=os.path.splitext(os.path.basename(self._path))[0] + ".bmp"
            if self._path else "logo.bmp")
        if not path:
            return
        img = Image.new("RGB", (self._W, self._H), (255, 255, 255))
        for (c, r) in self._pixels:
            if 0 <= c < self._W and 0 <= r < self._H:
                img.putpixel((c, r), (0, 0, 0))
        img.save(path, quality=95)
        messagebox.showinfo("Gespeichert", f"JPG gespeichert:\n{path}")       

    def _save_png(self):
        try:
            from PIL import Image
        except ImportError:
            messagebox.showerror("Pillow fehlt",
                "PNG-Export benötigt Pillow.\nInstallation: pip install pillow")
            return
        path = filedialog.asksaveasfilename(
            title="Logo als PNG speichern",
            defaultextension=".png",
            filetypes=[("PNG-Dateien", "*.png"), ("Alle Dateien", "*.*")],
            initialdir=self._logos_dir,
            initialfile=os.path.splitext(os.path.basename(self._path))[0] + ".png"
            if self._path else "logo.png")
        if not path:
            return
        img = Image.new("RGBA", (self._W, self._H), (255, 255, 255, 0))
        for (c, r) in self._pixels:
            if 0 <= c < self._W and 0 <= r < self._H:
                img.putpixel((c, r), (0, 0, 0, 255))
        img.save(path)
        messagebox.showinfo("Gespeichert", f"PNG gespeichert:\n{path}")

    def _save_jpg(self):
        try:
            from PIL import Image
        except ImportError:
            messagebox.showerror("Pillow fehlt",
                "JPG-Export benötigt Pillow.\nInstallation: pip install pillow")
            return
        path = filedialog.asksaveasfilename(
            title="Logo als JPG speichern",
            defaultextension=".jpg",
            filetypes=[("JPG-Dateien", "*.jpg *.jpeg"), ("Alle Dateien", "*.*")],
            initialdir=self._logos_dir,
            initialfile=os.path.splitext(os.path.basename(self._path))[0] + ".jpg"
            if self._path else "logo.jpg")
        if not path:
            return
        img = Image.new("RGB", (self._W, self._H), (255, 255, 255))
        for (c, r) in self._pixels:
            if 0 <= c < self._W and 0 <= r < self._H:
                img.putpixel((c, r), (0, 0, 0))
        img.save(path, quality=95)
        messagebox.showinfo("Gespeichert", f"JPG gespeichert:\n{path}")

    def load_from_path(self, path):
        """Logo direkt von einem Pfad laden (ohne Dateidialog). Gibt True bei Erfolg."""
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == ".svg":
                self._load_svg(path)
            elif ext == ".mlg":
                self._load_mlg(path)
            else:
                self._load_bitmap(path)
            self._path = path
            self._w_var.set(str(self._W))
            self._h_var.set(str(self._H))
            self._redraw()
            return True
        except Exception as e:
            messagebox.showerror("Fehler", f"Logo konnte nicht geladen werden:\n{e}")
            return False

    def _open_logo(self):
        path = filedialog.askopenfilename(
            title="Logo laden",
            initialdir=self._logos_dir,
            filetypes=[
                ("Alle unterstützten Formate", "*.svg *.png *.bmp *.gif *.jpg *.jpeg *.mlg"),
                ("Bitmap",        "*.png *.bmp *.gif *.jpg *.jpeg"),
                ("MLG-Dateien",   "*.mlg"),
                ("Alle Dateien",  "*.*"),
            ])
        if not path:
            return
        self.load_from_path(path)

    def _load_svg(self, path):
        import xml.etree.ElementTree as ET
        root = ET.parse(path).getroot()
        vb = root.get("viewBox", "")
        if vb:
            parts = vb.split()
            if len(parts) == 4:
                self._W = int(float(parts[2]))
                self._H = int(float(parts[3]))
        else:
            w = root.get("width"); h = root.get("height")
            if w: self._W = int(float(w.replace("px","")))
            if h: self._H = int(float(h.replace("px","")))
        self._pixels.clear()
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag == "rect":
                fill = elem.get("fill", "")
                if fill.lower() in ("black", "#000000", "#000"):
                    x = int(float(elem.get("x", 0)))
                    y = int(float(elem.get("y", 0)))
                    w = int(float(elem.get("width",  1)))
                    h = int(float(elem.get("height", 1)))
                    for dc in range(w):
                        for dr in range(h):
                            self._pixels.add((x+dc, y+dr))

    @staticmethod
    def _mlg_decode(path, hint_h=None):
        """
        MLG-Binärformat dekodieren. Spaltenweise (column-major), ceil(h/8) Bytes/Spalte.
        Zwei Varianten werden automatisch erkannt:

          • cgrafic (BMP→MLG-Konverter, von unseren Druckern gelesen):
              11-Byte-Header: [0:2]=Breite uint16 LE, [2:4]=Höhe uint16 LE,
              [4:11]=Signatur 00 00 01 00 01 00 00.
              Pixel: LSB-first, Zeile 0 = UNTEN (wird hier vertikal gespiegelt,
              damit der Editor mit Zeile 0 = oben das Logo aufrecht zeigt).
          • Editor-eigen (_save_mlg) / Legacy:
              3-Byte-Header [00, 00, Höhe]. Bit-Reihenfolge: MSB = oberste Zeile.

        hint_h: bekannte Druckerhöhe — nur für die Legacy-Variante als Fallback.
        Gibt (pixel_set, width, height) zurück.
        """
        import struct
        COMMON_H = [8, 16, 24, 32, 48, 64]
        with open(path, "rb") as fp:
            data = fp.read()
        if len(data) < 3:
            return set(), 1, 1

        # ── Variante cgrafic: 11-Byte-Header mit expliziter Breite/Höhe ──
        # Selbst-validierend: Breite > 0 und Dateigröße passt exakt → eindeutig.
        if len(data) >= 11:
            w = struct.unpack_from("<H", data, 0)[0]
            h = struct.unpack_from("<H", data, 2)[0]
            if w > 0 and 0 < h <= 256:
                bpc = (h + 7) // 8
                if 11 + w * bpc == len(data):
                    payload = data[11:]
                    pixels  = set()
                    for col in range(w):
                        base = col * bpc
                        for bi in range(bpc):
                            byte = payload[base + bi]
                            if not byte:
                                continue
                            for bit in range(8):
                                row = bi * 8 + bit
                                # MLG speichert Zeile 0 = UNTEN → vertikal spiegeln,
                                # damit der Pixel-Editor (Zeile 0 = oben) es aufrecht zeigt.
                                if row < h and (byte >> bit) & 1:
                                    pixels.add((col, h - 1 - row))
                    return pixels, w, h

        # ── Variante Editor / Legacy: 3-Byte-Header [00,00,Höhe], MSB-first ──
        height  = None
        payload = data

        # 1. Header-Byte[2] = Höhe (das Format aus _save_mlg)
        h_cand = data[2]
        if h_cand in COMMON_H:
            bpc_cand  = h_cand // 8
            remaining = len(data) - 3
            if remaining > 0 and remaining % bpc_cand == 0:
                height  = h_cand
                payload = data[3:]

        # 2. hint_h verwenden wenn Header nichts liefert
        if height is None and hint_h in COMMON_H:
            bpc_cand = hint_h // 8
            if len(data) % bpc_cand == 0:
                height  = hint_h
                payload = data

        # 3. Fallback: bevorzuge 32 (häufigste Druckerhöhe), dann absteigend
        if height is None:
            for h in [32, 48, 24, 16, 64, 8]:
                if len(data) % (h // 8) == 0:
                    height = h
                    break
        if height is None:
            height = 32

        bpc   = height // 8
        width = len(payload) // bpc
        if width == 0:
            return set(), 1, height

        pixels = set()
        for col in range(width):
            for bi in range(bpc):
                idx = col * bpc + bi
                if idx >= len(payload):
                    break
                byte = payload[idx]
                for bit in range(8):
                    row = bi * 8 + bit
                    if row < height and (byte >> (7 - bit)) & 1:   # MSB = oberste Zeile
                        pixels.add((col, row))
        return pixels, width, height

    def _load_mlg(self, path):
        """MLG binäres Format in den Pixel-Editor laden."""
        self._pixels.clear()
        self._pixels, self._W, self._H = LogoEditorTab._mlg_decode(path)

    def _load_bitmap(self, path):
        """PNG/BMP/GIF/JPG laden — konvertiert zu 1-bit (Schwellenwert 128)."""
        try:
            from PIL import Image
        except ImportError:
            messagebox.showerror(
                "Pillow fehlt",
                "Für PNG/BMP/JPG wird die Pillow-Bibliothek benötigt.\n"
                "Installation: pip install pillow")
            return
        img = Image.open(path).convert("L")  # Graustufen
        self._W, self._H = img.width, img.height
        self._pixels.clear()
        for r in range(self._H):
            for c in range(self._W):
                if img.getpixel((c, r)) < 128:
                    self._pixels.add((c, r))

    def _send_to_printer(self):
        if not self._run_cmd:
            messagebox.showwarning("Nicht verfügbar",
                                   "Kein Drucker verbunden.\n"
                                   "(run_cmd-Funktion nicht übergeben)")
            return
        if not self._pixels:
            messagebox.showwarning("Leer", "Keine Pixel gesetzt.")
            return
        fn = simpledialog.askstring(
            "An Drucker senden",
            "Dateiname auf dem Drucker (.svg):",
            initialvalue=os.path.basename(self._path) if self._path else "logo.svg",
            parent=self.parent)
        if not fn:
            return
        if not fn.lower().endswith(".svg"):
            fn += ".svg"
        # SVG als String zusammenbauen
        svg_lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg"'
            f' width="{self._W}" height="{self._H}"'
            f' viewBox="0 0 {self._W} {self._H}">',
            f'<rect width="{self._W}" height="{self._H}" fill="white"/>',
        ]
        for (c, r) in sorted(self._pixels):
            svg_lines.append(
                f'<rect x="{c}" y="{r}" width="1" height="1" fill="black"/>')
        svg_lines.append("</svg>")
        svg_content = "".join(svg_lines)
        # SAVESVG-Befehl — analog zu SAVELAB
        cmd = (f'<GP><SAVESVG aName="logo\\{fn}">'
               f'<![CDATA[{svg_content}]]>'
               f'</SAVESVG></GP>')
        self._run_cmd(cmd, f"Logo → Drucker: {fn}")
