# PYUI(Python UI)

This project is targeted to make cross platform applications using python.PYUI is a layout pre-compiled framework for making python applications in very lightweight sizes. It uses a xml layouting system for defining layouts, python for logic and **PYWebview** as the renderer.Leading to a blank application size only 16MB compared to heavyweight rendering systems cosing 50+ MB or TKinter that has very legacy thread-unsafe architecture

## Motivation
1.**Making General Purpose Applications:** This project is driven by the motivation of making a framework over python that can be used to make general purpose applications with little or no learning curve.

2.**Smaller learning curve:** Recent solutions for UI development mostly are hard to learn and manage. However we adopted age-old xml layouting system that makes defining UI easy for anyone with little xml/html knowlege. 

3.**Support of Python libaries and modules:** On the logic side python can use used to it's Limit, also the threadsafe nature of the framework helps in extreme scalability.

4.**Compiled Layout and Reusibility:** This framework has pre-compiled layouting system.So errors in layout are identified on runtime. Also Layout supports re-usibility using **PYUI Components**.

## Key Features of PYUI API
1. **DOM Manipulation:** One can change dom components from python side.There style,class,innertext and other attributes.

2. **PYUI Custom Syscalls:** Using this one can extend PYUI to support any JS libaries(chart.js and etc) by writing minimal Javascript.Or can use to commiunicate between JS ans Python runtime if needed without touching internal sockets.

3. **PYUI Hooks:** If some DOM updates are fast and can be lossy but realtime one can use PYUI Hooks.This can be mostly used to stream video or audio from Python to JS runtime

4. **Window Management:** A PYUI forms contain can contain more than one view(window) and **PYUI** provides apis to change windows dynamically. Also Exposes Webview object for *PYwebview* for changing the application window

5. **Forms Management:** **PYUI** provides dedicated apis to show and hide forms.

## Getting Started

### Installing PYUI 

PYUI has been tested only on Windows(x64) right now in v1.0 it will support both Windows and linux. However you can still use it in linux by building your own **PYUI** Package from source by compiling the xmlparser and changing few lines of code in *PYUI/compiler*.

1.Get the PYUI using 

    pip install pyui-desktop

### Setting up project

    python -m PYUI.create <directory-of-project>

This will generate boilerplate project. Following folder and files will be generated in the given directory.

    layout
    code
    layout/JS
    layout/styles
    code/index.py
    code/__init__.py
    layout/index.xml
    settings.py


### Compiling project

To compile to a PYUI project and run it

    python -m PYUI.buildtools --compile <directory-of-project> --run

This command will compile your project into a PYUI project and run it. Within few seconds(depending on project size) you can see you layout

To compile without running project

    python -m PYUI.buildtools --compile <directory-of-project>

It will save your project in *build/temp_xxxxx.yyyy* (see last line of buildscript output). To launch the project go to the directory and run:

    python bootstrap.py

It will launch your UI

### HotReloading Layouts

You can hot-reload the layout for faster UI development.

    python -m PYUI.buildtools --hotreload <layout-xml-file>

Changing the xml file will reload the UI automatically

**Note:** Use the *--keepontop* flag to keep the UI on top always

**Hot-Reloading-bug:** Current version(0.5) has a bug in hotreloading that non tailwind css are not applied.Will be fixed in 0.5.1

For further API references for XML and PYUI check the documentation.

Documentation: [PYUI Documentation](https://akalabayapal.github.io/PYUI-docs/)

**Note:** Documentation is yet not completed

## Changes and Contribution

Contribution in this project is open and highly welcomed.


## Credits

PyWebview: https://github.com/r0x0r/pywebview

