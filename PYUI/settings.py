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
    "vulkan-accelerated": set(),

    "main-content": {"default-active-window"},
    "window": {"id", "style-class"},

    "Text": {"id", "style-class", "innerText"},
    "Input": {"id", "style-class", "placeholder","type"},
    "Button": {"innerText", "style-class", "id"},
    "container": {"id", "style-class", "layout"},
    "br":(),
    "style":{"file","type"},
    "Component":{"file","name"},
    "ComponentFile":set(),
    "Para":{"id", "style-class", "layout", "padding","style-class"},
    
    # --- NEW MEDIA TAGS ---
    "img": {"id", "style-class", "src", "alt", "width", "height"},
    "video": {"id", "style-class", "src", "controls", "autoplay", "loop", "muted", "poster", "width", "height"},
    "audio": {"id", "style-class", "src", "controls", "autoplay", "loop", "muted"}

}
    # Strict lowercase match arrays to preserve structural boundaries
    LAYOUT_CONTAINER_TAGS = {"main-content", "window", "container", "pyui"}

    HTML_TAG_CONVERSION_MAP = {
    "main-content": "div",
    "window": "div",
    "container": "div",
    "text": "span",
    "button": "button",
    "input": "input",
    "br": "br",
    "Para":"p",
    # --- NEW MEDIA MAPPINGS ---
    "img": "img",
    "video": "video",
    "audio": "audio"
    }

    TAILWIND_ENABLED = False


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


