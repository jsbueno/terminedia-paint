import asyncio

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


class Painter():
    active_widgets = []

    def __init__(self):
        self.sc = TM.Screen()
        self.pos = V2(0,0)

    def event_setup(self):
        TM.events.Subscription(TM.events.KeyPress, self.key_dispatcher)
        TM.events.Subscription(TM.events.MousePress, self.mouse_click)
        TM.events.Subscription(TM.events.MouseMove, self.mouse_move)

    def tool_setup(self):
        global_shortcuts = {
            "q": self.quit,
            "s": self.save,
            "c": self.pick_color,
        }

        for shortcut, method in global_shortcuts.items():
            TM.events.Subscription(TM.events.KeyPress, method, guard=(lambda s: lambda event: event.key == s)(shortcut))

        self.tools = {
            "paint": SimplePaintTool(self.sc)
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
        if key == KeyCodes.RIGHT and \
                self.pos.x < self.sc.size.x:
            self.pos += (1, 0)
        elif key == KeyCodes.LEFT and \
                self.pos.x > 0:
            self.pos -= (1, 0)
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

    def save(self):
        pass

    def pick_color(self):
        pass

if __name__ == "__main__":
    painter = Painter()
    painter.run()
