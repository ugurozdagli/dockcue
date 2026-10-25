# Third-party notices

DockCue's own source is MIT-licensed. Dependencies retain their respective licenses.
The release builder collects their installed license files into `licenses/`.

| Component | Project | License family |
| --- | --- | --- |
| hidapi Python binding / HIDAPI | https://github.com/trezor/cython-hidapi | BSD / HIDAPI license options; see bundled notices |
| websocket-client | https://github.com/websocket-client/websocket-client | Apache-2.0 |
| CustomTkinter | https://github.com/TomSchimansky/CustomTkinter | MIT |
| pystray | https://github.com/moses-palmer/pystray | LGPL-3.0 |
| Pillow | https://github.com/python-pillow/Pillow | MIT-CMU / HPND and component notices |
| darkdetect | https://github.com/albertosottile/darkdetect | BSD-3-Clause |
| six | https://github.com/benjaminp/six | MIT |
| packaging | https://github.com/pypa/packaging | Apache-2.0 / BSD-2-Clause |
| Python | https://www.python.org | PSF License |
| Tcl/Tk | https://www.tcl.tk | Tcl/Tk license |
| PyInstaller bootloader | https://pyinstaller.org | GPL with bootloader exception |

The Windows build uses unmodified dependencies. To rebuild or modify library
components, use the source links and pinned versions in the requirements files.

Protocol background: [HeadsetControl](https://github.com/Sapd/HeadsetControl) and
[HeadsetControlA50Gui](https://github.com/lluiseduardo-silva/HeadsetControlA50Gui)
provided useful public protocol context. DockCue's supported A50 X behavior was
validated on real hardware; support for other A50 generations is not implied.

Logitech, Logitech G and ASTRO are trademarks of their respective owners. Names
are used to identify device compatibility. DockCue's icon is an original generic
headset drawing and does not use the Logitech G logo.
