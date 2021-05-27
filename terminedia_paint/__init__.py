import asyncio
import time
from ast import literal_eval

import sys, traceback


import terminedia as TM
from terminedia import V2
from terminedia.input import KeyCodes



class ProgramEnd(Exception):
    pass


class SimplePaintTool:
    def __init__(self, screen):
        self.sc = screen

    def set_point(self, pos):
        self.sc.draw.set(pos)


class SimpleEraseTool(SimplePaintTool):

    def set_point(self, pos):
        self.sc.draw.reset(pos)


class Painter():
    active_widgets = []

    def __init__(self):
        self.sc = TM.Screen()
        self.pointer = TM.Sprite(TM.shape((1,1)))
        self.pos = V2(0,0)
        self.pointer.shape[0,0] = "*"
        self.pointer.transformers.append(TM.Transformer(char=lambda char, tick: char if tick%2 else TM.TRANSPARENT))
        self.sc.shape.sprites.add(self.pointer)

    def event_setup(self):
        TM.events.Subscription(TM.events.KeyPress, self.key_dispatcher)
        TM.events.Subscription(TM.events.MousePress, self.mouse_click)
        TM.events.Subscription(TM.events.MouseMove, self.mouse_move)

    def tool_setup(self):
        global_shortcuts = {
            "q": self.quit,
            "s": self.save,
            "c": self.pick_color,
            "l": self.pick_character,
            "e": (lambda e: setattr(self, "active_tool", self.tools["erase"])),
            "p": (lambda e: setattr(self, "active_tool", self.tools["paint"])),
        }

        for shortcut, method in global_shortcuts.items():
            TM.events.Subscription(TM.events.KeyPress, method, guard=(lambda s: lambda event: event.key == s)(shortcut))

        self.tools = {
            "paint": SimplePaintTool(self.sc),
            "erase": SimpleEraseTool(self.sc)
        }

    def state_reset(self):
        self.active_tool = self.tools["paint"]
        self.continous_painting = False

    def run(self):
        with self.sc:
            self.tool_setup()
            self.event_setup()
            self.state_reset()

            try:
                asyncio.run(TM.terminedia_main(screen=self.sc))
            except ProgramEnd:
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
        if key == "x":
            self.continous_painting = ~self.continous_painting

        if self.continous_painting:
            self.active_tool.set_point(self.pos)

    def quit(self, event=None):
        raise ProgramEnd()

    def mouse_click(self, event):
        self.active_tool.set_point(event.pos)
        self.pos = event.pos

    def mouse_move(self, event):
        if event.buttons:
            self.active_tool.set_point(event.pos)
        self.pos = event.pos

    async def save(self, event=None):
        img = TM.shape(self.sc.size)

        def _pick_file_name(entry):
            nonlocal file_name_picked
            if not entry.value:
                return
            self.file_name = entry.value

            file_name_picked = True
            fn_widget.kill()
            label.kill()

        file_name = getattr(self, "file_name", "")

        label = TM.widgets.Label(self.sc, pos=(0, 3), text="Filename:")
        fn_widget = TM.widgets.Entry(self.sc, pos=(11, 3), width=30, enter_callback=_pick_file_name)
        file_name_picked = False


        while not file_name_picked:
            await asyncio.sleep(0.1)


        active_sprites = {sprite: sprite.active for sprite in self.sc.sprites}
        for sprite in self.sc.sprites:
            sprite.active = False
        img.draw.blit((0, 0), self.sc.shape)
        for sprite in self.sc.sprites:
            sprite.active = active_sprites[sprite]
        msg = TM.widgets.Label(self.sc, text=f"SAVING {self.file_name!r}", padding=2, border=True, pos=(self.sc.size.x//2,3))
        img.render(output=self.file_name, backend=("ANSI" if self.file_name.lower()[-4:] != "html" else "HTML"))
        await asyncio.sleep(2)
        msg.kill()

    def pick_character(self, options):
        options = {
            "█": "█",
            "*": "*",
            "#": "#",
            "O": "O",
            "type": "type",
            "search": "search"
        }

        label = None
        selector = None

        def _search_text(entry):
            options = TM.unicode.lookup(entry.value)
            if len(options) == 1:
                self.sc.context.char = options[0]
            elif options:
                pass
            else:
                pass
            entry.kill()
            label.kill()
            selector.kill()

        def _type_text(entry):
            self.sc.context.char = entry.value[0]
            entry.kill()
            label.kill()
            selector.kill()

        def _pick_option(selector):
            nonlocal label
            if selector.value == "type":
                label = TM.widgets.Label(self.sc, pos=(0,12), text="Character: ")
                entry = TM.widgets.Entry(self.sc, pos=(10, 12), width=2, enter_callback=_type_text)
            elif selector.value == "search":
                label = TM.widgets.Label(self.sc, pos=(0,12), text="Search: ")
                entry = TM.widgets.Entry(self.sc, pos=(10, 12), width=25, enter_callback=_search_text)
            else:
                self.sc.context.char = selector.value
                selector.kill()
        selector = TM.widgets.Selector(self.sc, options, pos=(0,0), select=_pick_option, border=True)


    def pick_color(self, event=None):
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
        def _color_from_text(entry):
            try:
                color = None
                try:
                    color = TM.Color(literal_eval(entry.value.strip()))
                except (ValueError, SyntaxError):
                    try:
                        color=TM.Color(entry.value.strip())
                    except ValueError:
                        pass

                if color is not None:
                    self.sc.context.foreground = color
                entry.kill()
                color_label.kill()
                color_widget.kill()
            except Exception as err:
                pass
                # sys.stderr.write(f"{err}\n")
                # sys.stderr.writelines("".join(traceback.format_tb(sys.last_traceback)))


        def _pick_color(selector):
            nonlocal color_label
            if selector.value == "other":
                color_label = TM.widgets.Label(self.sc, pos=(0,12), text="Color: ")
                entry = TM.widgets.Entry(self.sc, pos=(8, 12), width=15, enter_callback=_color_from_text)
            else:
                self.sc.context.foreground = selector.value
                selector.kill()
        color_widget = TM.widgets.Selector(self.sc, colors, pos=(0,0), select=_pick_color, border=True)

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
