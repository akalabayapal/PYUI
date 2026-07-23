![header img](assets/header-new.png)

This project is targeted to make cross platform applications using python.PYUI is a layout pre-compiled framework for making python applications in very lightweight sizes. It uses a xml layouting system for defining layouts, python for logic and **PYWebview** as the renderer.Leading to a blank application size only 16MB compared to heavyweight rendering systems costing 50+ MB or TKinter that has very legacy thread-unsafe architecture

**Note: Project is under rapid development and is in meta stable state. First stable release will be v1.0**

## Motivation
1.**Making General Purpose Applications:** This project is driven by the motivation of making a framework over python that can be used to make general purpose applications with little or no learning curve.

2.**Smaller learning curve:** Recent solutions for UI development mostly are hard to learn and manage. However we adopted age-old xml layouting system that makes defining UI easy for anyone with little xml/html knowledge. 

3.**Support of Python libraries and modules:** On the logic side python can be used to it's Limit, also the threadsafe nature of the framework helps in extreme scalability.

4.**Compiled Layout and Reusibility:** This framework has pre-compiled layouting system.So errors in layout are identified on runtime. Also Layout supports reusability using **PYUI Components**.

## Key Features of PYUI API

| Category | Features |
|----------|----------|
| **Layout System** | ✅ XML-based Layouts • ✅ Reusable Components • ✅ Multi-Form Applications • ✅ Resource Management |
| **DOM API** | ✅ Pythonic OOP API • ✅ Procedural API • ✅ Dynamic Style & Attribute Updates • ✅ Class Management |
| **Events** | ✅ Callback Registration • ✅ Callback Removal • ✅ Event Dispatching |
| **Dynamic UI** | ✅ Dynamic Component Addition • ✅ Component Removal • ✅ Runtime DOM Manipulation |
| **Development** | ✅ Hot Reload • ✅ Live UI Updates • ✅ `PYUI.manage` compilation, Executable compilation |
| **Performance** | ✅ DOM Batching • ✅ Pipelines • ✅ Hook System for High-Frequency Updates |
| **Communication** | ✅ Custom Syscalls • ✅ Secure HMAC Runtime Bridge • ✅ Python ↔ JavaScript Communication |
| **Compiler** | ✅ XML Compiler • ✅ Precompiled Binary Layouts (`.bin`) • ✅ Component Compiler • ✅ Fast Runtime Loading |
| **Platform Support** | ✅ Windows • ✅ Linux |

## Getting Started

PYUI has been tested on Windows(x64) and linux. However you can still use it in MacOS by building your own **PYUI** Package from source by compiling the `xmlparser.dylib` and puting it in dll folder.

### Installing PYUI (Windows)

1.Get the PYUI using 

    pip install pyui-desktop


### Installing PYUI (Linux)

Because this framework uses `pywebview` to render native GUI windows, it requires system-level GTK and WebKit libraries. 

Follow these steps to set up the system dependencies and install the framework cleanly without running into `externally-managed-environment` errors.

### Step 1: Install System GUI Dependencies
Open your terminal and run the command corresponding to your Linux distribution:

#### Ubuntu / Debian / Linux Mint / Pop!_OS
```bash
sudo apt update
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1
```
*(Note: If you are on an older version like Ubuntu 20.04, change `gir1.2-webkit2-4.1` to `gir1.2-webkit2-4.0`)*

#### Fedora / Red Hat
```bash
sudo dnf install python3-gobject gtk3 webkit2gtk4.1
```

#### Arch Linux
```bash
sudo pacman -S python-gobject gtk3 webkit2gtk-4.1
```

---

### Step 2: Set Up Your Virtual Environment
To keep your system clean, you must use a virtual environment. 

**CRITICAL:** You must pass the `--system-site-packages` flag so that Python can access the system GTK/WebKit graphics libraries you installed in Step 1. Without this flag, the installation will attempt to compile these libraries from source and fail.

```bash
# 1. Create the environment with system package access
python3 -m venv .venv --system-site-packages

# 2. Activate the virtual environment
source .venv/bin/activate
```

---

### Step 3: Install the Framework
Now that your environment is active and connected to your system's graphics engine, you can safely install the package:

```bash
pip install pyui-desktop
```


## Setting up project

    mkdir HelloWorldApp
    
    python -m PYUI.create --create HelloWorldApp

**Note:** Replace your app name with 'HelloWorldApp' as per your choice

This will generate boilerplate project. Following folder and files will be generated in the given folder(i.e HelloWorldApp or your app name).

    layouts
    code
    layouts/JS
    layouts/styles
    code/index.py
    code/__init__.py
    layouts/index.xml
    settings.py


## Compiling project

Go to the project directory

    cd HelloWorldApp 

**Note:** Replace your app name with 'HelloWorldApp' and go to that directory

To compile to a PYUI project and run it

    python -m PYUI.manage --compile ./ --run

This command will compile your project into a PYUI project and run it. Within few seconds(depending on project size) you can see your project load in a while.

**Note:** Use `python3` in place of `python` for linux systems for all commands present in this README.


![hello img](assets/hello.png)

To compile without running project

    python -m PYUI.manage --compile ./

It will save your project in *build/temp_xxxxx.yyyy* (see last line of buildscript output). To launch the project go to the directory and run:

    python bootstrap.py

It will launch your UI

To compile to a executable

    python -m PYUI.manage --compileexe ./ --name HelloWorldApp

This command will make a *debug* folder go to that folder and run *HelloWorldApp.exe*

**Note:** Replace the 'HelloWorldApp' with your desired App Name


## Changing Layouts

To change layouts open the *layouts/index.xml* and change the layout as per your needs.To start with a blank boilerplate, clear the content of the file and replace it with:

    <pyui>
        <metadata>
        <version>1.0.0</version>
        </metadata>
        <form-settings>
            <title>PyUI Portal - Hello World</title>
        </form-settings>
        <main-content default-active-window="boilerplateview">
            <window id="boilerplateview">
    
            </window>
        </main-content>
    </pyui>

[Refer to documentation for XML Tags](https://akalabayapal.github.io/PYUI-docs/PYUI%20XML%20LAYOUT%20GUIDE/important_tags/) for further references

**Note:** Documentation is yet not completed and is under development

## Component Re-use
Component can be re-used in `PYUI Xml`. The components are stored in `layouts/components` folder. 

### Component Writing
Open `layouts/component` folder and make a file `exampleComponent.xml` (Re-name as per convinience)

#### Boilerplate component:

    # File: layouts/components/example_component.xml

    <ComponentFile>
        <Text id="txt" innerText="Hello world"></Text>
    </ComponentFile>

    #File: layouts/index.xml (Can be any layout file index.xml is choosen as example)

    ....
    <Component file="exampleComponent.xml" name="component_name"></Component>

#### Component with property passing

Properties are essential for better component management

    # File: layouts/components/example_component.xml

    <ComponentFile  txt_component="Default text. This can be removed and is optional">
        <Text id="txt" innerText="{txt_component}"></Text>
    </ComponentFile>

    #File: layouts/index.xml (Can be any layout file index.xml is choosen as example)

    ....
    <Component file="exampleComponent.xml" name="component_name" txt_component="Passed property.If default is present this is optional."></Component>


**Note:** The component inner id's get renamed to exampleComponent_txt by compiler. While accessing it from `Python runtime` use

    from PYUI.Package.PYUI import cpath

    .....

    component_id =cpath('exampleComponent','txt') # <- cpath is a function from PYUI.Package.PYUI helps to write name mangling cleanly

    e = Element(component_id,self.pyui) # <- self.pyui is just the pyui instance

    .....

## Handling Logic using python

Open the *code/index.py* you will see

    from PYUI.Package.PYUI import PYUI,Element,Component,cpath

    '''
    Element: OOP facade over procedural PYUI
    Component: Add and remove dynamic components from UI
    cpath: helps is easy resolving component ids you need not write "component_id_element_id" better use cpath(component_id,    element_id)
    both are equivalent.
    '''

    class App:

        def __init__(self,obj:PYUI):

            '''
            Entry point of App class.
            Use this class to work with index.xml
            '''
            self.pyui = obj


    def entry(obj:PYUI):

        """
        This is the entry point for your form index.xml
        You can write procedural code using this entrypoint by deleting OOP function. Or use the boilerplate App class
        You can rename the Class to anything
        """
        App(obj) # executing the app class

`entry` is the entry point to your code for handling `layouts/index.xml`. It is recomended to use this OOP structure for better development. Hence the boilerplate is generated like this.

**Note:** You can remove the whole class and still work with only the `entry` function.


### Simple PYUI References


#### Get a element Instance

    e = Element('id',self.pyui)

1.Changing innertext for a component
    
    e.text = 'new_text'

Replace with the tag's id 

2.Getting a particular id's attribute

    val = e.attrib.attribute # This keep the attribute by reference, changing the variable `var` changes the attribute
    copy = str(e.attrib.attribute) # This keeps a copy of the attribute.You can typecast to the type of need

    hidden = bool(e.attrib.hidden) # Here hidden is a boolean hence we typecast to bool and store the copy

3.Setting a particular id's attribute

    e.attrib.attribute = value_of_attribute

    e.attrib.hidden = False # <- Hides the element completely (Example)

4.Set a new Style for a id

    e.style.style_attribute = 'new_style_value'

    e.style.color = 'red' 
    e.style.backgroundColor = 'blue' # <- Use camelCase for the properties with hypen in betweeen like background-color
    
5.Add or Remove a Class

    e.add_class('class_name')
    e.remove_class('class_name')
    e.toggle_class('class_name')


6.Register a callback to a id

    class App:

        def __init__(self,obj:PYUI):
            self.pyui = obj

            e = Element('btn_id') # <- get the element
            e.on('click',self.btn_callback,args=()) # <- Register callback .on(typeOfCallback,callback_function,args)
        
        def btn_callback(self,o,msg): # < - o and m are PYUI instance and callback msg(e.detail value from JS) 
            print("Clicked")


    def entry(obj:PYUI):

        ....
        App(obj)

**Note:** typeOfCallback is any valid callback supported by JS Dom like click,hover etc.

7.UnRegister a callback

    e.off("click") # <- unregister callback .off('typeofCallback')

8.End the form

    self.pyui.End() 

#### Dynamic attribute/style changing
Always the name of attribute or style you will change may not be known ahead of time. Use the functional approach to work

1. For getting a style

        e = Element('id')
        e.get_style('style-attribute') 

2. For setting style

        e.set_style('style-attribute','style-value')

3. For getting a attribute

        e.get_attribute('attribute-name')

4. For setting a attribute

        e.set_attribute('attribute-name','attribute-value')

#### Loading and adding components dynamically

    c = Component(self.pyui,'exampleComponent')
    
    id_of_comp_added = c.appendComponent('parent_id',c,**properties)

    id_of_comp_added = c.addComponentTop('parent_id',c,**properties)

    id_of_comp_added = c.addComponentAfter('preceeding-id',c,**properties)

#### Accessing a innercomponent element

    id_txt = cpath(id_of_comp_added,'element_id')
    e = Element(id_txt,self.pyui) # <- Now use this instance to work with

#### Removing component

    c.removeComponent(id_of_comp_added)

For further and more advanced features refer to our documentation.



## Making a new view/window

PYUI supports multiple view inside one form.To add a new view you need to add *window* tag with id inside *main-content* tag

    <main-content>
        <window id="window-1">
            ....
        </window>

        <window id="newly-added-window">
            ....
        </window>
    
    <main-content>


### Switching between views/Windows

You can dynamically switch between windows/views

    self.pyui.changeWindow('id-of-window-to-be-displayed')


## Creating a new form

Forms are isolated windows inside a single app.Each forms are process level isolated from one another.

To make a new form, go to your PYUI project root folder then,

    python -m PYUI.create --cf @new_form_name

It creates the boilerplate new form for the project

## Removing a form

To delete a form, go to your project root folder then,

    python -m PYUI.create --rf @delete_form_name



### Loading new forms dynamically

To load a form from python use:

    self.pyui.loadForm('newform')

**Note:** Replace 'newform' with your form name accordingly

### HotReloading Layouts

You can hot-reload the layout for faster UI development.

    python -m PYUI.manage --hotreload layouts/index.xml

**Note:** Replace with your file name

Changing the xml file will reload the UI automatically

If you are using styles from some folder that is not present in styles folder of the xml-file directory then

    python -m PYUI.manage --hotreload <layout-xml-file> --stylepath <custom-styles-folder>

**Note:** Use the *--keepontop* flag to keep the UI on top always


![hot reload image](assets/hotreload.png)   

## Examples
Figure out the examples folder to see real-world application implementation using `PYUI`




## Documentation

For further API references for XML and PYUI check the documentation.

Documentation: [PYUI Documentation](https://akalabayapal.github.io/PYUI-docs/)

**Note:** Documentation is yet not completed and is under development


## Changes and Contribution

Contribution in this project is open and highly welcomed.


## Credits

PyWebview: https://github.com/r0x0r/pywebview

