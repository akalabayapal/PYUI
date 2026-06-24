'''
Script to build the executable for the program
'''
import os
import time
import colorama
import PYUI.compiler
import PYUI.converter
import shutil
import PYUI.tailwindBuilder
import subprocess
import PYUI.settings
from pathlib import Path

BUILD_FOLDERS = [
    'compiled_layouts', #bin compiled layouts for instant loading
    'code', #Contains the python codes.Bootstraper handles control over main.py via a thread. and pywebview runs in another thread
    'layouts', #pure html layouts for pywebview to load nameing of compiled_layout and layout must match for rendering to work
    'layouts\\sources', #contains media images,excess graphics needed to run the program.is accessed by the htmls
    'layouts\\styles', #styles needed for the html to run.
    'layouts\\JS' #contains the required runtime JS required for the internal framework working
]

DEBUG_TYPE = {
    'error':colorama.Fore.RED,
    'warning':colorama.Fore.YELLOW,
    'success':colorama.Fore.GREEN,
    'info':colorama.Fore.CYAN
}

class TargetNotFoundError(Exception):
    pass

# Absolute path of the current script
script_path = Path(__file__).resolve().parent

def resolve_path(path:str):
     return os.path.join(script_path,path)

# args = sys.argv[1:] #ignore the first argv reserved for the file itself in pythons

# PROJECT_DIR = args[0] #stores the project folder
# TAILWIND_EXE = "..\\tailwind\\tailwind.exe"

#============================================

#1.Make temporary build folders to make structure
#============================================



def print_typed(msg,type='success',show_header=True):
    if show_header:
        print(DEBUG_TYPE[type]+f"[BUILD_SCRIPT]"+colorama.Fore.RESET,msg)
    else:
        print(msg)

def build(PROJECT_DIR:str,TAILWIND_EXE:str,target=None,isexe=None,name=None,is_console=None,config:PYUI.settings.CompilerSettings=None):
    if config == None:
        config = PYUI.settings.CompilerSettings
        
    if not os.path.isdir(os.path.join(PROJECT_DIR,'build')):
        print_typed('Build folder not found so making one','warning')
        os.mkdir(os.path.join(PROJECT_DIR,'build'))


    TEMP_FOLDER = os.path.abspath(os.path.join(PROJECT_DIR,'build\\temp_'+str(time.time())))

    print_typed(f'Build Folder:{TEMP_FOLDER} made to build procedure to be initiated.','info')
    os.mkdir(TEMP_FOLDER) #make a folder to make the req files to run pyinstaller after it on the folder

    REQ_FOLDERS = {
        ".":TEMP_FOLDER
    }

    #make the required folders in it...
    for folder in BUILD_FOLDERS:
        path = os.path.join(TEMP_FOLDER,folder)
        if not os.path.isdir(path):
            #make it
            print_typed(f"   ->{path} made.",show_header=False)
            REQ_FOLDERS[folder] = path
            os.mkdir(path)


    print_typed('Build environment made sucessfully.')

    #=============================================
    #2.Compile all layouts from the ./layouts folder
    #=============================================

    LAYOUT_FOLDER = os.path.join(PROJECT_DIR,'layouts')

    for f in os.scandir(LAYOUT_FOLDER):

        if not os.path.isdir(f):
        
            if os.path.basename(f).split('.')[-1].strip().lower() != "xml":
                continue
            
            if config.HOOK_MAP['COMPILATION']:
                config.HOOK_MAP['COMPILATION'](os.path.abspath(TEMP_FOLDER)) #Call hook 

            print("==================================================================================")
            #compile the tree store it and retrive the object
            tree = PYUI.compiler.compile_layout(f,os.path.join(REQ_FOLDERS['compiled_layouts'],os.path.basename(f).replace('.xml','')+'.bin'),PROJECT_DIR,TAG_RULES_HASHMAP=config.TAG_RULES_HASHMAP)
            print("-----------------------------------------------------------------------------------")
            
            if config.HOOK_MAP['CONVERTION']:
                config.HOOK_MAP['CONVERTION'](os.path.abspath(TEMP_FOLDER)) #Call hook 


            #convert the xml to a proper html file
            PYUI.converter.save_html_file(tree,os.path.join(REQ_FOLDERS['layouts'],os.path.basename(f).replace('.xml','')+'.html'),PROJECT_DIR,HTML_MAP=config.HTML_TAG_CONVERSION_MAP,LAYOUT_TAGS=config.LAYOUT_CONTAINER_TAGS)
            print_typed("The convertion of xml->html done and layout saved to -> "+os.path.join(REQ_FOLDERS['layouts'],os.path.basename(f).replace('.xml','')+'.html'))


    # =========================================
    # 3. Compile the whole HTML folder into a single global.css file
    # =========================================
    if config.TAILWIND_ENABLED:
        print("==================================================================================")
        
        if config.HOOK_MAP['TAILWIND_STYLE_COMPILATION']:
                config.HOOK_MAP['TAILWIND_STYLE_COMPILATION'](os.path.abspath(TEMP_FOLDER)) #Call hook 
        
        
        # The single destination path for your styles
        global_css = os.path.join(PROJECT_DIR, 'layouts', 'styles', 'global.css')

        # PASS THE DIRECTORY ONLY - tailwindBuilder handles the internal @source scanning!
        html_dir = REQ_FOLDERS['layouts']

        print_typed(f"Directing Tailwind to scan entire folder hierarchy: {html_dir}",'info')
        tbuilder = PYUI.tailwindBuilder.build_global_tailwind(os.environ.get('tailwind',TAILWIND_EXE), html_dir, global_css, 'temp.css')
        if tbuilder:
            print_typed(f"Tailwind UI compiled to ->"+global_css)

    print("==================================================================================")
    #==========================================
    #4.Copy the css files to the styles folder
    #==========================================

    if config.HOOK_MAP['STYLE_COPY']:
                config.HOOK_MAP['STYLE_COPY'](os.path.abspath(TEMP_FOLDER)) #Call hook 
    

    STYLE_FOLDER = os.path.join(PROJECT_DIR,'layouts','styles')

    print_typed("Copying styles to -> layout/styles.",type='info')
    for f in os.scandir(STYLE_FOLDER):
        if not os.path.isdir(f):
            shutil.copy(f,os.path.join(REQ_FOLDERS['layouts\\styles'],os.path.basename(f)))
            print_typed("   ->"+os.path.basename(f)+" copied to "+os.path.join(REQ_FOLDERS['layouts\\styles'],os.path.basename(f)),show_header=False)

    print("==================================================================================")

    # =============================================
    # 5.Copy the Package files to the build directory
    # ==============================================

    if config.HOOK_MAP['PACKAGE_COPY']:
                config.HOOK_MAP['PACKAGE_COPY'](os.path.abspath(TEMP_FOLDER)) #Call hook 

    print_typed("Copying package files to ->"+REQ_FOLDERS['.'],type='info')

    f = resolve_path("Package/bootstrap.py")
    shutil.copy(f,os.path.join(REQ_FOLDERS['.'],os.path.basename(f)))
    print_typed("   ->"+os.path.basename(f)+" copied to "+os.path.join(REQ_FOLDERS['.'],os.path.basename(f)),show_header=False)


    if config.HOOK_MAP['JS_COPY']:
                config.HOOK_MAP['JS_COPY'](os.path.abspath(TEMP_FOLDER)) #Call hook 

    for f in os.scandir(resolve_path("JS")):
        if not os.path.isdir(f):
            shutil.copy(f,os.path.join(REQ_FOLDERS['layouts\\JS'],os.path.basename(f)))
            print_typed("   ->"+os.path.basename(f)+" copied to "+os.path.join(REQ_FOLDERS['layouts\\JS'],os.path.basename(f)),show_header=False)
    print_typed("All Package files transfer completed...")

    shutil.copy(resolve_path('PYUICommonExecutable.spec'),os.path.join(REQ_FOLDERS['.'],'PYUICommonExecutable.spec'))
    print("==================================================================================")


    CUSTOM_JS_FOLDER = os.path.join(PROJECT_DIR,'layouts','JS')
    print_typed("Copying custom JS files to ->"+os.path.join(REQ_FOLDERS['layouts\\JS']),type='info')

    for f in os.scandir(CUSTOM_JS_FOLDER):
        if not os.path.isdir(f):
            shutil.copy(f,os.path.join(REQ_FOLDERS['layouts\\JS'],os.path.basename(f)))
            print_typed("   ->"+os.path.basename(f)+" copied to "+os.path.join(REQ_FOLDERS['layouts\\JS'],os.path.basename(f)),show_header=False)

    print("==================================================================================")


    if config.HOOK_MAP['CODE_COPY']:
                config.HOOK_MAP['CODE_COPY'](os.path.abspath(TEMP_FOLDER)) #Call hook 

    print_typed("Copying code files to ->"+REQ_FOLDERS['code'])
    for f in os.scandir(os.path.join(PROJECT_DIR,'code')):
         if not os.path.isdir(f):
            shutil.copy(f,os.path.join(REQ_FOLDERS['code'],os.path.basename(f)))
            print_typed("   ->"+os.path.basename(f)+" copied to "+os.path.join(REQ_FOLDERS['code'],os.path.basename(f)),show_header=False)
    print_typed("All Code files transfer completed...")
    print("==================================================================================")

    if isexe == None:
         print("The compiled project saved at -->",os.path.abspath(TEMP_FOLDER))
         return os.path.abspath(TEMP_FOLDER)
    #=================================================================
    # For Building Exe
    #=================================================================

    #Check target and mkdir if folder do not exists
    if target == None:
        target = 'debug'
    
    if config.HOOK_MAP['BUILD_START']:
                config.HOOK_MAP['BUILD_START'](os.path.abspath(TEMP_FOLDER)) #Call hook 
    
    if not target.lower().strip() in ['release','debug']:
        raise TargetNotFoundError(f"[BUILD ERROR] --> The given target {target.lower().strip()} do not exist.")

    target_path = os.path.abspath(os.path.join(PROJECT_DIR,target))

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
        # f"--name={name}",
        "PYUICommonExecutable.spec",
        # "--onefile",
        # "--add-data", "code;code",
        # "--add-data", "compiled_layouts;compiled_layouts",
        # "--add-data", "layouts;layouts",
        # "bootstrap.py"
    ]   

    
    print_typed("RUNNING PYINSTALLER FOR EXECUTABLE CONVERSION")
    print("==================================================================================")
   
    process = subprocess.run(script_args,cwd=REQ_FOLDERS['.'],text=True)
    print("==================================================================================")

    if process.returncode == 0 and os.path.exists(os.path.join(TEMP_FOLDER,'dist',f'{name}.exe')):
        # Copy the executable to target_path

        shutil.copy(

            src = os.path.join(TEMP_FOLDER,'dist',f'{name}.exe'),
            dst=os.path.join(target_path,f'{name}.exe')
        )

        print_typed("Build Completed with no errors." \
        f"   --> Exe saved at:{target_path}")

    else:
        print_typed(msg='Error in building executable.'
                    'Error Log:',type='error')
        print("==================================================================================")
        print(process.stderr)

