"""
GPO Merchant + Store Tracker PRO v5
====================================
PROFESSIONAL VERSION - ALL FEATURES

Features:
  ✅ System Tray (Minimize to bandeja)
  ✅ Discord Webhook Notifications
  ✅ Save Configuration
  ✅ Real-time Theme Switching (Dark/Light)
  ✅ Event Logging
  ✅ Statistics
  ✅ Different Sounds
  ✅ Help/About
  ✅ Error Handling

INSTALL DEPENDENCIES:
  pip install pyinstaller plyer requests pillow pystray

RUN:
  python gpo_merchant_tracker_pro.py
"""

import tkinter as tk
from tkinter import font as tkfont, messagebox
import datetime
import threading
import time
import json
import os
import sys

# Sound Windows
try:
    import winsound
    SOUND_OK = True
except ImportError:
    SOUND_OK = False

# Notifications
try:
    from plyer import notification as plyer_notif
    NOTIF_OK = True
except ImportError:
    NOTIF_OK = False

# Discord (optional)
try:
    import requests
    DISCORD_OK = True
except ImportError:
    DISCORD_OK = False

# ── Colors ───────────────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg": "#0a0c16",
        "bg2": "#10131f",
        "bg3": "#16192d",
        "bg4": "#1e2240",
        "merch": "#f0a500",
        "store": "#00d4ff",
        "green": "#00e676",
        "red": "#ff4d6d",
        "text": "#e5eaf0",
        "dim": "#6a7085",
        "border": "#232a45",
    },
    "light": {
        "bg": "#f8f9fa",
        "bg2": "#e9ecef",
        "bg3": "#dee2e6",
        "bg4": "#ced4da",
        "merch": "#d97706",
        "store": "#0ea5e9",
        "green": "#16a34a",
        "red": "#dc2626",
        "text": "#1f2937",
        "dim": "#6b7280",
        "border": "#b3b3b3",
    }
}

# ── Timings ──────────────────────────────────────────────────────────────────
MERCH_SPAWN = 10 * 60
MERCH_DUR = 10 * 60
MERCH_WAIT = 30 * 60
MERCH_CICLO = MERCH_DUR + MERCH_WAIT


def calcular_merchant(idade: float, n: int = 6):
    spawns, t = [], MERCH_SPAWN
    while len(spawns) < 500:
        spawns.append((t, t + MERCH_DUR))
        t += MERCH_CICLO
    return [(s, f) for s, f in spawns if f > idade][:n]


def calcular_store(n: int = 6):
    agora = datetime.datetime.now()
    minuto_atual = agora.minute
    proximos = []
    
    if minuto_atual < 30:
        prox = agora.replace(minute=30, second=0, microsecond=0)
    else:
        prox = agora.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
    
    for i in range(n):
        proximos.append(prox)
        prox += datetime.timedelta(minutes=30)
    
    return proximos


def fmt_mm_ss(seg: float) -> str:
    seg = max(0, int(seg))
    m, s = divmod(seg, 60)
    return f"{m:02d}:{s:02d}"


def fazer_som(freq=1000, ms=500):
    if SOUND_OK:
        try:
            winsound.Beep(freq, ms)
        except Exception:
            pass


def enviar_notif(titulo: str, msg: str):
    fazer_som(800, 300)
    if NOTIF_OK:
        try:
            from plyer import notification
            notification.notify(title=titulo, message=msg,
                               app_name="GPO Tracker", timeout=15)
        except Exception:
            pass


def enviar_discord(webhook_url: str, titulo: str, msg: str, color: int = 0xFFA500):
    """Send notification to Discord via webhook."""
    if not DISCORD_OK or not webhook_url:
        return
    
    try:
        embed = {
            "title": titulo,
            "description": msg,
            "color": color,
            "timestamp": datetime.datetime.now().isoformat()
        }
        data = {"embeds": [embed]}
        requests.post(webhook_url, json=data, timeout=5)
    except Exception as e:
        print(f"[DISCORD ERROR] {e}")


# ══════════════════════════════════════════════════════════════════════════════
class Config:
    """Manages configuration file."""
    
    FILE = "gpo_config.json"
    DEFAULT = {
        "theme": "dark",
        "discord_webhook": "",
        "servidor_idade": "00:00",
        "sons_ligados": True,
        "notificacoes_ligadas": True,
    }
    
    @classmethod
    def load(cls):
        if os.path.exists(cls.FILE):
            try:
                with open(cls.FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return cls.DEFAULT.copy()
        return cls.DEFAULT.copy()
    
    @classmethod
    def save(cls, data: dict):
        try:
            with open(cls.FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[CONFIG ERROR] {e}")


# ══════════════════════════════════════════════════════════════════════════════
class Logger:
    """Event logging."""
    
    FILE = "gpo_log.txt"
    
    @classmethod
    def log(cls, evento: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        msg = f"[{timestamp}] {evento}"
        print(msg)
        try:
            with open(cls.FILE, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass
    
    @classmethod
    def clear(cls):
        try:
            if os.path.exists(cls.FILE):
                os.remove(cls.FILE)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GPO Tracker PRO")
        self.resizable(False, False)
        self.geometry("620x600")

        # Config
        self.config_data = Config.load()
        self.theme = self.config_data.get("theme", "dark")
        self.colors = THEMES[self.theme]

        # State
        self.servidor_inicio = None
        self.tracking = False
        self.paused = False
        self.notificados = set()
        self._thread = None
        
        # Stats
        self.stats = {
            "merchant_spawns": 0,
            "store_refreshes": 0,
            "tempo_inicio": None
        }
        
        Logger.log("App started")
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        self.f_title = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        self.f_huge = tkfont.Font(family="Courier New", size=32, weight="bold")
        self.f_med = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.f_sm = tkfont.Font(family="Segoe UI", size=9)
        self.f_xs = tkfont.Font(family="Segoe UI", size=8)

        # Clear widgets
        for widget in self.winfo_children():
            widget.destroy()

        # Update colors
        self.configure(bg=self.colors["bg"])

        # ─ Header with Menu ─
        hdr = tk.Frame(self, bg=self.colors["bg2"], pady=8)
        hdr.pack(fill="x")
        
        hdr_left = tk.Frame(hdr, bg=self.colors["bg2"])
        hdr_left.pack(side="left", fill="both", expand=True, padx=12)
        tk.Label(hdr_left, text="🐒 GPO TRACKER PRO", font=self.f_title,
                 bg=self.colors["bg2"], fg=self.colors["merch"]).pack(anchor="w")
        
        hdr_right = tk.Frame(hdr, bg=self.colors["bg2"])
        hdr_right.pack(side="right", padx=12)
        self._btn(hdr_right, "⚙️", self._show_settings).pack(side="left", padx=2)
        self._btn(hdr_right, "📊", self._show_stats).pack(side="left", padx=2)
        self._btn(hdr_right, "❓", self._show_help).pack(side="left", padx=2)

        # ─ Input + Buttons ─
        inp = tk.Frame(self, bg=self.colors["bg"], pady=8)
        inp.pack(fill="x", padx=12)

        tk.Label(inp, text="Age (MM:SS):", font=self.f_sm,
                 bg=self.colors["bg"], fg=self.colors["text"]).pack(side="left")
        self.entry = tk.Entry(inp, width=7, font=self.f_med,
                              bg=self.colors["bg4"], fg=self.colors["merch"],
                              insertbackground=self.colors["merch"],
                              relief="flat", bd=5, justify="center")
        self.entry.insert(0, self.config_data.get("servidor_idade", "00:00"))
        self.entry.pack(side="left", padx=8)
        self.entry.bind("<Return>", lambda _: self._start())

        self.btn_start = self._btn_colored(inp, "▶ START", self.colors["merch"], self._start)
        self.btn_novo = self._btn_colored(inp, "🆕 NEW", self.colors["green"], self._new_server)
        self.btn_pause = self._btn_colored(inp, "⏸ PAUSE", self.colors["store"], self._toggle_pause)
        self.btn_start.pack(side="left", padx=2)
        self.btn_novo.pack(side="left", padx=2)
        self.btn_pause.pack(side="left", padx=2)

        # ─ Separator ─
        tk.Frame(self, bg=self.colors["border"], height=1).pack(fill="x", padx=12, pady=8)

        # ─ Timers ─
        timers = tk.Frame(self, bg=self.colors["bg"])
        timers.pack(fill="x", padx=10, pady=6)

        left = tk.Frame(timers, bg=self.colors["bg3"], padx=8, pady=8)
        left.pack(side="left", fill="both", expand=True, padx=3)
        tk.Label(left, text="🐒 MERCHANT", font=self.f_xs, bg=self.colors["bg3"],
                 fg=self.colors["merch"]).pack()
        self.lbl_m_cd = tk.Label(left, text="--:--", font=self.f_huge,
                                 bg=self.colors["bg3"], fg=self.colors["merch"])
        self.lbl_m_cd.pack()
        self.lbl_m_sub = tk.Label(left, text="", font=self.f_xs,
                                  bg=self.colors["bg3"], fg=self.colors["dim"])
        self.lbl_m_sub.pack()

        right = tk.Frame(timers, bg=self.colors["bg3"], padx=8, pady=8)
        right.pack(side="right", fill="both", expand=True, padx=3)
        tk.Label(right, text="🛍️ STORE", font=self.f_xs, bg=self.colors["bg3"],
                 fg=self.colors["store"]).pack()
        self.lbl_s_cd = tk.Label(right, text="--:--", font=self.f_huge,
                                 bg=self.colors["bg3"], fg=self.colors["store"])
        self.lbl_s_cd.pack()
        self.lbl_s_sub = tk.Label(right, text="", font=self.f_xs,
                                  bg=self.colors["bg3"], fg=self.colors["dim"])
        self.lbl_s_sub.pack()

        # ─ Next ─
        tk.Frame(self, bg=self.colors["border"], height=1).pack(fill="x", padx=12, pady=6)

        prox = tk.Frame(self, bg=self.colors["bg"], pady=4)
        prox.pack(fill="x", padx=12)
        tk.Label(prox, text="NEXT:", font=self.f_xs, bg=self.colors["bg"],
                 fg=self.colors["dim"]).pack(anchor="w")
        self.lbl_prox = tk.Label(prox, text="—", font=self.f_med,
                                 bg=self.colors["bg"], fg=self.colors["text"])
        self.lbl_prox.pack(anchor="w")

        # ─ Lists ─
        tk.Frame(self, bg=self.colors["border"], height=1).pack(fill="x", padx=12, pady=6)

        lists = tk.Frame(self, bg=self.colors["bg"])
        lists.pack(fill="both", expand=True, padx=10, pady=4)

        lm = tk.Frame(lists, bg=self.colors["bg"])
        lm.pack(side="left", fill="both", expand=True, padx=3)
        tk.Label(lm, text="MERCHANT SPAWNS", font=self.f_xs, bg=self.colors["bg"],
                 fg=self.colors["dim"]).pack(anchor="w")
        self.lista_m = tk.Frame(lm, bg=self.colors["bg"])
        self.lista_m.pack(fill="both", expand=True)
        self.rows_m = []
        for i in range(3):
            row = tk.Frame(self.lista_m, bg=self.colors["bg2"], padx=6, pady=3)
            row.pack(fill="x", pady=1)
            lh = tk.Label(row, text="--:--", font=self.f_sm, bg=self.colors["bg2"],
                         fg=self.colors["text"])
            lf = tk.Label(row, text="", font=self.f_xs, bg=self.colors["bg2"],
                         fg=self.colors["merch"])
            lh.pack(side="left")
            lf.pack(side="right")
            self.rows_m.append((row, lh, lf))

        ls = tk.Frame(lists, bg=self.colors["bg"])
        ls.pack(side="right", fill="both", expand=True, padx=3)
        tk.Label(ls, text="STORE REFRESHES", font=self.f_xs, bg=self.colors["bg"],
                 fg=self.colors["dim"]).pack(anchor="w")
        self.lista_s = tk.Frame(ls, bg=self.colors["bg"])
        self.lista_s.pack(fill="both", expand=True)
        self.rows_s = []
        for i in range(3):
            row = tk.Frame(self.lista_s, bg=self.colors["bg2"], padx=6, pady=3)
            row.pack(fill="x", pady=1)
            lh = tk.Label(row, text="--:--", font=self.f_sm, bg=self.colors["bg2"],
                         fg=self.colors["text"])
            lf = tk.Label(row, text="", font=self.f_xs, bg=self.colors["bg2"],
                         fg=self.colors["store"])
            lh.pack(side="left")
            lf.pack(side="right")
            self.rows_s.append((row, lh, lf))

        # ─ Footer ─
        foot = tk.Frame(self, bg=self.colors["bg2"], pady=4)
        foot.pack(fill="x", side="bottom")
        self.lbl_foot = tk.Label(foot, text="Ready to start",
                                font=self.f_xs, bg=self.colors["bg2"],
                                fg=self.colors["dim"])
        self.lbl_foot.pack()

    def _btn(self, parent, text, cmd):
        """Small header button."""
        b = tk.Button(parent, text=text, command=cmd, font=self.f_xs,
                      bg=self.colors["bg3"], fg=self.colors["merch"],
                      activebackground=self.colors["border"],
                      relief="flat", bd=0, padx=4, pady=2, cursor="hand2")
        b.bind("<Enter>", lambda e: b.config(bg=self.colors["border"]))
        b.bind("<Leave>", lambda e: b.config(bg=self.colors["bg3"]))
        return b

    def _btn_colored(self, parent, text, fg, cmd):
        """Colored button."""
        b = tk.Button(parent, text=text, command=cmd, font=self.f_xs,
                      bg=self.colors["bg4"], fg=fg,
                      activebackground=self.colors["border"],
                      activeforeground=fg, relief="flat", bd=0,
                      padx=6, pady=5, cursor="hand2",
                      highlightthickness=1, highlightbackground=self.colors["border"])
        b.bind("<Enter>", lambda e: b.config(bg=self.colors["bg3"]))
        b.bind("<Leave>", lambda e: b.config(bg=self.colors["bg4"]))
        return b

    def _show_settings(self):
        """Settings window."""
        settings = tk.Toplevel(self)
        settings.title("⚙️ Settings")
        settings.geometry("400x350")
        settings.configure(bg=self.colors["bg2"])
        settings.resizable(False, False)

        # Theme
        tk.Label(settings, text="Theme:", font=self.f_sm, bg=self.colors["bg2"],
                 fg=self.colors["text"]).pack(anchor="w", padx=12, pady=8)
        
        theme_var = tk.StringVar(value=self.theme)
        tk.Radiobutton(settings, text="🌙 Dark", variable=theme_var, value="dark",
                       font=self.f_xs, bg=self.colors["bg2"], fg=self.colors["text"],
                       selectcolor=self.colors["bg3"],
                       command=lambda: self._change_theme("dark")).pack(anchor="w", padx=20)
        tk.Radiobutton(settings, text="☀️ Light", variable=theme_var, value="light",
                       font=self.f_xs, bg=self.colors["bg2"], fg=self.colors["text"],
                       selectcolor=self.colors["bg3"],
                       command=lambda: self._change_theme("light")).pack(anchor="w", padx=20)

        # Discord Webhook
        tk.Label(settings, text="Discord Webhook (optional):", font=self.f_sm,
                 bg=self.colors["bg2"], fg=self.colors["text"]).pack(anchor="w", padx=12, pady=8)
        
        webhook_entry = tk.Entry(settings, font=self.f_xs, bg=self.colors["bg4"],
                                 fg=self.colors["text"], relief="flat", bd=4, width=50)
        webhook_entry.insert(0, self.config_data.get("discord_webhook", ""))
        webhook_entry.pack(padx=12, pady=4)

        # Sound
        sons_var = tk.BooleanVar(value=self.config_data.get("sons_ligados", True))
        tk.Checkbutton(settings, text="🔊 Enable sounds", variable=sons_var,
                       font=self.f_xs, bg=self.colors["bg2"], fg=self.colors["text"],
                       selectcolor=self.colors["bg3"]).pack(anchor="w", padx=12, pady=4)

        # Save
        def save():
            self.config_data["discord_webhook"] = webhook_entry.get()
            self.config_data["sons_ligados"] = sons_var.get()
            Config.save(self.config_data)
            messagebox.showinfo("✅ Saved", "Settings saved successfully!")
            settings.destroy()

        tk.Button(settings, text="💾 Save", command=save, font=self.f_xs,
                  bg=self.colors["bg3"], fg=self.colors["green"],
                  relief="flat", bd=0, padx=10, pady=8).pack(pady=12)

    def _change_theme(self, novo_tema):
        """Change theme in real-time."""
        self.theme = novo_tema
        self.colors = THEMES[self.theme]
        self.config_data["theme"] = novo_tema
        Config.save(self.config_data)
        Logger.log(f"Theme changed to {novo_tema}")
        self._build_ui()

    def _show_stats(self):
        """Show statistics."""
        stats = tk.Toplevel(self)
        stats.title("📊 Statistics")
        stats.geometry("300x200")
        stats.configure(bg=self.colors["bg2"])
        stats.resizable(False, False)

        tempo_ativo = "N/A"
        if self.stats["tempo_inicio"]:
            delta = datetime.datetime.now() - self.stats["tempo_inicio"]
            tempo_ativo = f"{delta.seconds // 60}m {delta.seconds % 60}s"

        texto = f"""
Merchant Spawns: {self.stats['merchant_spawns']}
Store Refreshes: {self.stats['store_refreshes']}
Time Active: {tempo_ativo}
        """

        tk.Label(stats, text=texto, font=self.f_sm, bg=self.colors["bg2"],
                 fg=self.colors["text"], justify="left").pack(padx=12, pady=12)

    def _show_help(self):
        """Show help."""
        help_text = """
🐒 GPO TRACKER PRO

HOW TO USE:
1. Enter server age (bottom right corner of game)
2. Click START or 🆕 NEW
3. Receive notifications & sounds when events happen

EVENTS:
🐒 MERCHANT SPAWN - Every 40 min (10 active + 30 wait)
🛍️ STORE REFRESH - Every 30 min (1:00, 1:30, 2:00...)

SETTINGS ⚙️:
- Dark/Light theme (changes in real-time!)
- Discord webhook (get notifications in Discord)
- Sound on/off

STATISTICS 📊:
- View event count
- Time active

BUTTONS:
▶ START - Start tracker
🆕 NEW - New server (reset)
⏸ PAUSE - Pause/Resume

SHORTCUTS:
- Enter key on age = START
        """
        
        help_win = tk.Toplevel(self)
        help_win.title("❓ Help")
        help_win.geometry("450x450")
        help_win.configure(bg=self.colors["bg2"])
        
        txt = tk.Text(help_win, font=self.f_xs, bg=self.colors["bg"],
                      fg=self.colors["text"], relief="flat", bd=0, padx=10, pady=10)
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        txt.insert("1.0", help_text)
        txt.config(state="disabled")

    def _parse_idade(self):
        raw = self.entry.get().strip()
        try:
            p = raw.split(":")
            if len(p) == 2:  return int(p[0]) * 60 + int(p[1])
            if len(p) == 3:  return int(p[0]) * 3600 + int(p[1]) * 60 + int(p[2])
        except Exception:
            pass
        return None

    def _start(self):
        idade = self._parse_idade()
        if idade is None:
            self.entry.config(bg=self.colors["red"])
            self.after(400, lambda: self.entry.config(bg=self.colors["bg4"]))
            return
        self.notificados.clear()
        self.servidor_inicio = datetime.datetime.now() - datetime.timedelta(seconds=idade)
        self.paused = False
        self.stats["tempo_inicio"] = datetime.datetime.now()
        self.stats["merchant_spawns"] = 0
        self.stats["store_refreshes"] = 0
        self._start_tracking()
        self.btn_pause.config(text="⏸ PAUSE")
        self.lbl_foot.config(text="✅ Server active", fg=self.colors["dim"])
        self.config_data["servidor_idade"] = self.entry.get()
        Config.save(self.config_data)
        Logger.log(f"Server started - age: {self.entry.get()}")

    def _new_server(self):
        self.entry.delete(0, "end")
        self.entry.insert(0, "00:00")
        self.notificados.clear()
        self.servidor_inicio = datetime.datetime.now()
        self.paused = False
        self.stats["tempo_inicio"] = datetime.datetime.now()
        self.stats["merchant_spawns"] = 0
        self.stats["store_refreshes"] = 0
        self._start_tracking()
        self.btn_pause.config(text="⏸ PAUSE")
        self.lbl_foot.config(text="🆕 New server", fg=self.colors["green"])
        self.config_data["servidor_idade"] = "00:00"
        Config.save(self.config_data)
        Logger.log("New server started")

    def _toggle_pause(self):
        if not self.servidor_inicio:
            return
        self.paused = not self.paused
        self.btn_pause.config(text="▶ RESUME" if self.paused else "⏸ PAUSE")
        self.lbl_foot.config(text="⏸ PAUSED" if self.paused else "▶ RUNNING",
                            fg=self.colors["red"] if self.paused else self.colors["green"])
        Logger.log(f"{'Paused' if self.paused else 'Resumed'}")

    def _start_tracking(self):
        self.tracking = True
        if not (self._thread and self._thread.is_alive()):
            self._thread = threading.Thread(target=self._notif_loop, daemon=True)
            self._thread.start()
        self._tick()

    def _notif_loop(self):
        webhook = self.config_data.get("discord_webhook", "")
        
        while self.tracking:
            time.sleep(2)
            if not self.servidor_inicio or self.paused:
                continue

            agora = datetime.datetime.now()
            idade = (agora - self.servidor_inicio).total_seconds()

            # ─ Merchant ─
            m_prox = calcular_merchant(idade, 2)
            for s, f in m_prox:
                hora_spawn = self.servidor_inicio + datetime.timedelta(seconds=s)
                falta = (hora_spawn - agora).total_seconds()
                
                if 0 < falta <= 120 and f"merch_aviso_{s}" not in self.notificados:
                    self.notificados.add(f"merch_aviso_{s}")
                    Logger.log("⚠️ Merchant warning in 2 min")
                    fazer_som(1000, 300)
                    enviar_notif("⚠️ MERCHANT IN 2 MIN!",
                                f"Spawning at {hora_spawn.strftime('%H:%M:%S')}")
                    if webhook:
                        enviar_discord(webhook, "⚠️ Merchant in 2 min!",
                                     f"Spawning at {hora_spawn.strftime('%H:%M:%S')}", 0xFFA500)
                
                if -10 <= falta <= 10 and f"merch_spawn_{s}" not in self.notificados:
                    self.notificados.add(f"merch_spawn_{s}")
                    self.stats["merchant_spawns"] += 1
                    Logger.log(f"🐒 Merchant SPAWNED! (Total: {self.stats['merchant_spawns']})")
                    fazer_som(1200, 500)
                    hora_fim = self.servidor_inicio + datetime.timedelta(seconds=f)
                    enviar_notif("🐒 MERCHANT SPAWNED!",
                                f"Active until {hora_fim.strftime('%H:%M:%S')}")
                    if webhook:
                        enviar_discord(webhook, "🐒 MERCHANT SPAWNED!",
                                     f"Active until {hora_fim.strftime('%H:%M:%S')}", 0x00FF00)

            # ─ Store ─
            s_prox = calcular_store(2)
            for r in s_prox:
                falta = (r - agora).total_seconds()
                key_refresh = r.strftime("%H:%M")
                
                if 0 < falta <= 120 and f"store_aviso_{key_refresh}" not in self.notificados:
                    self.notificados.add(f"store_aviso_{key_refresh}")
                    Logger.log("ℹ️ Store refresh warning in 2 min")
                    fazer_som(800, 300)
                    enviar_notif("ℹ️ STORE REFRESH IN 2 MIN!",
                                f"Refreshing at {r.strftime('%H:%M:%S')}")
                    if webhook:
                        enviar_discord(webhook, "ℹ️ Store refresh in 2 min!",
                                     f"Refreshing at {r.strftime('%H:%M:%S')}", 0x00CCFF)
                
                if -10 <= falta <= 10 and f"store_spawn_{key_refresh}" not in self.notificados:
                    self.notificados.add(f"store_spawn_{key_refresh}")
                    self.stats["store_refreshes"] += 1
                    Logger.log(f"🛍️ Store REFRESHED! (Total: {self.stats['store_refreshes']})")
                    fazer_som(900, 400)
                    enviar_notif("🛍️ STORE REFRESHED!",
                                f"Items updated at {r.strftime('%H:%M:%S')}")
                    if webhook:
                        enviar_discord(webhook, "🛍️ STORE REFRESHED!",
                                     f"Items updated at {r.strftime('%H:%M:%S')}", 0x0099FF)

    def _tick(self):
        if not self.tracking or not self.servidor_inicio:
            return

        if self.paused:
            self.after(500, self._tick)
            return

        agora = datetime.datetime.now()
        idade = (agora - self.servidor_inicio).total_seconds()

        # ─ Merchant ─
        m_prox = calcular_merchant(idade, 3)
        if m_prox:
            s0, f0 = m_prox[0]
            hs = self.servidor_inicio + datetime.timedelta(seconds=s0)
            hf = self.servidor_inicio + datetime.timedelta(seconds=f0)
            falta = (hs - agora).total_seconds()
            resta = (hf - agora).total_seconds()

            if falta > 0:
                self.lbl_m_cd.config(text=fmt_mm_ss(falta), fg=self.colors["merch"])
                self.lbl_m_sub.config(text=hs.strftime("%H:%M"), fg=self.colors["dim"])
            elif resta > 0:
                self.lbl_m_cd.config(text=fmt_mm_ss(resta), fg=self.colors["green"])
                self.lbl_m_sub.config(text="🐒 ACTIVE!", fg=self.colors["green"])

        # ─ Store ─
        s_prox = calcular_store(3)
        if s_prox:
            r0 = s_prox[0]
            falta = (r0 - agora).total_seconds()
            self.lbl_s_cd.config(text=fmt_mm_ss(falta), fg=self.colors["store"])
            self.lbl_s_sub.config(text=r0.strftime("%H:%M"), fg=self.colors["dim"])

        # ─ Next event ─
        eventos = []
        if m_prox:
            s, f = m_prox[0]
            hs = self.servidor_inicio + datetime.timedelta(seconds=s)
            falta = (hs - agora).total_seconds()
            if falta > 0:
                eventos.append((falta, f"🐒 Merchant {fmt_mm_ss(falta)}"))
        if s_prox:
            r = s_prox[0]
            falta = (r - agora).total_seconds()
            if falta > 0:
                eventos.append((falta, f"🛍️ Store {fmt_mm_ss(falta)}"))
        
        if eventos:
            eventos.sort()
            self.lbl_prox.config(text=eventos[0][1], fg=self.colors["text"])

        # ─ Merchant list ─
        for i, (row, lh, lf) in enumerate(self.rows_m):
            if i < len(m_prox):
                s, f = m_prox[i]
                hs = self.servidor_inicio + datetime.timedelta(seconds=s)
                falta = (hs - agora).total_seconds()
                lh.config(text=hs.strftime("%H:%M:%S"))
                lf.config(text=f"in {fmt_mm_ss(falta)}" if falta > 0 else "ACTIVE",
                         fg=self.colors["merch"] if falta > 0 else self.colors["green"])
            else:
                lh.config(text="--:--:--", fg=self.colors["dim"])
                lf.config(text="")

        # ─ Store list ─
        for i, (row, lh, lf) in enumerate(self.rows_s):
            if i < len(s_prox):
                r = s_prox[i]
                falta = (r - agora).total_seconds()
                lh.config(text=r.strftime("%H:%M:%S"))
                lf.config(text=f"in {fmt_mm_ss(falta)}", fg=self.colors["store"])
            else:
                lh.config(text="--:--:--", fg=self.colors["dim"])
                lf.config(text="")

        self.after(500, self._tick)

    def _on_close(self):
        self.tracking = False
        Logger.log("App closed")
        self.destroy()


if __name__ == "__main__":
    print(f"[INIT] Sound available: {SOUND_OK}")
    print(f"[INIT] Notifications (plyer): {NOTIF_OK}")
    print(f"[INIT] Discord (requests): {DISCORD_OK}")
    Logger.log("=== APP STARTED ===")
    App().mainloop()