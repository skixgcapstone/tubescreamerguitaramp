from __future__ import annotations

import argparse
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog
from typing import Final

from audio_engine import AudioEngine, AudioSnapshot
from performance import PerformanceMonitor
from simulation import ControlState, SignalMetrics, simulate_signal

APP_TITLE = "Tube Screamer Amplifier"
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 600

BG = "#0b0e10"
SURFACE = "#14191d"
PANEL = "#1c2328"
BORDER = "#294756"
TEXT = "#f4efe5"
MUTED = "#9aadb6"
GRID = "#223946"
ORANGE = "#ff7a2f"
ORANGE_DARK = "#6a3015"
BLUE = "#45b7e8"
FONT = "DejaVu Sans"
DEFAULT_DEVELOPMENT_TRACK = (
    Path.home()
    / "Library"
    / "Application Support"
    / "vantabeat"
    / "library"
    / "Cliffs Of Dover (Instrumental).m4a"
)
HOME_LOGO = Path(__file__).resolve().parent / "assets" / "skixg-logo.png"

EQ_BANDS: Final = ("100 Hz", "400 Hz", "1 kHz", "4 kHz", "10 kHz")
EFFECTS: Final = ("delay", "reverb", "chorus", "echo", "distortion", "phaser", "flanger")
EFFECT_HELP: Final = {
    "delay": "Produces a distinct repeat of each note. Adjust the repeat interval below.",
    "reverb": "Builds a short group of reflections that resembles an acoustic room.",
    "chorus": "Adds a moving, slightly delayed copy for a wider and thicker sound.",
    "echo": "Produces longer repeating notes. Feedback sets how long the repeats continue.",
    "distortion": "Applies nonlinear clipping for a stronger and more aggressive harmonic sound.",
    "phaser": "Sweeps phase cancellation through the signal to create a smooth swirling sound.",
    "flanger": "Mixes a very short moving delay into the signal for a metallic sweeping sound.",
}
EFFECT_PARAMETERS: Final = {
    "delay": ("Delay time (ms)", 80, 700, 280),
    "reverb": ("Decay (%)", 10, 95, 68),
    "chorus": ("Rate (0.1 Hz)", 1, 30, 8),
    "echo": ("Feedback (%)", 0, 80, 48),
    "distortion": ("Drive (%)", 0, 100, 60),
    "phaser": ("Rate (0.1 Hz)", 1, 30, 8),
    "flanger": ("Depth (%)", 0, 100, 60),
}
STATUS_ROWS: Final = (
    "Effects enabled",
    "Audio source",
    "Audio state",
    "Audio format",
    "Input level",
    "Output level",
    "Output RMS",
    "Signal level",
    "Limited samples",
    "Stream errors",
    "Callback time",
    "Effective latency",
)


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


class EffectPad(tk.Canvas):
    def __init__(
        self,
        parent: tk.Widget,
        name: str,
        variable: tk.IntVar,
        changed: Callable[[], None],
        show_info: Callable[[str], None],
    ) -> None:
        super().__init__(parent, bg=SURFACE, highlightthickness=0, bd=0, cursor="hand2")
        self.name = name
        self.variable = variable
        self.changed = changed
        self.show_info = show_info
        self.last_level = max(80, variable.get())
        self.press_y = 0
        self.dragged = False
        self.info_press = False
        self.bind("<Configure>", lambda _event: self.draw())
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", self._release)

    def _press(self, event: tk.Event) -> None:
        self.info_press = event.x >= self.winfo_width() - 58 and event.y >= self.winfo_height() - 50
        if self.info_press:
            self.show_info(self.name)
            return
        self.press_y = event.y
        self.dragged = False

    def _drag(self, event: tk.Event) -> None:
        if self.info_press or (not self.dragged and abs(event.y - self.press_y) < 4):
            return
        self.dragged = True
        usable_height = max(1, self.winfo_height() - 30)
        level = clamp(round((self.winfo_height() - 15 - event.y) * 100 / usable_height), 0, 100)
        self.variable.set(level)
        if level:
            self.last_level = level
        self.changed()

    def _release(self, _event: tk.Event) -> None:
        if self.info_press:
            self.info_press = False
            return
        if not self.dragged:
            current = self.variable.get()
            if current:
                self.last_level = current
                self.variable.set(0)
            else:
                self.variable.set(self.last_level)
            self.changed()

    def draw(self) -> None:
        width = max(150, self.winfo_width())
        height = max(140, self.winfo_height())
        level = self.variable.get()
        self.delete("all")
        self.create_rectangle(2, 2, width - 2, height - 2, fill=PANEL, outline=BORDER, width=2)
        if level:
            fill_top = 2 + (height - 4) * (100 - level) / 100
            self.create_rectangle(3, fill_top, width - 3, height - 3, fill=ORANGE_DARK, outline="")
            self.create_line(3, fill_top, width - 3, fill_top, fill=ORANGE, width=3)
        self.create_text(14, 14, text=self.name.upper(), fill=TEXT, anchor="nw", font=(FONT, 14, "bold"))
        self.create_text(
            14,
            46,
            text=f"{level:02d}%" if level else "OFF",
            fill=ORANGE if level else MUTED,
            anchor="nw",
            font=(FONT, 22, "bold"),
        )
        self.create_text(
            14,
            height - 16,
            text="TAP / DRAG",
            fill=MUTED,
            anchor="sw",
            font=(FONT, 8, "bold"),
        )
        self.create_oval(width - 47, height - 43, width - 17, height - 13, outline=BLUE if level else MUTED, width=2)
        self.create_text(width - 32, height - 28, text="i", fill=BLUE if level else TEXT, font=(FONT, 13, "bold"))


class TubeScreamerApp:
    def __init__(
        self,
        root: tk.Tk,
        fullscreen: bool = False,
        start_live: bool = False,
        development_tools: bool = False,
    ) -> None:
        self.root = root
        root.title(APP_TITLE)
        root.configure(bg=BG)
        root.geometry(f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}")
        root.resizable(False, False)
        root.option_add("*Font", f"{{{FONT}}} 10")
        if fullscreen:
            root.attributes("-fullscreen", True)
            root.bind("<Escape>", lambda _event: root.attributes("-fullscreen", False))

        self.phase = 0.0
        self.current_page = "home"
        self.animation_token: str | None = None
        self.benchmark_token: str | None = None
        self.performance_monitor: PerformanceMonitor | None = None
        self.audio_engine = AudioEngine()
        self.audio_error = ""
        self.status_window: tk.Toplevel | None = None
        self.development_window: tk.Toplevel | None = None
        self.info_window: tk.Toplevel | None = None
        self.status_labels: dict[str, tk.Label] = {}
        self.effect_pads: dict[str, EffectPad] = {}
        self.loop_canvas: tk.Canvas | None = None
        self.control_vars = {
            name: tk.IntVar(value=value)
            for name, value in (
                ("delay", 0),
                ("reverb", 0),
                ("chorus", 0),
                ("echo", 0),
                ("distortion", 0),
                ("phaser", 0),
                ("flanger", 0),
                ("volume", 100),
                ("bias", 0),
            )
        }
        parameter_names = (
            "delay_time_ms",
            "reverb_decay",
            "chorus_rate",
            "echo_feedback",
            "distortion_drive",
            "phaser_rate",
            "flanger_depth",
        )
        self.parameter_vars = {
            name: tk.IntVar(value=spec[3])
            for name, spec in zip(parameter_names, EFFECT_PARAMETERS.values(), strict=True)
        }
        self.eq_vars = {band: tk.IntVar(value=0) for band in EQ_BANDS}
        self.home_logo_image = tk.PhotoImage(file=HOME_LOGO).subsample(4, 4)

        self._build_ui()
        self.audio_engine.update_controls(self._controls())
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.bind("<F12>", lambda _event: self.open_development_tools())
        root.bind("<Command-d>", lambda _event: self.open_development_tools())
        root.bind("1", lambda _event: self.show_page("effects"))
        root.bind("2", lambda _event: self.show_page("eq"))
        root.bind("<Home>", lambda _event: self.show_page("home"))
        self._animate()
        if start_live:
            root.after(150, self._start_live_input)
        if development_tools:
            root.after(150, self.open_development_tools)

    def _build_ui(self) -> None:
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)
        self._build_header()

        self.page_host = tk.Frame(self.root, bg=BG)
        self.page_host.grid(row=1, column=0, sticky="nsew", padx=18)
        self.page_host.rowconfigure(0, weight=1)
        self.page_host.columnconfigure(0, weight=1)
        self.pages = {name: tk.Frame(self.page_host, bg=BG) for name in ("home", "effects", "eq")}
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")
        self._build_home_page(self.pages["home"])
        self._build_effects_page(self.pages["effects"])
        self._build_eq_page(self.pages["eq"])
        self._build_footer()
        self.show_page("home")

    def _build_header(self) -> None:
        header = tk.Frame(self.root, bg=BG, height=54, padx=18)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        self.back_button = self._button(header, "‹ HOME", lambda: self.show_page("home"), 10)
        self.back_button.grid(row=0, column=0, sticky="w", pady=8)

    def _build_footer(self) -> None:
        footer = tk.Frame(self.root, bg=BG, height=50, padx=18)
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_propagate(False)
        footer.columnconfigure(0, weight=1)
        self.footer_state = tk.Label(footer, text="AUDIO: SIMULATION", bg=BG, fg=MUTED, font=(FONT, 9, "bold"))
        self.footer_state.grid(row=0, column=0, sticky="w", pady=10)
        self._button(footer, "SYSTEM STATUS", self.open_status, 9).grid(row=0, column=1, sticky="e", pady=8)

    def _button(self, parent: tk.Widget, text: str, command: Callable[[], None], font_size: int = 11) -> tk.Label:
        button = tk.Label(
            parent,
            text=text,
            bg=PANEL,
            fg=TEXT,
            padx=14,
            pady=9,
            cursor="hand2",
            font=(FONT, font_size, "bold"),
            highlightthickness=0,
        )
        button.bind("<Button-1>", lambda _event: command())
        return button

    def _build_home_page(self, page: tk.Frame) -> None:
        page.rowconfigure(1, weight=1)
        page.columnconfigure(0, weight=1)

        brand = tk.Canvas(page, bg=BG, height=106, highlightthickness=0, bd=0)
        brand.grid(row=0, column=0, sticky="ew")
        brand.create_line(0, 101, SCREEN_WIDTH / 2, 101, fill=ORANGE, width=2)
        brand.create_line(SCREEN_WIDTH / 2, 101, SCREEN_WIDTH, 101, fill=BLUE, width=2)
        brand.create_image(SCREEN_WIDTH / 2 - 18, 51, image=self.home_logo_image)

        navigation = tk.Frame(page, bg=BG)
        navigation.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        navigation.rowconfigure(0, weight=1)
        for column in range(2):
            navigation.columnconfigure(column, weight=1, uniform="home")
        effects = self._home_tile(navigation, "EFFECTS", "Tap, hold, and shape the sound", "effects", 0)
        self.home_effects_canvas = self._home_canvas(effects, "effects")
        eq = self._home_tile(navigation, "EQ + WAVEFORMS", "See the signal and tune five bands", "eq", 1)
        self.home_eq_canvas = self._home_canvas(eq, "eq")

    def _home_tile(self, parent: tk.Frame, title: str, subtitle: str, target: str, column: int) -> tk.Frame:
        tile = tk.Frame(parent, bg=PANEL, highlightthickness=2, highlightbackground=BORDER, cursor="hand2")
        tile.grid(row=0, column=column, sticky="nsew", padx=(0, 8) if column == 0 else (8, 0))
        tile.rowconfigure(1, weight=1)
        tile.columnconfigure(0, weight=1)
        heading = tk.Frame(tile, bg=PANEL, cursor="hand2")
        heading.grid(row=0, column=0, sticky="ew", padx=16, pady=14)
        heading.columnconfigure(0, weight=1)
        labels = (
            tk.Label(heading, text=title, bg=PANEL, fg=TEXT, cursor="hand2", font=(FONT, 17, "bold")),
            tk.Label(heading, text="OPEN  ›", bg=PANEL, fg=BLUE, cursor="hand2", font=(FONT, 10, "bold")),
            tk.Label(heading, text=subtitle, bg=PANEL, fg=MUTED, cursor="hand2", font=(FONT, 9)),
        )
        labels[0].grid(row=0, column=0, sticky="w")
        labels[1].grid(row=0, column=1, sticky="e")
        labels[2].grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        for widget in (tile, heading, *labels):
            widget.bind("<Button-1>", lambda _event, page_name=target: self.show_page(page_name))
        return tile

    def _home_canvas(self, parent: tk.Frame, target: str) -> tk.Canvas:
        canvas = tk.Canvas(parent, bg=SURFACE, highlightthickness=0, height=320, cursor="hand2")
        canvas.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        canvas.bind("<Button-1>", lambda _event: self.show_page(target))
        return canvas

    def _build_effects_page(self, page: tk.Frame) -> None:
        for row in range(2):
            page.rowconfigure(row, weight=1, uniform="effects")
        for column in range(4):
            page.columnconfigure(column, weight=1, uniform="effects")
        for index, name in enumerate(EFFECTS):
            pad = EffectPad(page, name, self.control_vars[name], self._controls_changed, self.open_effect_info)
            pad.grid(
                row=index // 4,
                column=index % 4,
                sticky="nsew",
                padx=5,
                pady=5,
            )
            self.effect_pads[name] = pad
        self._build_looper(page)

    def _build_looper(self, page: tk.Frame) -> None:
        self.loop_canvas = tk.Canvas(page, bg=SURFACE, highlightthickness=0, bd=0, cursor="hand2")
        self.loop_canvas.grid(row=1, column=3, sticky="nsew", padx=5, pady=5)
        self.loop_canvas.bind("<Configure>", lambda _event: self._draw_looper())
        self.loop_canvas.bind("<Button-1>", self._looper_press)

    def _looper_press(self, event: tk.Event) -> None:
        if event.x < event.widget.winfo_width() / 2:
            self._toggle_loop()
        else:
            self._close_loop()

    def _draw_looper(self) -> None:
        if self.loop_canvas is None:
            return
        canvas = self.loop_canvas
        width = max(180, canvas.winfo_width())
        height = max(140, canvas.winfo_height())
        middle = width / 2
        state = self.audio_engine.looper.state
        canvas.delete("all")
        left_fill = ORANGE_DARK if state != "off" else PANEL
        right_fill = ORANGE_DARK if state == "recording" else PANEL
        canvas.create_rectangle(2, 2, middle, height - 2, fill=left_fill, outline=ORANGE if state != "off" else BORDER, width=2)
        canvas.create_rectangle(middle, 2, width - 2, height - 2, fill=right_fill, outline=ORANGE if state == "recording" else BORDER, width=2)
        canvas.create_text(middle / 2, 22, text="LOOPER", fill=TEXT, font=(FONT, 11, "bold"))
        canvas.create_text(middle + middle / 2, 22, text=state.upper(), fill=ORANGE if state != "off" else MUTED, font=(FONT, 10, "bold"))
        canvas.create_text(middle / 2, height / 2, text="STOP" if state != "off" else "START", fill=TEXT, font=(FONT, 16, "bold"))
        canvas.create_text(middle + middle / 2, height / 2, text="CLOSE\nLOOP", fill=TEXT if state == "recording" else MUTED, justify="center", font=(FONT, 14, "bold"))
        canvas.create_text(middle / 2, height - 18, text="LEFT SIDE", fill=MUTED, font=(FONT, 7, "bold"))
        canvas.create_text(middle + middle / 2, height - 18, text="RIGHT SIDE", fill=MUTED, font=(FONT, 7, "bold"))

    def _build_eq_page(self, page: tk.Frame) -> None:
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=1)
        page.rowconfigure(1, weight=1)
        page.rowconfigure(2, weight=2)
        self.input_canvas = self._waveform_panel(page, "INPUT", 0, BLUE)
        self.output_canvas = self._waveform_panel(page, "OUTPUT", 1, ORANGE)
        eq_panel = tk.Frame(page, bg=PANEL, highlightthickness=1, highlightbackground=BORDER, padx=10, pady=6)
        eq_panel.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        for column, band in enumerate(EQ_BANDS):
            eq_panel.columnconfigure(column, weight=1, uniform="eq")
            group = tk.Frame(eq_panel, bg=PANEL)
            group.grid(row=0, column=column, sticky="nsew", padx=5)
            tk.Scale(
                group,
                from_=12,
                to=-12,
                orient="vertical",
                variable=self.eq_vars[band],
                command=lambda _value: self._controls_changed(),
                bg=PANEL,
                fg=TEXT,
                troughcolor=SURFACE,
                activebackground=BLUE,
                highlightthickness=0,
                relief="flat",
                bd=0,
                sliderlength=28,
                width=19,
                length=175,
                font=(FONT, 9, "bold"),
            ).grid(row=0, column=0)
            tk.Label(group, text=band, bg=PANEL, fg=MUTED, font=(FONT, 9, "bold")).grid(row=1, column=0)

    def _waveform_panel(self, parent: tk.Frame, label: str, row: int, color: str) -> tk.Canvas:
        panel = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        panel.grid(row=row, column=0, sticky="nsew", pady=(0, 5) if row == 0 else (5, 0))
        panel.columnconfigure(1, weight=1)
        panel.rowconfigure(0, weight=1)
        tk.Label(panel, text=label, bg=PANEL, fg=color, width=9, font=(FONT, 10, "bold")).grid(
            row=0, column=0, sticky="nsw", padx=8
        )
        canvas = tk.Canvas(panel, bg=SURFACE, highlightthickness=0, height=90)
        canvas.grid(row=0, column=1, sticky="nsew")
        return canvas

    def show_page(self, name: str) -> None:
        self.pages[name].tkraise()
        self.current_page = name
        if name == "home":
            self.back_button.grid_remove()
        else:
            self.back_button.grid()

    def open_effect_info(self, name: str) -> None:
        if self.info_window is not None and self.info_window.winfo_exists():
            self.info_window.destroy()
        window = tk.Toplevel(self.root)
        self.info_window = window
        window.title(f"{name.title()} settings")
        window.geometry("430x250")
        window.resizable(False, False)
        window.configure(bg=BG)
        window.transient(self.root)
        window.columnconfigure(0, weight=1)
        tk.Label(window, text=name.upper(), bg=BG, fg=TEXT, font=(FONT, 18, "bold")).grid(
            row=0, column=0, sticky="w", padx=22, pady=(20, 5)
        )
        tk.Label(
            window,
            text=EFFECT_HELP[name],
            bg=BG,
            fg=MUTED,
            wraplength=380,
            justify="left",
            font=(FONT, 10),
        ).grid(row=1, column=0, sticky="w", padx=22)
        parameter_name = {
            "delay": "delay_time_ms",
            "reverb": "reverb_decay",
            "chorus": "chorus_rate",
            "echo": "echo_feedback",
            "distortion": "distortion_drive",
            "phaser": "phaser_rate",
            "flanger": "flanger_depth",
        }[name]
        label, minimum, maximum, _default = EFFECT_PARAMETERS[name]
        tk.Scale(
            window,
            from_=minimum,
            to=maximum,
            orient="horizontal",
            label=label,
            variable=self.parameter_vars[parameter_name],
            command=lambda _value: self._controls_changed(),
            bg=BG,
            fg=TEXT,
            troughcolor=SURFACE,
            activebackground=ORANGE,
            highlightthickness=0,
            length=370,
            sliderlength=30,
            font=(FONT, 10, "bold"),
        ).grid(row=2, column=0, padx=22, pady=10)
        self._button(window, "CLOSE", window.destroy, 9).grid(row=3, column=0, sticky="e", padx=22)

    def open_development_tools(self) -> None:
        if self.development_window is not None and self.development_window.winfo_exists():
            self.development_window.lift()
            return
        window = tk.Toplevel(self.root)
        self.development_window = window
        window.title("Development Audio Tools")
        window.geometry("500x250")
        window.resizable(False, False)
        window.configure(bg=BG)
        window.columnconfigure(0, weight=1)
        controls = tk.Frame(window, bg=BG)
        controls.grid(row=0, column=0, sticky="ew", padx=16, pady=(18, 16))
        for column in range(2):
            controls.columnconfigure(column, weight=1)
        actions = (
            ("LOAD TRACK", self._load_audio),
            ("PLAY", self._play_audio),
            ("PAUSE", self._pause_audio),
            ("STOP", self._stop_audio),
            ("START / STOP LIVE INPUT", self._toggle_live_input),
        )
        for index, (label, action) in enumerate(actions):
            self._button(controls, label, action, 10).grid(
                row=index // 2,
                column=index % 2,
                columnspan=2 if index == 4 else 1,
                sticky="ew",
                padx=4,
                pady=4,
            )
        self.dev_source_label = tk.Label(window, text="Source: Visual simulation", bg=BG, fg=TEXT, anchor="w", font=(FONT, 10, "bold"))
        self.dev_source_label.grid(row=1, column=0, sticky="ew", padx=20)
        self.dev_state_label = tk.Label(window, text="State: Simulation", bg=BG, fg=MUTED, anchor="w", font=(FONT, 10))
        self.dev_state_label.grid(row=2, column=0, sticky="ew", padx=20, pady=(4, 0))
        self.dev_error_label = tk.Label(window, text="", bg=BG, fg=ORANGE, anchor="w", wraplength=450, justify="left", font=(FONT, 9))
        self.dev_error_label.grid(row=3, column=0, sticky="ew", padx=20, pady=(4, 0))

    def open_status(self) -> None:
        if self.status_window is not None and self.status_window.winfo_exists():
            self.status_window.lift()
            return
        window = tk.Toplevel(self.root)
        self.status_window = window
        window.title("System Status")
        window.geometry("600x470")
        window.resizable(False, False)
        window.configure(bg=BG)
        window.columnconfigure(1, weight=1)
        tk.Label(window, text="SYSTEM STATUS", bg=BG, fg=TEXT, font=(FONT, 16, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(18, 10)
        )
        self.status_labels = {}
        for row, name in enumerate(STATUS_ROWS, 1):
            tk.Label(window, text=name, bg=BG, fg=MUTED, font=(FONT, 10, "bold"), anchor="w").grid(
                row=row, column=0, sticky="w", padx=(20, 16), pady=4
            )
            value = tk.Label(window, text="—", bg=BG, fg=TEXT, font=(FONT, 10), anchor="w")
            value.grid(row=row, column=1, sticky="w", padx=(0, 20), pady=4)
            self.status_labels[name] = value

    def _load_audio(self) -> None:
        path = filedialog.askopenfilename(
            title="Load Test Audio",
            filetypes=(("Supported audio", "*.wav *.mp3 *.m4a"), ("WAV", "*.wav"), ("MP3", "*.mp3"), ("M4A", "*.m4a")),
        )
        if path:
            self._audio_action(lambda: self.audio_engine.load_file(path))

    def load_development_track(self, path: Path) -> None:
        self._audio_action(lambda: self.audio_engine.load_file(path))

    def _play_audio(self) -> None:
        self._audio_action(self.audio_engine.play)

    def _pause_audio(self) -> None:
        self._audio_action(self.audio_engine.pause)

    def _stop_audio(self) -> None:
        self._audio_action(self.audio_engine.stop)

    def _start_live_input(self) -> None:
        self._audio_action(self.audio_engine.start_live_input)

    def _toggle_live_input(self) -> None:
        action = self.audio_engine.stop_live_input if self.audio_engine.live_mode else self.audio_engine.start_live_input
        self._audio_action(action)

    def _toggle_loop(self) -> None:
        self.audio_engine.toggle_loop()
        self._update_looper()

    def _close_loop(self) -> None:
        self.audio_engine.close_loop()
        self._update_looper()

    def _update_looper(self) -> None:
        self._draw_looper()

    def _audio_action(self, action: Callable[[], object]) -> None:
        try:
            action()
            self.audio_error = ""
        except (OSError, RuntimeError, ValueError) as error:
            self.audio_error = str(error)

    def _controls(self) -> ControlState:
        return ControlState(
            delay=self.control_vars["delay"].get(),
            reverb=self.control_vars["reverb"].get(),
            chorus=self.control_vars["chorus"].get(),
            echo=self.control_vars["echo"].get(),
            volume=self.control_vars["volume"].get(),
            bias=self.control_vars["bias"].get(),
            eq=tuple(self.eq_vars[band].get() for band in EQ_BANDS),
            distortion=self.control_vars["distortion"].get(),
            phaser=self.control_vars["phaser"].get(),
            flanger=self.control_vars["flanger"].get(),
            delay_time_ms=self.parameter_vars["delay_time_ms"].get(),
            reverb_decay=self.parameter_vars["reverb_decay"].get(),
            chorus_rate=self.parameter_vars["chorus_rate"].get(),
            echo_feedback=self.parameter_vars["echo_feedback"].get(),
            distortion_drive=self.parameter_vars["distortion_drive"].get(),
            phaser_rate=self.parameter_vars["phaser_rate"].get(),
            flanger_depth=self.parameter_vars["flanger_depth"].get(),
        )

    def _controls_changed(self) -> None:
        self.audio_engine.update_controls(self._controls())
        for pad in self.effect_pads.values():
            pad.draw()

    def _effects_text(self, controls: ControlState) -> str:
        names = [name.title() for name in EFFECTS if getattr(controls, name) > 0]
        if self.audio_engine.looper.state != "off":
            names.append(f"Looper ({self.audio_engine.looper.state})")
        if any(controls.eq):
            names.append("EQ")
        return ", ".join(names) if names else "None"

    def _draw_waveform(self, canvas: tk.Canvas, signal: tuple[float, ...], color: str) -> None:
        width = max(300, canvas.winfo_width())
        height = max(80, canvas.winfo_height())
        canvas.delete("all")
        center = height / 2
        for column in range(1, 8):
            x = width * column / 8
            canvas.create_line(x, 7, x, height - 7, fill=GRID)
        canvas.create_line(0, center, width, center, fill=BORDER)
        if len(signal) < 2:
            return
        points: list[float] = []
        for index, sample in enumerate(signal):
            points.extend((index * width / (len(signal) - 1), center - sample * height * 0.34))
        canvas.create_line(*points, fill=TEXT, width=4, smooth=True)
        canvas.create_line(*points, fill=color, width=2, smooth=True)

    def _draw_home_previews(
        self,
        controls: ControlState,
        input_signal: tuple[float, ...],
        output_signal: tuple[float, ...],
    ) -> None:
        canvas = self.home_effects_canvas
        width, height = max(300, canvas.winfo_width()), max(220, canvas.winfo_height())
        canvas.delete("all")
        gap = 7
        pad_width, pad_height = (width - gap * 5) / 4, (height - gap * 3) / 2
        preview_names = (*EFFECTS, "looper")
        for index, name in enumerate(preview_names):
            column, row = index % 4, index // 4
            left, top = gap + column * (pad_width + gap), gap + row * (pad_height + gap)
            right, bottom = left + pad_width, top + pad_height
            level = getattr(controls, name) if name != "looper" else int(self.audio_engine.looper.state != "off") * 100
            canvas.create_rectangle(left, top, right, bottom, fill=ORANGE_DARK if level else PANEL, outline=ORANGE if level else BORDER, width=2)
            canvas.create_text(left + 7, top + 8, text=name.upper(), fill=TEXT, anchor="nw", font=(FONT, 8, "bold"))
            value = self.audio_engine.looper.state.upper() if name == "looper" else (f"{level}%" if level else "OFF")
            canvas.create_text(left + 7, bottom - 8, text=value, fill=ORANGE if level else MUTED, anchor="sw", font=(FONT, 10, "bold"))

        canvas = self.home_eq_canvas
        width, height = max(300, canvas.winfo_width()), max(220, canvas.winfo_height())
        canvas.delete("all")
        self._draw_mini_waveform(canvas, input_signal, BLUE, 15, height * 0.34, width - 30)
        self._draw_mini_waveform(canvas, output_signal, ORANGE, height * 0.42, height * 0.34, width - 30)
        baseline = height - 20
        for index, band in enumerate(EQ_BANDS):
            x = 40 + index * (width - 80) / 4
            value = self.eq_vars[band].get()
            canvas.create_line(x, baseline - 72, x, baseline, fill=BORDER, width=8)
            y = baseline - 36 - value * 3
            canvas.create_line(x - 10, y, x + 10, y, fill=BLUE, width=4)
            canvas.create_text(x, baseline + 2, text=band, fill=MUTED, anchor="n", font=(FONT, 8, "bold"))

    @staticmethod
    def _draw_mini_waveform(
        canvas: tk.Canvas,
        signal: tuple[float, ...],
        color: str,
        top: float,
        height: float,
        width: float,
    ) -> None:
        if len(signal) < 2:
            return
        center = top + height / 2
        points: list[float] = []
        for index, sample in enumerate(signal):
            points.extend((15 + index * width / (len(signal) - 1), center - sample * height * 0.36))
        canvas.create_line(*points, fill=color, width=2, smooth=True)

    def _update_status(self, controls: ControlState, metrics: SignalMetrics, audio: AudioSnapshot) -> None:
        if self.status_window is None or not self.status_window.winfo_exists():
            return
        real_audio = bool(audio.input_waveform or audio.output_waveform)
        values = {
            "Effects enabled": self._effects_text(controls),
            "Audio source": audio.source_name,
            "Audio state": audio.state.title(),
            "Audio format": f"{self.audio_engine.sample_rate / 1_000:g} kHz / {self.audio_engine.block_size} frames / float32",
            "Input level": f"{audio.input_peak:.3f} FS peak" if real_audio else f"{metrics.input_peak_volts:.2f} V peak (simulated)",
            "Output level": f"{audio.output_peak:.3f} FS peak" if real_audio else f"{metrics.output_peak_volts:.2f} V peak (simulated)",
            "Output RMS": f"{audio.output_rms:.3f} FS RMS" if real_audio else f"{metrics.output_rms_volts:.2f} V RMS (simulated)",
            "Signal level": f"{audio.output_dbfs:.1f} dBFS" if real_audio else f"{metrics.signal_dbfs:.1f} dBFS (simulated)",
            "Limited samples": str(audio.limited_samples) if real_audio else "0 (simulated)",
            "Stream errors": f"{audio.underruns} under / {audio.overruns} over / {audio.deadline_misses} deadline",
            "Callback time": f"{audio.callback_ms:.2f} ms" if real_audio else "Not active",
            "Effective latency": f"{audio.latency_ms:.2f} ms" if real_audio else f"{metrics.latency_ms} ms (estimated)",
        }
        for name, label in self.status_labels.items():
            label.configure(text=values[name])

    def _update_development_tools(self, audio: AudioSnapshot) -> None:
        self.footer_state.configure(text=f"AUDIO: {audio.state.upper()}")
        if self.development_window is None or not self.development_window.winfo_exists():
            return
        self.dev_source_label.configure(text=f"Source: {audio.source_name}")
        self.dev_state_label.configure(text=f"State: {audio.state.title()}")
        self.dev_error_label.configure(text=self.audio_error or audio.error)

    def _animate(self) -> None:
        controls = self._controls()
        self.audio_engine.update_controls(controls)
        self.audio_engine.service()
        audio = self.audio_engine.get_status()
        status_open = self.status_window is not None and self.status_window.winfo_exists()
        if self.current_page in ("home", "eq") or status_open:
            frame = simulate_signal(controls, self.phase)
            input_signal = audio.input_waveform or frame.raw
            output_signal = audio.output_waveform or frame.processed
            if self.current_page == "eq":
                self._draw_waveform(self.input_canvas, input_signal, BLUE)
                self._draw_waveform(self.output_canvas, output_signal, ORANGE)
            elif self.current_page == "home":
                self._draw_home_previews(controls, input_signal, output_signal)
            self._update_status(controls, frame.metrics, audio)
        self._update_development_tools(audio)
        if self.current_page == "effects":
            self._update_looper()
        self.phase = (self.phase + 0.12) % 6.283185307179586
        self.animation_token = self.root.after(70, self._animate)

    def _set_benchmark_controls(self, maximum: bool) -> None:
        for name in EFFECTS:
            self.control_vars[name].set(100 if maximum else 0)
        for band in EQ_BANDS:
            self.eq_vars[band].set(12 if maximum else 0)
        self._controls_changed()

    def start_benchmark(self, path: str | None, seconds: int, report: str, scenario: str) -> None:
        if seconds <= 0:
            raise ValueError("benchmark duration must be greater than zero")
        if scenario in ("clean", "worst") and path is None:
            raise ValueError(f"the {scenario} scenario requires --benchmark-file")
        self._set_benchmark_controls(scenario in ("worst", "live"))
        if scenario in ("clean", "worst"):
            self.audio_engine.load_file(path, loop=True)
            self.audio_engine.play()
        elif scenario == "live":
            self.audio_engine.start_live_input()
        self.performance_monitor = PerformanceMonitor(
            self.audio_engine,
            report,
            configuration={
                "scenario": scenario,
                "source": path,
                "seconds": seconds,
                "sample_rate": self.audio_engine.sample_rate,
                "block_size": self.audio_engine.block_size,
            },
        )
        self.performance_monitor.start()
        self.benchmark_token = self.root.after(seconds * 1_000, self._finish_benchmark)

    def _finish_benchmark(self) -> None:
        self.benchmark_token = None
        if self.performance_monitor is not None:
            summary = self.performance_monitor.stop()
            self.performance_monitor = None
            print(f"Benchmark complete. Passed: {summary['passed']}")
        self.close()

    def close(self) -> None:
        if self.animation_token is not None:
            self.root.after_cancel(self.animation_token)
        if self.benchmark_token is not None:
            self.root.after_cancel(self.benchmark_token)
        if self.performance_monitor is not None:
            self.performance_monitor.stop()
        self.audio_engine.shutdown()
        self.root.destroy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tube Screamer touchscreen control")
    parser.add_argument("--fullscreen", action="store_true", help="start in touchscreen fullscreen mode")
    parser.add_argument("--live-input", action="store_true", help="open the live stream after startup")
    parser.add_argument("--development-tools", action="store_true", help="open desktop test controls separately")
    parser.add_argument("--benchmark-file", help="loop this audio file during a benchmark")
    parser.add_argument("--benchmark-seconds", type=int, default=0, help="benchmark duration in seconds")
    parser.add_argument("--benchmark-report", default="reports/pi5-v2.csv", help="benchmark CSV output path")
    parser.add_argument(
        "--benchmark-scenario",
        choices=("idle", "clean", "worst", "live"),
        default="worst",
        help="resource benchmark scenario",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = tk.Tk()
    open_player = args.development_tools or not (
        args.fullscreen or args.live_input or args.benchmark_seconds
    )
    app = TubeScreamerApp(root, args.fullscreen, args.live_input, open_player)
    if open_player and DEFAULT_DEVELOPMENT_TRACK.is_file():
        app.load_development_track(DEFAULT_DEVELOPMENT_TRACK)
    if args.benchmark_seconds:
        app.start_benchmark(args.benchmark_file, args.benchmark_seconds, args.benchmark_report, args.benchmark_scenario)
    root.mainloop()
