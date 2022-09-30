import math
import re
from pathlib import Path
from tkinter import *
from tkinter import ttk, font
from typing import Any, Callable

import sv_ttk
from PIL import Image, ImageTk

# Some init
win = Tk()
win.option_add("*tearOff", FALSE)
sv_ttk.set_theme("light")
default_font_family = "Microsoft YaHei UI Light"
default_font = font.nametofont("TkDefaultFont")
default_font.config(family=default_font_family, size=12)
f = default_font.actual("family")

win.option_add("*Font", default_font)

DEFAULT_FONT = font.Font(family=f, size=12)
TITLE_FONT = font.Font(family=f, size=24, weight="bold")
SUBTITLE_FONT = font.Font(family=f, size=18)


class VariableDescriptor:
    def __set_name__(self, owner, name):
        self.name = name
        self.storage_name = f"variable"

    def __init__(self, construct) -> None:
        self.construct = construct

    def __get__(self, instance, owner):
        if instance:
            return instance.__dict__[self.storage_name].get()
        else:
            return self

    def __set__(self, instance, value):
        instance.__dict__.setdefault(self.storage_name, self.construct(instance)).set(
            value
        )


class DefaultEntry(ttk.Entry):
    value = VariableDescriptor(StringVar)

    def __init__(
        self,
        master,
        prompt: str = "",
        checker: Callable[[Any], bool] = None,
        key_re: str | re.Pattern = ".*",
        total_re: str | re.Pattern = ".*",
        checker_args: tuple[str] = ("%P", "%V", "%s", "%S", "%W"),
        *args,
        **kwargs,
    ):
        super().__init__(master, *args, **kwargs)
        # %P new content
        # %s prior content
        # %d difference between insert and delete
        # %i index of insert or delete
        # %S what is deleted/inserted
        # %v current setting of validate
        # %W name of the widget
        # %V method
        # By default, new content is passed to checker

        self.prompt = prompt
        self.value = self.prompt
        self._prompt_state = True
        self.checker = checker
        checker = (
            self.register(self._default_checker),
            *checker_args,
        )

        self.config(
            textvariable=self.variable,
            validate="all",  # all make it call on other triggers
            validatecommand=checker,
        )
        self._set_prompt_style()
        self.bind("<FocusIn>", lambda e: self.icursor(0))

        if isinstance(key_re, str):
            self.key_re: re.Pattern = re.compile("^" + key_re + "$")
        if isinstance(total_re, str):
            self.total_re: re.Pattern = re.compile("^" + total_re + "$")

    def _default_checker(self, new_val, method, previous, diff, widget_name):
        if method != "forced":
            if (
                self.value == self.prompt and self._prompt_state
            ):  # After prompt, type again.
                self._prompt_state = False
                self.value = diff
                self.selection_clear()
                self.icursor(len(diff))
                self._set_default_style()
                return False
            elif (
                new_val == ""
                and len(new_val) < len(previous)
                and not self._prompt_state
            ):  # Entering, then forgot and clear it
                self.value = self.prompt
                self.icursor(0)
                self.selection_clear()
                self._prompt_state = True
                self._set_prompt_style()
                return False
        else:
            if self.value == self.prompt:
                return False
            if self.checker:
                return self.checker(new_val, method, previous, diff)
            
            match method:
                case "key":
                    if self.key_re:
                        return bool(self.key_re.match(new_val))
                case "focusout" | "forced" | "_":
                    if self.total_re:
                        return bool(self.total_re.match(new_val))
        return True

    def _set_prompt_style(self):
        _prompt_style = ttk.Style()
        _prompt_style.configure("PromptStyle.TEntry", foreground="grey")
        self.config(style="PromptStyle.TEntry")

    def _set_default_style(self):
        _default_style = ttk.Style()
        _default_style.configure("DefaultStyle.TEntry")
        self.config(style="DefaultStyle.TEntry")


def load_icon_from_path(icon_path, width=..., height=...):
    if not Path(icon_path).is_absolute():
        icon_path = Path(__file__).parent / "assets" / icon_path

    img = Image.open(icon_path)
    img_width, img_height = img.size
    resized_img = img
    if width is not ... or height is not ...:
        sz = min(
            width if width is not ... else 99999,
            height if height is not ... else 9999,
        )
        ratio = min(sz / img_width, sz / img_height)
        img_width, img_height = (
            int(ratio * img_width),
            int(ratio * img_height),
        )
        resized_img = img.resize((img_width, img_height))
    res = ImageTk.PhotoImage(resized_img)
    return img_width, img_height, img, res


class Icon(Canvas):
    def __init__(
        self, master, *args, icon_path="", padding=8, sz=None, resizable=True, **kwargs
    ):
        super().__init__(
            master, *args, **kwargs, bd=0, highlightthickness=0, relief="ridge"
        )  # Necessary for canvas to start at 0,0 without border
        (
            self.icon_width,
            self.icon_height,
            self.original_image,
            self.tk_icon,
        ) = load_icon_from_path(
            icon_path,
            width=sz if sz else kwargs.get("width", ...),
            height=sz if sz else kwargs.get("height", ...),
        )
        self.size = max(self.icon_width, self.icon_height)
        self.padding = padding
        self.icon_tag = self.create_image(
            max(self.icon_width, self.icon_height) / 2 + padding,
            max(self.icon_width, self.icon_height) / 2 + padding,
            image=self.tk_icon,
        )
        self.bind("<Configure>", self._resizable_redraw if resizable else self._redraw)

    def _redraw(self, event):
        self.moveto(
            self.icon_tag,
            event.width / 2 - self.icon_width / 2,
            event.height / 2 - self.icon_height / 2,
        )

    def _resizable_redraw(self, event):
        self.delete(self.icon_tag)
        self.size = min(event.width, event.height)
        ratio = min(
            self.size / self.original_image.size[0],
            self.size / self.original_image.size[1],
        )
        self.icon_height = int(ratio * self.original_image.size[1]) - self.padding * 2
        self.icon_height = max(self.icon_height, 1)
        self.icon_width = int(ratio * self.original_image.size[0]) - self.padding * 2
        self.icon_width = max(self.icon_width, 1)
        self.config(width=self.size, height=self.size)
        self.tk_icon = ImageTk.PhotoImage(
            self.original_image.resize(
                (
                    self.icon_width,
                    self.icon_height,
                )
            )
        )
        self.create_image(
            event.width / 2,
            event.height / 2,
            image=self.tk_icon,
        )


def round_rectangle(
    x1,
    y1,
    x2,
    y2,
    radius=25,
):

    points = [
        x1 + radius,
        y1,
        x1 + radius,
        y1,
        x2 - radius,
        y1,
        x2 - radius,
        y1,
        x2,
        y1,
        x2,
        y1 + radius,
        x2,
        y1 + radius,
        x2,
        y2 - radius,
        x2,
        y2 - radius,
        x2,
        y2,
        x2 - radius,
        y2,
        x2 - radius,
        y2,
        x1 + radius,
        y2,
        x1 + radius,
        y2,
        x1,
        y2,
        x1,
        y2 - radius,
        x1,
        y2 - radius,
        x1,
        y1 + radius,
        x1,
        y1 + radius,
        x1,
        y1,
    ]

    return points


class PasswordEntry(DefaultEntry):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.display_btn = Icon(
            self,
            icon_path="eye.png",
            takefocus=False,
            padding=2,
            resizable=False,
            sz=16,
            width=24,
            height=24,
            background="#ffffff",
        )

        self.display_btn.bind("<ButtonPress>", self._show)
        self.display_btn.bind("<Button1-ButtonRelease>", self._hide)

        self.variable.trace_add("write", self._auto_hide())
        self.bind("<Configure>", self._place)

    def _auto_hide(self):
        def _impl(var, index, mode):
            if self.value != self.prompt and self.value != "":
                self._place()
                self["show"] = "●"
            else:
                self.display_btn.place_forget()
                self["show"] = ""

        return _impl

    def _place(self, event=None):
        if not event:
            self.display_btn.place(
                in_=self,
                relx=1.0,
                x=-(self.winfo_height() - self.display_btn.icon_height) // 2
                - self.display_btn.icon_width // 2,
                rely=0.5,
                y=-1,
                anchor="center",
            )
        else:
            y_distance = (event.height - self.display_btn.icon_height) // 2
            self.display_btn.place(
                in_=self,
                x=-y_distance - self.display_btn.icon_width // 2,
                rely=0.5,
                y=-1,
                anchor="center",
            )

    def _show(self, *args, **kwargs):
        if not getattr(self, "active_tag", None):
            self.active_tag = self.display_btn.create_polygon(
                round_rectangle(
                    0,
                    0,
                    self.display_btn.winfo_width(),
                    self.display_btn.winfo_height(),
                    radius=16,
                ),
                fill="#fafafa",
                smooth=True,
                outline="#ebebeb",
            )
            self.display_btn.tag_raise(self.display_btn.icon_tag, self.active_tag)
        self["show"] = ""

    def _hide(self, *args, **kwargs):
        self.display_btn.delete(self.active_tag)
        self.active_tag = None
        if self.value != self.prompt:
            self["show"] = "●"


class CircularProgressBar(Canvas):
    INTERVAL = 50

    @property
    def running(self):
        return self._running

    @running.setter
    def running(self, value):
        if (not getattr(self, "_running", False)) and value:
            self.start()
        elif (getattr(self, "_running", False)) and not value:
            self.stop()
        self._running = value

    def __init__(
        self,
        master,
        *args,
        size=10,
        width=...,
        speed=0.075,
        padding=5,
        **kwargs,
    ):
        super().__init__(
            master,
            *args,
            **kwargs,
            width=size + padding * 2,
            height=size + padding * 2,
            bd=0,
            highlightthickness=0,
            relief="ridge",  # Necessary for canvas to start at 0,0 without border
        )
        self.arc = self.create_arc(
            padding,
            padding,
            size - padding,
            size - padding,
            width=width if width is not ... else size / 5,
            start=0,
            extent=0,
            style="arc",
            fill="#0067c0",
            outline="#0067c0",
        )
        self.x = 0.0
        self.delta = speed
        self.padding = padding

        self.bind("<Configure>", self._resize)

    def _resize(self, event):
        padding = self.padding
        size = min(event.width, event.height)
        self.coords(self.arc, padding, padding, size - padding, size - padding)

    def step(self):
        if self.running:
            self.x += self.delta
            self.cur_extent = min((math.sin(self.x) + 1) * 180, 350)
            self.cur_start = (self.x * 360) % 360
            self.itemconfigure(self.arc, start=self.cur_start, extent=self.cur_extent)
        self.after_id = self.after(CircularProgressBar.INTERVAL, self.step)

    def start(self):
        self.after(CircularProgressBar.INTERVAL, self.step)

    def stop(self):
        try:
            self.after_cancel(self.after_id)
        except AttributeError:
            pass
        self.itemconfigure(self.arc, start=0, extent=0)
        self.x = 0


class Notification:
    """
    create a notification
    """

    def __init__(
        self,
        title="Notification",
        subtitle="widget info",
        width=348,
        icon=None,
        callback=None,
        icon_sz=64,
        lapse=5000,
    ):
        self.wraplength = width - 16
        self.title = title
        self.subtitle = subtitle
        if isinstance(icon, str) or isinstance(icon, Path):
            icon = load_icon_from_path(icon, width=icon_sz, height=icon_sz)[-1]
        self.icon = icon
        self.callback = callback
        self.show_notification()

        self.tw.bind("<ButtonPress>", self.remove)
        self.tw.after(lapse, self.remove)

    def remove(self, event=None):
        self.hide_notification()
        if self.callback:
            self.callback()

    def show_notification(self):
        # creates a toplevel window
        self.tw = Toplevel(win, border=1, relief="ridge")

        # on top and remove border
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("348x110-30-30")
        self.tw.attributes("-topmost", True)
        self.tw.lift()

        icon_args = {"image": self.icon, "compound": "left"} if self.icon else {}
        title = ttk.Label(
            self.tw,
            text=self.title,
            font=(default_font_family, 14, "bold"),
            justify="left",
            wraplength=self.wraplength,
            anchor="w",
        )
        title.grid(row=0, column=0, padx=8, pady=(8, 4), sticky="nwe")
        subtitle = ttk.Label(
            self.tw,
            text=self.subtitle,
            font=(default_font_family, 12, "normal"),
            justify="left",
            wraplength=self.wraplength,
            anchor="w",
            **icon_args,
        )
        subtitle.grid(row=1, column=0, padx=8, pady=(4, 8), sticky="nwe")

        self.tw.rowconfigure(0, weight=1)
        self.tw.rowconfigure(1, weight=1)
        self.tw.columnconfigure(0, weight=1)

    def hide_notification(self):
        tw = self.tw
        self.tw = None
        if tw:
            tw.destroy()
