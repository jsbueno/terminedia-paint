import asyncio
import time
from ast import literal_eval
from math import ceil

import sys, traceback

from PIL import Image

import terminedia as TM
from terminedia import V2
from terminedia.input import KeyCodes
from terminedia.transformers.library import box_transformers

"""
Early version of paint-app for the terminal, using Terminedia.

I apologize for the UI elements mixed with logic  - as terminedia widget and
event system evolves, we shuld get better abstractions and separation.
"""

class CancelledException(Exception):
    pass


class SimplePaintTool:
    erase = False
    def __init__(self, drawable):
        self.reset(drawable)

    def reset(self, drawable):
        self.drawable = drawable
        self.last_set = None

    def set_point(self, pos):
        if self.last_set:
            self.drawable.line(pos, self.last_set, erase=self.erase)
            self.last_set = None
        elif not self.erase:
            self.drawable.set(pos)
        else:
            self.drawable.set(pos)
        # self.last_set = pos


class SimpleEraseTool(SimplePaintTool):
    erase = True


class Painter():
    active_widgets = []

    def __init__(self):
        self.sc = TM.Screen()
        self.pointer = TM.Sprite(TM.shape((1,1)))
        self.pos = V2(0,0)
        self.pointer.shape[0,0] = "*"
        self.pointer.transformers.append(TM.Transformer(char=lambda char, tick: char if (tick // 8) %2 else TM.TRANSPARENT))
        self.sc.shape.sprites.add(self.pointer)
        TM.context.fps = 20

    def event_setup(self):
        TM.events.Subscription(TM.events.KeyPress, self.key_dispatcher)
        TM.events.Subscription(TM.events.MousePress, self.mouse_click)
        TM.events.Subscription(TM.events.MouseMove, self.mouse_move)

    def tool_setup(self):
        self.global_shortcuts = {
            "<space>": (None, "Paint pixel"),
            "←↑→↓": (None, "Move cursor"),
            "x": (None, "Toggle drawing"),
            "v": (None, "Line to last point"),
            "s": (self.save, "Save"),
            "c": (self.pick_color, "Choose Color"),
            "b": (self.pick_background, "Background Color"),
            "l": (self.pick_character, "Pick Char"),
            "i": (self.insert_image, "Paste Image"),
            "e": ((lambda e: setattr(self, "active_tool", self.tools["erase"])), "Erase"),
            "p": ((lambda e: setattr(self, "active_tool", self.tools["paint"])), "Paint"),
            "h": (self.toggle_help, "Toggle help"),
            "q": (self.quit, "Quit"),
        }

        for shortcut, (method, doc) in self.global_shortcuts.items():
            if method is None:
                continue
            if len(shortcut) > 1:
                shortcut = getattr(TM.input.KeyCodes, shortcut)
            TM.events.Subscription(TM.events.KeyPress, method, guard=(lambda s: lambda event: event.key == s)(shortcut))

        self.tools = {
            "paint": SimplePaintTool(self.sc.shape.draw),
            "erase": SimpleEraseTool(self.sc.shape.draw)
        }

    def state_reset(self):
        self.dirty = False
        self.active_tool = self.tools["paint"]
        self.active_tool.reset(self.sc.draw)
        self.continous_painting = False
        self.help_active = False
        self.toggle_help()

    def run(self):
        with self.sc:
            self.tool_setup()
            self.event_setup()
            self.state_reset()

            asyncio.run(TM.terminedia_main(screen=self.sc))
            # reached when a QuitLoop event is dispatched
            self.sc.commands.moveto(self.sc.size)


    def key_dispatcher(self, event):
        key = event.key
        width = 1
        if isinstance(self.sc.context.char, TM.unicode.Character) and self.sc.context.char.width=="W":
            width = 2
        if key == KeyCodes.RIGHT and \
                self.pos.x < self.sc.size.x:
            self.pos += (width, 0)
        elif key == KeyCodes.LEFT and \
                self.pos.x > 0:
            self.pos -= (width, 0)
        elif key == KeyCodes.DOWN and \
                self.pos.y < self.sc.size.y:
            self.pos += (0, 1)
        elif key == KeyCodes.UP and \
                self.pos.y > 0:
            self.pos -= (0, 1)
        if key == " ":
            self.active_tool.set_point(self.pos)
            self.active_tool.last_set = self.pos
            self.dirty = True
        if key == "v":
            if getattr(self.active_tool, "one_to_last_click", False):
                self.active_tool.last_set = self.active_tool.one_to_last_click
                self.active_tool.one_to_last_click = None
            self.active_tool.set_point(self.pos)
            self.active_tool.last_set = self.pos
            self.dirty = True
        if key == "x":
            self.continous_painting = ~self.continous_painting
            self.active_tool.last_set = None

        if self.continous_painting:
            self.active_tool.set_point(self.pos)
            self.active_tool.last_set = self.pos
            self.dirty = True

    async def quit(self, event=None):
        if self.dirty:
            confirm = await self._input("Confirm quit without save? (y/N)", width=3)
            if confirm.lower() != "y":
                return
        TM.events.Event(TM.events.QuitLoop)

    def mouse_click(self, event):
        #if not TM.inkey() == "v":
        self.active_tool.one_to_last_click = self.active_tool.last_set
        self.active_tool.last_set = None
        self.active_tool.set_point(event.pos)
        self.active_tool.last_set = event.pos
        self.pos = event.pos
        self.dirty = True

    def mouse_move(self, event):
        if event.buttons:
            self.active_tool.set_point(event.pos)
            self.active_tool.last_set = event.pos
            self.dirty = True
        self.pos = event.pos

    async def _input(self, label, pos=(0,3), default="", width=30):

        text = default
        text_picked = False
        def _pick_text(entry, event=None):
            nonlocal text_picked, text
            if not entry.value:
                return
            text = entry.value
            self.file_name = entry.value

            text_picked = True
            widget.kill()
            label_w.kill()

        def _cancel(entry, event=None):
            nonlocal text_picked, text
            text = ""
            text_picked = True
            widget.kill()
            label_w.kill()

        label_w = TM.widgets.Label(self.sc, pos=pos, text=label)
        widget = TM.widgets.Entry(self.sc, value=text, pos=V2(pos) + (len(label) + 1, 0), width=width, enter_callback=_pick_text, esc_callback=_cancel)

        while not text_picked:
            await asyncio.sleep(0.1)

        return text

    async def insert_image(self, event=None):

        size=(100,50)
        img_path = await self._input("Load image:")
        if not img_path:
            return

        try:
            img_meta = Image.open(img_path)
        except OSError:
            await self._message(f"Can't open file {img_path}")
            return

        x, y = self.sc.size
        size_txt = await self._input("Paste width in char blocks ({x}):", width=4)
        if not size_txt:
            width = x
        else:
            try:
                width = int(size_txt)
            except ValueError:
                await self._message(f"Invalid width {size_txt}")
                return

        proportion = width / img_meta.size[0]
        height = int(img_meta.size[1] * proportion)

        img = TM.shape(img_path, size=(width, height), promote=True, resolution="square")
        self.sc.shape.draw.blit(self.pos, img)
        self.dirty = True


    async def save(self, event=None):
        img = TM.shape(self.sc.size)
        file_name = getattr(self, "file_name", "")
        new_file_name = await self._input("Save file name:", default=file_name)
        if not new_file_name:
            await self._message("Saving canceled")
            return

        self.file_name = new_file_name

        active_sprites = {sprite: sprite.active for sprite in self.sc.sprites}
        for sprite in self.sc.sprites:
            sprite.active = False
        img.draw.blit((0, 0), self.sc.shape)
        asyncio.create_task(self._message(f"SAVING {self.file_name!r}"))
        await asyncio.sleep(0)
        for sprite in self.sc.sprites:
            if sprite in active_sprites:
                sprite.active = active_sprites[sprite]
        img.render(output=self.file_name, backend=("ANSI" if self.file_name.lower()[-4:] != "html" else "HTML"))
        self.dirty = False

    async def _message(self, text):
        msg = TM.widgets.Label(self.sc, text=text, padding=2, border=True, pos=(self.sc.size.x // 2 - len(text) // 2 - 1,3))
        await asyncio.sleep(2)
        msg.kill()

    async def pick_character(self, options):
        options = {
            "█": "█",
            "*": "*",
            "#": "#",
            "⏶": "⏶",
            "type": "type",
            "search": "search"
        }


        selector = TM.widgets.Selector(self.sc, options, pos=(0,0), border=True, cancellable=True) # select=_pick_option, border=True)
        try:
            char = await selector
        except TM.widgets.WidgetCancelled:
            return
        if char == "type":
            char = (await self._input("Type character:", width=2))
            if not char:
                return
            char = char[0]
        elif char == "search":
            try:
                search = await self._input("Unicode char name :", width=40)
            except WidgetCancelled:
                return
            options = TM.unicode.lookup(search)
            if not options:
                self._message("Character not found")
                return
            if len(options) == 1:
                char = options[0]
            elif options:
                options = {f"{str(option)} - {option.name[0:20]}": str(option) for option in options}
                extended_selector = TM.widgets.Selector(self.sc, options, pos=(0,0), border=True, cancellable=True)
                try:
                    char = await extended_selector
                except WidgetCancelled:
                    return

        self.sc.context.char = char


    async def pick_color(self, event=None):
        try:
            self.sc.context.foreground = await self._pick_color(event)
        except TM.widgets.WidgetCancelled:
            pass

    async def pick_background(self, event=None):
        try:
            color = await self._pick_color(event)
            self.sc.context.background = color if color != TM.DEFAULT_FG else TM.DEFAULT_BG
        except TM.widgets.WidgetCancelled:
            pass

    async def _pick_color(self, event=None):
        colors = {
            "default": TM.DEFAULT_FG,
            "white":  TM.Color("white"),
            "red":  TM.Color("red"),
            "green":  TM.Color("green"),
            "blue":  TM.Color("blue"),
            "orange":  TM.Color((255,192,0)),
            "yellow":  TM.Color("yellow"),
            "black":  TM.Color("black"),
            "other": "other"
        }
        color_label = None
        color_widget = None

        color_widget = TM.widgets.Selector(self.sc, colors, pos=(0,0), border=True, cancellable=True)
        color = await color_widget
        if color == "other":
            try:
                color_label = TM.widgets.Label(self.sc, pos=(0,3), text="Color: ")
                color_str = (await TM.widgets.Entry(self.sc, pos=(8, 3), width=15, cancellable=True)).strip()
                try:
                    color = literal_eval(color_str)
                except (ValueError, SyntaxError):
                    pass
                try:
                    color = TM.Color(color_str)
                except ValueError:
                    raise TM.widgets.WidgetCancelled()

            finally:
                color_label.kill()
        return color


    def toggle_help(self, event=None):
        if not getattr(self, "help_sprite", None):
            rows = ceil(len(self.global_shortcuts) // 3) + 1
            sh = TM.shape((self.sc.size.x,  rows + 2))
            sh.text[1].add_border(transform=box_transformers["DOUBLE"])
            col_width = (sh.size.x - 2) // 3
            current_row = 0
            sh.context.foreground = TM.DEFAULT_FG
            current_col = 0
            actual_width = min(col_width, 25)
            for shortcut, (callback, text) in self.global_shortcuts.items():
                sh.text[1][current_col * col_width + 1, current_row] = f"[effects: bold|underline]{shortcut}[/effects]{text:>{actual_width - len(shortcut) - 3}s}"
                current_row += 1
                if current_row >= rows:
                    current_col += 1
                    current_row = 0

            self.help_sprite = TM.Sprite(sh, alpha=False)
        if not self.help_active:
            self.help_sprite.pos = (0, self.sc.size.y - self.help_sprite.rect.height)
            self.sc.sprites.add(self.help_sprite)
            self.help_active = True
        else:
            self.help_sprite.kill()
            self.help_active = False

    @property
    def pos(self):
        return self.pointer.pos
    @pos.setter
    def pos(self, value):
        self.pointer.pos = value

def run():
    painter = Painter()
    painter.run()

if __name__ == "__main__":
    run()
