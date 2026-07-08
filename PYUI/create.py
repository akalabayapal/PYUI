'''
Script to create a PYUI project 
'''

import sys
import os
import colorama
import shutil
from pathlib import Path

DEBUG_TYPE = {
    'error': colorama.Fore.RED,
    'warning': colorama.Fore.YELLOW,
    'success': colorama.Fore.GREEN,
    'info': colorama.Fore.CYAN
}

script_path = Path(__file__).resolve().parent

def resolve_path(path: str):
     return os.path.join(script_path, path)

def print_typed(msg, type='success', show_header=True):
    if show_header:
        print(DEBUG_TYPE[type] + f"[PYUI]" + colorama.Fore.RESET, msg)
    else:
        print(msg)

if len(sys.argv) > 1:
    folder = sys.argv[1]
else:
    print_typed("Please give a valid folder.", type='error')
    exit(-1)

# FIXED: Added missing (folder) evaluation so it properly checks if it is a directory
if not os.path.exists(folder) or not os.path.isdir(folder):
    print_typed('Can not make project given path do not exists or is not a directory.', type='error')
    exit(-1)

folder_to_make = [
    'code',
    'layouts',
    'layouts/styles',
    'layouts/JS',
    'layouts/components',
]

for f in folder_to_make:
    path = os.path.abspath(os.path.join(folder, f))

    if not os.path.exists(path):
        os.mkdir(path)
print_typed("Project Folder Structure Generation Done")

print("==================================================================================")
print_typed("Boilerplate Template is generated \n" \
"   -> code/index.py \n" \
"   -> layouts/styles/index.css \n" \
"   -> layouts/index.xml")
print("==================================================================================")

code_path = os.path.abspath(os.path.join(folder, 'code', 'index.py'))
shutil.copyfile(resolve_path('boilerplate/index.py'), code_path)

pkg_path = os.path.abspath(os.path.join(folder, 'code', '__init__.py'))

with open(pkg_path, 'w') as handle:
    handle.write("# Please do not remove this file. Your Projects entrypoint is index.py")

style_path = os.path.abspath(os.path.join(folder, 'layouts', 'styles', 'index.css'))
shutil.copyfile(resolve_path('boilerplate/index.css'), style_path)

xml_path = os.path.abspath(os.path.join(folder, 'layouts', 'index.xml'))
shutil.copyfile(resolve_path('boilerplate/index.xml'), xml_path)

config_path = os.path.abspath(os.path.join(folder, 'settings.py'))
shutil.copyfile(resolve_path('settings.py'), config_path)

print_typed("Generation of settings completed")
print("==================================================================================")
print_typed("Environment Generated at:" + folder)
print("==================================================================================")