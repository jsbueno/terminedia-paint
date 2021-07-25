import asyncio
import time
import random
from ast import literal_eval
from collections.abc import Sequence
from math import ceil
from pathlib import Path

import sys, traceback

from PIL import Image

import terminedia as TM
from terminedia import V2
from terminedia.input import KeyCodes
from terminedia.transformers.library import box_transformers
from terminedia.values import EMPTY
from terminedia.widgets import WidgetCancelled

"""
Early version of paint-app for the terminal, using Terminedia.

I apologize for the UI elements mixed with logic  - as terminedia widget and
event system evolves, we shuld get better abstractions and separation.
"""

class CancelledException(Exception):
    pass


class SimplePaintTool:
    erase = False
    def __init__(self, drawable_cmds):
        self.reset(drawable_cmds)

    def reset(self, drawable_cmds):
        self.draw = drawable_cmds
        self.last_set = None

    def toggle_point(self, pos):
        open("bla11.txt", "at").write(repr(self.draw.get(pos)) + "\n")
        value = self.draw.get(pos)
        if isinstance(value, TM.Color):
            value = value == self.draw.context.foreground
        elif isinstance(value, Sequence):
            value = value[0]
            value = False if value == " " else bool(value)
        if not value:
            self.draw.set(pos)
            self.last_set = pos
        else:
            self.draw.reset(pos)

    def set_point(self, pos, interpolate=False):
        if self.last_set and interpolate:
            self.draw.line(pos, self.last_set, erase=self.erase)
            self.last_set = None
        elif not self.erase:
            self.draw.set(pos)
        else:
            self.draw.reset(pos)

class PathTypeTool:
    """allows free typing following a previous drawn path on the screen"""
    # TBD
    def __init__(self, drawable_cmds):
        self.reset(drawable_cmds)


class SimpleEraseTool(SimplePaintTool):
    erase = True


resolutions = {
    1: ("block", V2(1, 1)),
    2: ("square", V2(1, .5)),
    4: ("high", V2(.5, .5)),
    6: ("sextant", V2(.5, 1 / 3)),
    8: ("braille", V2(.5, .25)),
}

POINTER_CHAR = "*"


class Painter():
    active_widgets = []

    def __init__(self):
        self.sc = TM.Screen()
        self.sc.shape.undo_active = True
        self.pointer = TM.Sprite(TM.shape((1,1)))
        self.pointer.transformers.append(TM.Transformer(char=lambda char, tick: char if (tick // 8) %2 else TM.TRANSPARENT))
        self.sc.shape.sprites.add(self.pointer)
        TM.context.fps = 20

    def event_setup(self):
        TM.events.Subscription(TM.events.KeyPress, self.key_dispatcher)
        TM.events.Subscription(TM.events.MouseClick, self.mouse_click)
        TM.events.Subscription(TM.events.MouseDoubleClick, self.mouse_double_click)
        TM.events.Subscription(TM.events.MouseRelease, self.mouse_release)
        TM.events.Subscription(TM.events.MouseMove, self.mouse_move)

    def tool_setup(self):
        self.global_shortcuts = {
            "<space>": (None, "Toggle pixel"),
            "←↑→↓": (None, "Move cursor"),
            "x": (None, "Toggle drawing"),
            "v": (None, "Line to last point"),
            "s": (self.save, "Save"),
            "c": (self.pick_color, "Choose Color"),
            "b": (self.pick_background, "Background Color"),
            "l": (self.pick_character, "Pick Char"),
            "i": (self.insert_image, "Paste Image"),
            "1": (lambda e=None: setattr(self, "resolution", 1), "Draw with full chars"),
            "2": (lambda e=None: setattr(self, "resolution", 2), "Draw with 1/2 blocks"),
            "4": (lambda e=None: setattr(self, "resolution", 4), "Draw with 1/4 blocks"),
            "6": (lambda e=None: setattr(self, "resolution", 6), "Draw with 1/6 blocks"),
            "8": (lambda e=None: setattr(self, "resolution", 8), "Draw with braille dots"),
            "e": ((lambda e=None: setattr(self, "active_tool", self.tools["erase"])), "Erase"),
            "p": ((lambda e=None: setattr(self, "active_tool", self.tools["paint"])), "Paint"),
            "F": ((lambda e=None: self.sc.draw.fill()), "Fill Image"),
            "f": ((lambda e=None: self.drawable.draw.floodfill(self.pos)), "Flood Fill"),
            "^z":((lambda e=None: self.sc.shape.undo()), "Undo"),
            "^y": ((lambda e=None: self.sc.shape.redo()), "Redo"),
            "h": ("toggle", "Toggle help"), #(self.toggle_help, "Toggle help"),
            "q": (self.quit, "Quit"),
        }

        self.tools = {
            "paint": SimplePaintTool(self.sc.shape.draw),
            "erase": SimpleEraseTool(self.sc.shape.draw)
        }
        self.menu = TM.widgets.ScreenMenu(self.sc, self.global_shortcuts, columns=3, focus_position=None)

    def state_reset(self):
        self.resolution = 1
        self.dirty = False
        self.active_tool = self.tools["paint"]
        self.active_tool.reset(self.sc.draw)
        self.continuous_painting = False
        # self.help_active = False
        if getattr(self, "menu", None):
            self.menu.sprite.active = True
        self.drag_drawing = False
        self.resolution = 1
        self.pos = V2(0,0)
        self.last_painting_move = (-1, -1)


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
        if self.resolution == 1 and isinstance(self.sc.context.char, TM.unicode.Character) and self.sc.context.char.width=="W":
            width = 2
        previous_pos = self.pos
        if key == KeyCodes.RIGHT and \
                self.pos.x < self.drawable.size.x:
            self.pos += (width, 0)
        elif key == KeyCodes.LEFT and \
                self.pos.x > 0:
            self.pos -= (width, 0)
        elif key == KeyCodes.DOWN and \
                self.pos.y < self.drawable.size.y:
            self.pos += (0, 1)
        elif key == KeyCodes.UP and \
                self.pos.y > 0:
            self.pos -= (0, 1)
        if key == " ":
            self.active_tool.last_set = None
            self.active_tool.toggle_point(self.pos)
            self.active_tool.last_set = self.pos
            self.dirty = True
        if key == "v":
            if getattr(self.active_tool, "one_to_last_click", False):
                self.active_tool.last_set = self.active_tool.one_to_last_click
                self.active_tool.one_to_last_click = None
            self.active_tool.set_point(self.pos, interpolate=True)
            self.active_tool.last_set = self.pos
            self.dirty = True
        if key == "x":
            self.continuous_painting = ~self.continuous_painting
            self.active_tool.last_set = self.pos if not self.continuous_painting else None

        if previous_pos != self.pos and self.continuous_painting:
            self.active_tool.set_point(previous_pos)
            #self.active_tool.set_point(self.pos)
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
        # self.active_tool.last_set = event.pos
        self.pointer.pos = event.pos
        self.active_tool.toggle_point(self.pos)
        self.drag_drawing = False
        self.dirty = True
        self.last_painting_move = event.pos

    def mouse_double_click(self, event):
        #FIXME - provisional to test double-click event
        self.sc.context.char = random.choice("#*!|><")

    def mouse_move(self, event):
        if event.tick - getattr(self, "last_dragging_tick", 0) > 1:
            self.drag_drawing = False
        if event.buttons:
            if getattr(self, "_undo_group", None) is None:
                self._undo_group =  True
                self.sc.shape.undo_group_start()
            self.pointer.pos = event.pos
            pos = self.pos
            if self.last_painting_move == pos:
                # Avoids acummulating several repeated paiting events on the same position -
                # each of which generates one UNDO state.
                # FIXME: have a terminedia public 'undo-group-start' to undo a full stroke at once.
                return
            self.active_tool.set_point(pos, interpolate=self.drag_drawing)
            self.active_tool.last_set = pos
            self.drag_drawing = True
            self.last_dragging_tick = event.tick
            self.dirty = True
            self.last_painting_move = pos
        else:
            self.pointer.pos = event.pos

    def mouse_release(self, event):
        if getattr(self, "_undo_group", None):
            self.sc.shape.undo_group_end()
            self._undo_group = None

    async def _input(self, label, pos=(0,3), default="", width=30):

        text = default

        label_w = TM.widgets.Label(self.sc, pos=pos, text=label)

        widget = TM.widgets.Entry(self.sc, value=text, pos=V2(pos) + (len(label) + 1, 0), width=width, cancellable=True)
        try:
            text = await widget
        except TM.widgets.WidgetCancelled:
            text = ""
        finally:
            label_w.kill()

        return text

    async def load_image_as_shape(self, img_path):
        try:
            #self.sc.__exit__(None, None, None)
            #import os; os.system("reset")
            shape = TM.shape(img_path)
        except (OSError, NotImplementedError):

            await self._message(f"Can't open file {img_path}")
            return
        self.sc.draw.blit(self.pos, shape)


    async def insert_image(self, event=None):
        """Attempts to open an image as a pixel-based image file with PIL

        If that fails fallback to reading a terminedia-shape - which can load
        pure text (without markup, for the time being) and shape "snapshot" files
        """

        img_path = await self._input("Load image:")
        if not img_path:
            return
        try:
            img_meta = Image.open(img_path)
        except OSError:
            await self.load_image_as_shape(img_path)
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
        path = Path(self.file_name)
        backend = path.suffix.strip(".").upper()
        if backend not in ("HTML", "SNAPSHOT"):
            backend = "ANSI"
        img.render(output=path, backend=backend)
        self.dirty = False

    async def _message(self, text):
        msg = TM.widgets.Label(self.sc, text=text, padding=2, border=True, pos=(self.sc.size.x // 2 - len(text) // 2 - 1,3))
        await asyncio.sleep(2)
        msg.kill()

    async def pick_character(self, event=None):
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
            search = await self._input("Unicode char name :", width=40)
            if not search:
                return

            options = TM.unicode.lookup(search)
            if not options:
                self._message("Character not found")
                return
            if len(options) == 1:
                char = options[0]
            elif options:
                options = {f"{str(option)} - {option.name[0:20]}": str(option) for option in options}
                extended_selector = TM.widgets.Selector(self.sc, options, pos=(0,0), border=True, max_height=(self.sc.size.y - self.menu.shape.size.y - 2),  cancellable=True)
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

        new_colors = {}
        for color_label, color in list(colors.items()):
            if color is TM.DEFAULT_FG or color == TM.Color("black") or not isinstance(color, TM.Color):
                new_label = color_label
            elif color == TM.Color('white'):
                new_label = f"[foreground: black][background: white]{color_label}"
            else:
                new_label = f"[foreground: {color.html}]{'[background: white]' if color == TM.Color('white') else ''}{color_label}"
            new_colors[new_label] = color
        colors = new_colors

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

    @property
    def pos(self):
        physical_pos = self.pointer.pos
        res = resolutions[self.resolution][1]
        factor = 1/res[0], 1/res[1]
        pos = V2(
            physical_pos[0] * factor[0] + self._remainder_pos[0],
            physical_pos[1] * factor[1] + self._remainder_pos[1]
        ).as_int
        return pos
    @pos.setter
    def pos(self, value):
        res = resolutions[self.resolution][1]
        factor = 1/res[0], 1/res[1]
        physical_pos = V2(value[0] // factor[0], value[1] // factor[1]).as_int
        remainder_pos = self._remainder_pos = V2(value[0] % factor[0], value[1] % factor[1]).as_int
        self.pointer.pos = physical_pos

        if self.resolution == 1:
            return
        self.pointer.shape[0,0] = EMPTY
        pointer_draw = (self.pointer.shape if value == 1 else getattr(self.pointer.shape, resolutions[self.resolution][0])).draw
        pointer_draw.set(remainder_pos)
        # todo: change pointer char to the proper pixel in the proper resolution

    @property
    def resolution(self):
        return self.__dict__["resolution"]

    @resolution.setter
    def resolution(self, value):
        if value not in resolutions:
            return
        self._remainder_pos = 0, 0
        self.drawable = drawable = self.sc.shape if value == 1 else getattr(self.sc.shape, resolutions[value][0])

        self.tools["paint"].reset(drawable.draw)
        self.tools["erase"].reset(drawable.draw)
        self.__dict__["resolution"] = value
        self.pointer.shape[0,0] = EMPTY if value != 1 else POINTER_CHAR


def run():
    painter = Painter()
    painter.run()

if __name__ == "__main__":
    run()
