#Class containing all the setting for an app


class CompilerSettings:

    TAG_RULES_HASHMAP = {
    "pyui": set(), 
    "metadata": set(),
    "version": set(),
    "form-settings": set(),
    "title": set(),
    "width": set(),
    "height": set(),
    "resizable": set(),
    "x":set(),
    "y":set(),
    "fullscreen":set(),
    "hidden":set(),
    "frameless":set(),
    "easy_drag":set(),
    "shadow":set(), # windows only feature
    "focus":set(), #default is true, false:non-focusable window
    "minimized":set(),
    "maximized":set(),
    "on_top":set(),
    "confirm_close":set(),
    "background_color":set(),
    "text_select":set(),



    "main-content": {"default-active-window"},
    "window": {"id", "style-class"},

    "Input": {"id", "style-class", "placeholder","type"},
    "Button": {"innerText", "style-class", "id"},
    "container": {"id", "style-class", "layout"},
    "br":(),
    "style":{"file","type"},
    "Component":{"file","name"},
    "ComponentFile":set(),
    
    "selector":{"id","style-class"},
    "option":{"id","style-class","value"},

    # --- TEXT TAGS ---
    "Text": {"id", "style-class", "innerText"},
    "Para":{"id", "style-class","innerText"},
    "h1":{"id", "style-class", "innerText"},
    "h2":{"id", "style-class", "innerText"},
    "h3":{"id", "style-class", "innerText"},
    "h4":{"id", "style-class", "innerText"},
    "label":{"id", "style-class", "innerText"},
    




    
    # --- NEW MEDIA TAGS ---
    "Img": {"id", "style-class", "src", "alt", "width", "height"},
    "Video": {"id", "style-class", "src", "controls", "autoplay", "loop", "muted", "poster", "width", "height"},
    "Audio": {"id", "style-class", "src", "controls", "autoplay", "loop", "muted"},

    # ---- DATA GRID -------- #
    "Datagrid":{"id","style-class"},
    "row":{"id","style-class"},
    "data":{"id","style-class","innerText"}

}
    # Strict lowercase match arrays to preserve structural boundaries
    LAYOUT_CONTAINER_TAGS = {"main-content", "window", "container", "pyui","Datagrid","row","ComponentFile","Selector"}

    HTML_TAG_CONVERSION_MAP = {
    "main-content": "div",
    "window": "div",
    "container": "div",
    "text": "span",
    "button": "button",
    "input": "input",
    "br": "br",
    "Para":"p",
    "selector":"select",
    "option":"option",

    # --- TEXT TAGS ---
    "h1":"h1",
    "h2":"h2",
    "h3":"h3",
    "h4":"h4",
    "label":"label",
    # --- NEW MEDIA MAPPINGS ---
    "img": "img",
    "video": "video",
    "audio": "audio",
    # --- DATA GRID --- #

    "Datagrid":"table",
    "row":"tr",
    "data":"th"

    }

    TAILWIND_ENABLED = False
    ISSUE_TEMP_OVERCROWDING_LIMIT = 10


    HOOK_MAP = {
    "COMPILATION":None,
    "CONVERTION":None,
    "TAILWIND_STYLE_COMPILATION":None,
    "STYLE_COPY":None,
    "PACKAGE_COPY":None,
    "JS_COPY":None,
    "CODE_COPY":None,
    "BUILD_START":None
    }

class PreExecuteCoRountine:
    def __init__(self):
        pass
    def entry(self):
        pass

class PostExecuteCoRoutine:
    def __init__(self):
        pass
    def entry(self):
        pass


