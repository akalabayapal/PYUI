'''
Script to create a PYUI project 
'''

import sys
import os
import colorama
import shutil
from pathlib import Path
import argparse


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


def create(folder:str):

    '''
    Function for handling Creating a project
    '''
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

def _makefile(file_path:str,file_name:str,path):


    code_path = os.path.abspath(file_path)

    if os.path.exists(file_path):

        condition = input(colorama.Fore.YELLOW+f'The layout file:{file_name} is already present do you want to replace it(R) or skip creation of file(S):'+colorama.Fore.RESET)

        if condition.lower() == 'r':
            shutil.copy(resolve_path(path), code_path)
            return True
        elif condition.lower() == 's':
            return True
        else:
            print_typed("Invalid option choosen",type='error')
            return False
    else:
        shutil.copy(resolve_path(path), code_path) # just copy
        return True

def _delfile(file_path):

    while True:

        try:
            os.remove(file_path)
            return True
        except Exception as ex:
            print_typed(f"Failed to remove file:{file_path}."
                        "   -> Reason:"+ex)
            i = input("Try again(n to no, pressing anything else will try again) ?")  
            if i.lower() == 'n':
                return False
    

def cf(uri:str):

    '''
    Function to handle creation of Form
    '''
    
    parsed = uri.split("@")

    folder = ''.join(parsed[:-1])
    name = parsed[-1]
    # check if the paths exists and create them at onces.. Even one of them is not present or is a duplicate raise error

    path_layout = os.path.join(folder,'layouts',name+'.xml')
    path_code = os.path.join(folder,'code',name+'.py')


    if not (os.path.isdir(os.path.join(folder,'layouts')) and os.path.isdir(os.path.join(folder,'code'))):
        print_typed('Can not make form.Most probably it is not a valid PYUI project folder.',type='error') 
        return
    
    
    if _makefile(path_layout,name+'.xml','boilerplate/index.xml'):
        print_typed('Layout file generated',type='success')

        if _makefile(path_code,name+'.py','boilerplate/index.py'):
            print_typed('Code file generated',type='success')
        else:
            print_typed('Code file generation failed',type='error')
    else:
        print_typed('Layout file generation failed',type='error')


    

def rf(uri:str):

    parsed = uri.split("@")

    folder = ''.join(parsed[:-1])
    name = parsed[-1]


    path_layout = os.path.join(folder,'layouts',name+'.xml')
    path_code = os.path.join(folder,'code',name+'.py')


    if not (os.path.exists(path_layout) and os.path.exists(path_code)):
        print_typed(f"The given uri {uri} is not a valid existing form uri.\n" 
                   f"    -> Make sure there is {folder}/{name}.xml and" 
                   f"    -> Make sure there is {folder}/{name}.py",type='error')
        return


    if _delfile(path_layout) and _delfile(path_code):

        print_typed("Form Deleted completed",type='success')

    else:
        print_typed("Sorry, can not remove the given form uri:",uri)

    

parser = argparse.ArgumentParser("Select mode of create tool")

parser.add_argument("--create", type=str, help="To create a new project.")
parser.add_argument("--cf", type=str, help="To add a new form to project directory.")
parser.add_argument("--rf", type=str, help="To remove form to project directory.")

args = parser.parse_args()

if args.create:

    # call create function
    create(args.create)

elif args.cf:

    #call create form function
    cf(args.cf)
elif args.rf:

    rf(args.rf)