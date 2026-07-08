'''
Script to build the executable for the program
'''
import os
import sys  # Added for cross-platform OS detection
import time
import colorama
import PYUI.compiler
import PYUI.converter
import shutil
import PYUI.tailwindBuilder
import subprocess
import PYUI.settings
from pathlib import Path
import stat
import pickle

# Fixed: Using cross-platform forward slashes. Python handles these smoothly on Windows too.
BUILD_FOLDERS = [
    'compiled_components', 
    'compiled_layouts', 
    'code', 
    'layouts', 
    'layouts/sources', 
    'layouts/styles', 
    'layouts/JS'
]

DEBUG_TYPE = {
    'error': colorama.Fore.RED,
    'warning': colorama.Fore.YELLOW,
    'success': colorama.Fore.GREEN,
    'info': colorama.Fore.CYAN
}

class TargetNotFoundError(Exception):
    pass

script_path = Path(__file__).resolve().parent

def resolve_path(path: str):
    return os.path.join(script_path, path)

def print_typed(msg, type='success', show_header=True):
    if show_header:
        print(DEBUG_TYPE[type] + f"[BUILD_SCRIPT]" + colorama.Fore.RESET, msg)
    else:
        print(msg)

def remove_readonly(func, path, excinfo):
    # Cross-platform permission reset
    os.chmod(path, stat.S_IWRITE | stat.S_IWUSR)
    func(path)

def build(PROJECT_DIR: str, TAILWIND_EXE: str, target=None, isexe=None, name=None, is_console=None, config: PYUI.settings.CompilerSettings = None):
    if config == None:
        config = PYUI.settings.CompilerSettings
        
    if not os.path.isdir(os.path.join(PROJECT_DIR, 'build')):
        print_typed('Build folder not found so making one', 'warning')
        os.mkdir(os.path.join(PROJECT_DIR, 'build'))
    else:
         item = 0
         for obj in os.scandir(os.path.join(PROJECT_DIR, 'build')):
              if os.path.basename(obj).startswith('temp_') and os.path.isdir(obj):
                   item += 1
        
         if config.ISSUE_TEMP_OVERCROWDING_LIMIT <= item:
              print_typed(f"Your build directory is too overcrowded and has {item} previous builds.", type='warning')
              val = input("Press (c) to clean them or enter to continue: ")

              if val.lower() == 'c':
                   for obj in os.scandir(os.path.join(PROJECT_DIR, 'build')):
                        if os.path.basename(obj).startswith('temp_') and os.path.isdir(obj):
                             try:
                                  shutil.rmtree(obj.path, onexc=remove_readonly)
                             except:
                                  print_typed(f"Failed to remove directory {obj.path}.", type='error')
              
    # Fixed: Removed hardcoded backslash out of path construction
    TEMP_FOLDER = os.path.abspath(os.path.join(PROJECT_DIR, 'build', 'temp_' + str(time.time())))

    print_typed(f'Build Folder:{TEMP_FOLDER} made.', 'info')
    os.mkdir(TEMP_FOLDER) 

    REQ_FOLDERS = {
        ".": TEMP_FOLDER
    }

    for folder in BUILD_FOLDERS:
        path = os.path.join(TEMP_FOLDER, folder)
        if not os.path.isdir(path):
            print_typed(f"   ->{path} made.", show_header=False)
            REQ_FOLDERS[folder] = path
            os.mkdir(path)

    print_typed('Build environment made successfully.')

    # =============================================
    # 2. Compile Layouts
    # =============================================
    LAYOUT_FOLDER = os.path.join(PROJECT_DIR, 'layouts')

    for f in os.scandir(LAYOUT_FOLDER):
        if not os.path.isdir(f):
            if os.path.basename(f).split('.')[-1].strip().lower() != "xml":
                continue
            
            if config.HOOK_MAP['COMPILATION']:
                config.HOOK_MAP['COMPILATION'](os.path.abspath(TEMP_FOLDER)) 

            print("==================================================================================")
            tree = PYUI.compiler.compile_layout(f, os.path.join(REQ_FOLDERS['compiled_layouts'], os.path.basename(f).replace('.xml', '') + '.bin'), PROJECT_DIR, TAG_RULES_HASHMAP=config.TAG_RULES_HASHMAP)
            print("-----------------------------------------------------------------------------------")
            
            if config.HOOK_MAP['CONVERTION']:
                config.HOOK_MAP['CONVERTION'](os.path.abspath(TEMP_FOLDER)) 

            PYUI.converter.save_html_file(tree, os.path.join(REQ_FOLDERS['layouts'], os.path.basename(f).replace('.xml', '') + '.html'), PROJECT_DIR, HTML_MAP=config.HTML_TAG_CONVERSION_MAP, LAYOUT_TAGS=config.LAYOUT_CONTAINER_TAGS)
            print_typed("Conversion done -> " + os.path.join(REQ_FOLDERS['layouts'], os.path.basename(f).replace('.xml', '') + '.html'))

    # =========================================
    # 3. Compile Components
    # =========================================
    COMPONENTS_FOLDER = os.path.join(PROJECT_DIR, 'layouts', 'components')
    for f in os.scandir(COMPONENTS_FOLDER):
            PYUI.compiler.compile_layout(f, os.path.join(REQ_FOLDERS['compiled_components'], os.path.basename(f).replace('.xml', '') + '.bin'), PROJECT_DIR, TAG_RULES_HASHMAP=config.TAG_RULES_HASHMAP, Component=True)

    SETTINGS_FILE = os.path.join(REQ_FOLDERS['.'], 'settings.bin')
    pickle.dump(config, open(SETTINGS_FILE, 'wb'))
    
    # =========================================
    # 4. Tailwind Build
    # =========================================
    if config.TAILWIND_ENABLED:
        print("==================================================================================")
        if config.HOOK_MAP['TAILWIND_STYLE_COMPILATION']:
                config.HOOK_MAP['TAILWIND_STYLE_COMPILATION'](os.path.abspath(TEMP_FOLDER)) 
        
        global_css = os.path.join(PROJECT_DIR, 'layouts', 'styles', 'global.css')
        html_dir = REQ_FOLDERS['layouts']

        print_typed(f"Directing Tailwind to scan: {html_dir}", 'info')
        tbuilder = PYUI.tailwindBuilder.build_global_tailwind(os.environ.get('tailwind', TAILWIND_EXE), html_dir, global_css, 'temp.css')
        if tbuilder:
            print_typed(f"Tailwind UI compiled to ->" + global_css)

    print("==================================================================================")
    
    # ==========================================
    # 5. Copy CSS files (Fixed Dictionary Keys)
    # ==========================================
    if config.HOOK_MAP['STYLE_COPY']:
                config.HOOK_MAP['STYLE_COPY'](os.path.abspath(TEMP_FOLDER)) 
    
    STYLE_FOLDER = os.path.join(PROJECT_DIR, 'layouts', 'styles')

    print_typed("Copying styles to -> layout/styles.", type='info')
    for f in os.scandir(STYLE_FOLDER):
        if not os.path.isdir(f):
            # Fixed key: 'layouts/styles' instead of 'layouts\\styles'
            dest_path = os.path.join(REQ_FOLDERS['layouts/styles'], os.path.basename(f))
            shutil.copy(f, dest_path)
            print_typed(f"   -> {os.path.basename(f)} copied.", show_header=False)

    print("==================================================================================")

    # =============================================
    # 6. Copy Package Files (Fixed Dictionary Keys)
    # ==============================================
    if config.HOOK_MAP['PACKAGE_COPY']:
                config.HOOK_MAP['PACKAGE_COPY'](os.path.abspath(TEMP_FOLDER)) 

    print_typed("Copying package files...", type='info')

    f = resolve_path("Package/bootstrap.py")
    shutil.copy(f, os.path.join(REQ_FOLDERS['.'], os.path.basename(f)))


    if config.HOOK_MAP['JS_COPY']:
                config.HOOK_MAP['JS_COPY'](os.path.abspath(TEMP_FOLDER)) 

    for f in os.scandir(resolve_path("JS")):
        if not os.path.isdir(f):
            # Fixed key: 'layouts/JS'
            dest_path = os.path.join(REQ_FOLDERS['layouts/JS'], os.path.basename(f))
            shutil.copy(f, dest_path)
            
    print_typed("All Package files transfer completed...")

    shutil.copy(resolve_path('PYUICommonExecutable.spec'), os.path.join(REQ_FOLDERS['.'], 'PYUICommonExecutable.spec'))
    print("==================================================================================")

    CUSTOM_JS_FOLDER = os.path.join(PROJECT_DIR, 'layouts', 'JS')
    # Fixed key: 'layouts/JS'
    print_typed("Copying custom JS files...", type='info')

    for f in os.scandir(CUSTOM_JS_FOLDER):
        if not os.path.isdir(f):
            dest_path = os.path.join(REQ_FOLDERS['layouts/JS'], os.path.basename(f))
            shutil.copy(f, dest_path)

    print("==================================================================================")

    if config.HOOK_MAP['CODE_COPY']:
                config.HOOK_MAP['CODE_COPY'](os.path.abspath(TEMP_FOLDER)) 

    print_typed("Copying code files to ->" + REQ_FOLDERS['code'])
    for f in os.scandir(os.path.join(PROJECT_DIR, 'code')):
         if not os.path.isdir(f):
            shutil.copy(f, os.path.join(REQ_FOLDERS['code'], os.path.basename(f)))
            
    print_typed("All Code files transfer completed...")
    print("==================================================================================")

    if isexe == None:
         print("The compiled project saved at -->", os.path.abspath(TEMP_FOLDER))
         return os.path.abspath(TEMP_FOLDER)

    # =================================================================
    # 7. For Building Executable (Dynamic OS Handling)
    # =================================================================
    if target == None:
        target = 'debug'
    
    if config.HOOK_MAP['BUILD_START']:
                config.HOOK_MAP['BUILD_START'](os.path.abspath(TEMP_FOLDER)) 
    
    if not target.lower().strip() in ['release', 'debug']:
        raise TargetNotFoundError(f"[BUILD ERROR] --> The target {target} does not exist.")

    target_path = os.path.abspath(os.path.join(PROJECT_DIR, target))

    if not os.path.exists(target_path):
        os.mkdir(target_path)

    if name == None:
        name = "PYUICommonExecutable"
        
    if is_console:
        os.environ['CONSOLE'] = '1'
    else:
        os.environ['CONSOLE'] = '0'
    
    os.environ['FOLDER'] = REQ_FOLDERS['.']
    os.environ['OUT'] = target_path
    os.environ['NAME'] = name
    
    script_args = [
        "pyinstaller",
        "PYUICommonExecutable.spec",
    ]   
    
    print_typed("RUNNING PYINSTALLER FOR EXECUTABLE CONVERSION")
    print("==================================================================================")
   
    process = subprocess.run(script_args, cwd=REQ_FOLDERS['.'], text=True)
    print("==================================================================================")

    # Fixed: Determine binary extension dynamically based on OS
    exe_ext = ".exe" if sys.platform == "win32" else ""
    generated_binary = os.path.join(TEMP_FOLDER, 'dist', f'{name}{exe_ext}')

    if process.returncode == 0 and os.path.exists(generated_binary):
        shutil.copy(
            src=generated_binary,
            dst=os.path.join(target_path, f'{name}{exe_ext}')
        )
        print_typed(f"Build Completed with no errors. Saved at: {target_path}")
    else:
        print_typed(msg='Error in building executable.', type='error')
        print("==================================================================================")
        print(process.stderr)