terminedia paint
=================



Interactive app to create ASCII-art and Unicode art in
an interactive way directly from the terminal


![draft screenshot](logo0.png?raw=true "Screenshot")

This is very early work, but already allows on to have some fun.
To install: `pip install --user terminedia-paint`

To install development version:
`pip install --user git+https://github.com/jsbueno/terminedia-paint.git && terminedia-paint`

(`--user` can be omitted if you have an active virtual environment)

(install will pull along a suitable version of the terminedia Unicode Art framework

Currently it works on Linux, Mac and other Posix software -
there might be some limited functionality under windows
(no mouse suport yet though). It might work fine under WSL2.

This is in very ealy stage - the main idea
is to enable people to create text-art in by
using terminedia's capabilities, without having
to resort to Python programming.

This is also set as a demonstration project
for terminedia: https://github.com/jsbueno/terminedia

How to run: pip install the main branch directly with
and run "terminedia-paint" on the terminal.

Saving and exporting
------------------------
: the file extension one use to save a file will determine the file type:
    if the ".snapshot" suffix is used, it is a reloadable internal format, that can be loaded back
    with "insert image". (Load occurs at cursor position).
    Other supported formats are "HTML": a hard-coded HTML with characters using inline-style
    for positioning and color, and "ANSI" (the default file format):
    a text file  which will be correctly displayed in the terminal
    when printed (e.g. with the `cat` command)

The typing tool
-----------------

The on-screen display has no help to the "typing tool"
(entered by pressing "t" on the app screen):
the software pointer will be shut down, and arrow keys
won't move it (but the mouse will). start typing to
enter text directly on the image, press one of the
arrow keys to change text direction at any point.

This is the "line" typing mode.
There is also the "path" typing mode:

In the typing tool, click on any sequence of
full block characters, and begin typing: all characters typed will follow the
line (or area, in an exquisite way), of full blocks.

Press <ESC> to leave the typing tool and return to
painting.


