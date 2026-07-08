'''
Dev Tools Script...
'''

from PYUI.compiler import compile_layout
from PYUI.converter import save_html_file
from PYUI.buildscript import build
import PYUI.settings

import os
import argparse
import webview
import sys  # Imported to check system platforms dynamically

from PYUI.tailwindBuilder import build_global_tailwind
import time
import pickle
import shutil
import importlib.util

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import threading
import subprocess
import atexit
import stat
import pathlib
import hashlib
import queue

# FIXED: Dynamic Tailwind binary detection base fallback
TAILWIND_BINARY = "tailwind/tailwind.exe" if sys.platform == "win32" else "tailwind/tailwind"

DEFAULT_WINDOW_CONFIG = {
    "title": "PyUI Application",
    "url": None,
    "html": None,
    "js_api": None,
    "width": 800,
    "height": 600,
    "x": None,
    "y": None,
    "screen": None,
    "resizable": True,
    "fullscreen": False,
    "min_size": (200, 100),
    "hidden": False,
    "frameless": False,
    "easy_drag": True,
    "shadow": False,
    "focus": True,
    "minimized": False,
    "maximized": False,
    "menu": [],
    "on_top": False,
    "confirm_close": False,
    "background_color": "#FFFFFF",
    "transparent": False,
    "text_select": False,
    "zoomable": False,
    "draggable": False,
    "vibrancy": False,
    "server_args": {},
    "localization": None,
}

reload_queue = queue.Queue()
watcher_queue = queue.Queue()

def calculate_md5(file_path):
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

def load_layout(file, bin_file, new):
    print("[Main Thread] Parsing binary environment layout...")
    try:
        load = pickle.load(open(bin_file, 'rb'))
        settings_map = load['form_settings']
        for key in settings_map:
            DEFAULT_WINDOW_CONFIG[key] = str(settings_map[key])
    except Exception as e:
        print(f"[Warning] Failed to load index.bin.Error: {e}")
        exit(1)

    sanitized_settings = sanitize_window_config(DEFAULT_WINDOW_CONFIG)
    sanitized_settings['url'] = os.path.abspath(file)
    if args.keepontop:
        sanitized_settings['on_top'] = True

    if not new:
        print("[Watcher Thread] Compilation complete. Queueing reload signal...")
        reload_queue.put("TRIGGER_RELOAD")
    else:  
        win = webview.create_window(**sanitized_settings)
        return win

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, file_to_watch, bin_file, temp_file_load, folder, css_file, components, settings, cooldown=0.5):
        self.cooldown = cooldown  
        self.last_triggered = 0   
        self.last_md5 = {}
        self.file_to_watch = file_to_watch
        self.bin_file = bin_file
        self.temp_file_load = temp_file_load
        self.folder = folder
        self.css_file = css_file
        self.component_list = components
        self.settings = settings

        for c in components:
            self.last_md5[c] = calculate_md5(c)
        self.last_md5[self.file_to_watch] = calculate_md5(self.file_to_watch)

    def on_modified(self, event):
        if event.is_directory:
            return
        
        if event.src_path == self.file_to_watch:
            current_time = time.time()
            md5 = calculate_md5(event.src_path)
            if current_time - self.last_triggered > self.cooldown and md5 != self.last_md5[event.src_path]:
                self.last_triggered = current_time
                self.last_md5[event.src_path] = md5
                try:
                    run(self.file_to_watch, self.bin_file, self.temp_file_load, self.folder, self.css_file, self.settings)
                except Exception as ex:
                    print("Error in script compilation:", ex)

        elif event.src_path in self.component_list:
            current_time = time.time()
            md5 = calculate_md5(event.src_path)
            if current_time - self.last_triggered > self.cooldown and md5 != self.last_md5[event.src_path]:
                self.last_triggered = current_time
                self.last_md5[event.src_path] = md5
                try:
                    run(self.file_to_watch, self.bin_file, self.temp_file_load, self.folder, self.css_file, self.settings)
                except Exception as ex:
                    print("[Error in compilation]", ex)

def observer(file_to_watch, bin_file, temp_file_load, folder, css_file, components, settings):
    path_to_watch = os.path.join(os.path.dirname(file_to_watch))  
    event_handler = FileChangeHandler(file_to_watch, bin_file, temp_file_load, folder, css_file, components, settings)
    obs = Observer()
    obs.schedule(event_handler, path=path_to_watch, recursive=True)
    obs.daemon = True

    print(f"Monitoring changes in '{file_to_watch}'...")
    obs.start()
    while True:
        signal = watcher_queue.get()
        if signal == "STOP":
            obs.stop()
            break
        
def run(file_to_watch, bin_file, temp_file_load, folder, css_file, settings: PYUI.settings):
    tree, components = compile_layout(
        os.path.abspath(file_to_watch),
        bin_file, os.path.dirname(os.path.dirname(file_to_watch)),
        isBuildSript=True, TAG_RULES_HASHMAP=settings.CompilerSettings.TAG_RULES_HASHMAP)
    
    save_html_file(
        tree, temp_file_load, '',
        HTML_MAP=settings.CompilerSettings.HTML_TAG_CONVERSION_MAP,
        LAYOUT_TAGS=settings.CompilerSettings.LAYOUT_CONTAINER_TAGS)

    if PYUI.settings.CompilerSettings.TAILWIND_ENABLED:
        if settings.CompilerSettings.HOOK_MAP['TAILWIND_STYLE_COMPILATION']:
            settings.CompilerSettings.HOOK_MAP['TAILWIND_STYLE_COMPILATION'](os.path.abspath(folder))
        # FIXED: Replaced hardcoded string with dynamic TAILWIND_BINARY
        build_global_tailwind(os.environ.get('tailwind', TAILWIND_BINARY), os.path.join(folder, 'layouts'), css_file)
    
    style_dir = os.path.join(folder, 'layouts', 'styles')
    if args.stylepath:
        for obj in os.scandir(args.stylepath):
            shutil.copy(obj, os.path.join(style_dir, os.path.basename(obj)))
    else:
        stylepath_expected = os.path.join(pathlib.Path(file_to_watch).parent, 'styles')
        if os.path.isdir(stylepath_expected):
            for obj in os.scandir(stylepath_expected):
                shutil.copy(obj, os.path.join(style_dir, os.path.basename(obj)))
    
    load_layout(temp_file_load, bin_file, False)

def HandleHotReload():
    path_of_xml = args.hotreload
    if args.settings != None:
        settingsCustom = ImportCustomSettings(args.settings)
    else:
        settingsCustom = PYUI.settings

    if not os.path.exists("temprun"):
        os.mkdir("temprun")

    folder = 'temprun/temp' + str(time.time())
   
    if not os.path.exists(folder):
        os.mkdir(folder)
        os.mkdir(os.path.join(folder, 'layouts'))
        os.mkdir(os.path.join(folder, 'layouts', 'styles'))

    bin_file = os.path.join(folder, 'layouts', 'index.bin')
    html_file = os.path.join(folder, 'layouts', 'index.html')
    css_file =  os.path.join(folder, 'layouts', 'styles', 'global.css')
    
    if settingsCustom.CompilerSettings.HOOK_MAP['COMPILATION']:
            settingsCustom.CompilerSettings.HOOK_MAP['COMPILATION'](os.path.abspath(folder))

    tree, paths_etc = compile_layout(
        os.path.abspath(path_of_xml),
        bin_file, os.path.dirname(os.path.dirname(path_of_xml)),
        isBuildSript=True,
        TAG_RULES_HASHMAP=settingsCustom.CompilerSettings.TAG_RULES_HASHMAP)
    
    if settingsCustom.CompilerSettings.HOOK_MAP['CONVERTION']:
            settingsCustom.CompilerSettings.HOOK_MAP['CONVERTION'](os.path.abspath(folder))
    
    stylesheets = save_html_file(
        tree, html_file, '',
        HTML_MAP=settingsCustom.CompilerSettings.HTML_TAG_CONVERSION_MAP,
        LAYOUT_TAGS=settingsCustom.CompilerSettings.LAYOUT_CONTAINER_TAGS,
        return_style_path=True)

    basepath = os.path.dirname(path_of_xml)
    stylesheets_absbolute_path = [os.path.join(basepath, 'styles', style_path) for style_path in stylesheets]
    paths_to_scan = paths_etc + stylesheets_absbolute_path

    if settingsCustom.CompilerSettings.TAILWIND_ENABLED:
        if settingsCustom.CompilerSettings.HOOK_MAP['TAILWIND_STYLE_COMPILATION']:
            settingsCustom.CompilerSettings.HOOK_MAP['TAILWIND_STYLE_COMPILATION'](os.path.abspath(folder))
        # FIXED: Replaced hardcoded string with dynamic TAILWIND_BINARY
        build_global_tailwind(os.environ.get('tailwind', TAILWIND_BINARY), os.path.join(folder, 'layouts'), css_file)

    style_dir = os.path.join(folder, 'layouts', 'styles')
    if args.stylepath:
        for obj in os.scandir(args.stylepath):
            shutil.copy(obj, os.path.join(style_dir, os.path.basename(obj)))
    else:
        stylepath_expected = os.path.join(pathlib.Path(path_of_xml).parent, 'styles')
        if os.path.isdir(stylepath_expected):
            for obj in os.scandir(stylepath_expected):
                shutil.copy(obj, os.path.join(style_dir, os.path.basename(obj)))
    
    window = load_layout(html_file, bin_file, True)
    th = threading.Thread(target=observer, args=(path_of_xml, bin_file, html_file, folder, css_file, paths_to_scan, settingsCustom,), daemon=True)
    th.start()

    webview.start(main_thread_loop, args=(window,))
    watcher_queue.put("STOP")
    reload_queue.put("STOP")
    th.join()
    
def main_thread_loop(window):
    while True:
        try:
            signal = reload_queue.get(timeout=0.1)
            if signal == "TRIGGER_RELOAD":
                print("[Main Thread] Safe reload signal received! Refreshing view...")
                window.evaluate_js('window.location.reload()')
            elif signal == "STOP":
                break
        except queue.Empty:
            continue

parser = argparse.ArgumentParser("Select mode of the build tool")
parser.add_argument("--hotreload", type=str, help="To hot reload some layout and show how compiled XML will look on PYUI.")
parser.add_argument("--keepontop", action='store_true', help="Used by hotreload and watch-reloading process.")
parser.add_argument("--compile", type=str, help="To compile project")
parser.add_argument("--compileexe", type=str, help="To compile project to executable")
parser.add_argument("--console", action='store_true', help="Tag if you want to show console in your built binary.")
parser.add_argument("--name", type=str, help="Name of your project binary")
parser.add_argument('--target', type=str, help='Target of build DEBUG or RELEASE')
parser.add_argument('--settings', type=str, help='Build settings file')
parser.add_argument('--tailwindpath', type=str, help='Path to tailwind binary.')
parser.add_argument('--run', action='store_true', help='To instantly execute project used with --compile')
parser.add_argument('--stylepath', type=str, help='Styles for hotreloading only.')

def remove_readonly(func, path, excinfo):
    # FIXED: Extended write permissions explicitly to work reliably on Linux environments
    os.chmod(path, stat.S_IWRITE | stat.S_IWUSR)
    func(path)

@atexit.register
def cleanup():
    try:
        if args.hotreload:
            print("Cleaning up cache files")
            err = False
            if os.path.isdir('temprun'):
                for obj in os.scandir('temprun'):
                    try:
                        shutil.rmtree(obj.path, onexc=remove_readonly)
                    except:
                        err = True
            if err:
                print("Can not delete all temprun cache files automatically.")
    except:
        pass

def sanitize_window_config(config: dict) -> dict:
    boolean_keys = {
        "resizable", "fullscreen", "hidden", "frameless", "easy_drag", 
        "shadow", "focus", "minimized", "maximized", "on_top", 
        "confirm_close", "transparent", "text_select", "zoomable", 
        "draggable", "vibrancy"
    }
    int_keys = {"width", "height", "x", "y"}
    injected = {"url", "js_api"}
    
    sanitized = config.copy()
    for key, value in sanitized.items():
        if value is None:
            continue
        if key in injected:
            continue
        if key in boolean_keys:
            if isinstance(value, str):
                sanitized[key] = value.strip().lower() in ("true", "1", "yes")
            else:
                sanitized[key] = bool(value)
        elif key in int_keys:
            try:
                sanitized[key] = int(value)
            except (ValueError, TypeError):
                pass
        elif key == "min_size":
            if isinstance(value, str):
                try:
                    parts = value.split(",")
                    sanitized[key] = (int(parts[0]), int(parts[1]))
                except (IndexError, ValueError):
                    sanitized[key] = (200, 100)
            elif isinstance(value, (list, tuple)):
                sanitized[key] = (int(value[0]), int(value[1]))
    return sanitized

def ImportCustomSettings(file_path):
    module_name = "PYUI.settings"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module: PYUI.settings = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

args = parser.parse_args()

if args.tailwindpath:
    os.environ['tailwind'] = args.tailwindpath

if args.hotreload != None:
    HandleHotReload()
elif args.compile != None:
    if args.settings == None:
        compilerconfig = None
        preexeccorountine = PYUI.settings.PreExecuteCoRountine()
        postexecutioncorountine = PYUI.settings.PostExecuteCoRoutine()
    else:
        settingsCustom = ImportCustomSettings(args.settings)
        compilerconfig = settingsCustom.CompilerSettings
        preexeccorountine: PYUI.settings.PreExecuteCoRountine = settingsCustom.PreExecuteCoRountine()
        postexecutioncorountine: PYUI.settings.PostExecuteCoRoutine = settingsCustom.PostExecuteCoRoutine()

    preexeccorountine.entry()
    # FIXED: Replaced fallback string with dynamic TAILWIND_BINARY
    path = build(args.compile, os.environ.get('tailwind', TAILWIND_BINARY), config=compilerconfig)
    postexecutioncorountine.entry()

    if args.run:
        cmd = [os.path.abspath(sys.executable), os.path.join(path, 'bootstrap.py')]
        print("Runing bootstrapper:", os.path.join(path, 'bootstrap.py'))
        subprocess.run(cmd, cwd=path)

elif args.compileexe != None:
    if args.settings == None:
        compilerconfig = None
        preexeccorountine = PYUI.settings.PreExecuteCoRountine()
        postexecutioncorountine = PYUI.settings.PostExecuteCoRoutine()
    else:
        settingsCustom = ImportCustomSettings(args.settings)
        compilerconfig: PYUI.settings.CompilerSettings = settingsCustom.CompilerSettings
        preexeccorountine: PYUI.settings.PreExecuteCoRountine = settingsCustom.PreExecuteCoRountine()
        postexecutioncorountine: PYUI.settings.PostExecuteCoRoutine = settingsCustom.PostExecuteCoRoutine()
    
    preexeccorountine.entry()
    # FIXED: Replaced fallback string with dynamic TAILWIND_BINARY
    build(args.compileexe, os.environ.get('tailwind', TAILWIND_BINARY), isexe=True, target=args.target, is_console=args.console, name=args.name, config=compilerconfig)
    postexecutioncorountine.entry()