# =========================================================
# HTML ELEMENT TRANSPILATION SPECIFICATION MAP
# =========================================================
from PYUI.pyuinode import PyUILayoutNode
import os
import warnings

# Strict lowercase match arrays to preserve structural boundaries
LAYOUT_CONTAINER_TAGS_DEFAULT = {"main-content", "window", "container", "pyui","Datagrid","row","ComponentFile"}

HTML_TAG_CONVERSION_MAP_DEFAULT = {
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
    "audio": "audio",
    # --- DATA GRID --- #

    "Datagrid":"table",
    "row":"tr",
    "data":"th"

    }




def convert_node_to_html(node,view_window_active_id:str,HTML_TAG_CONVERSION_MAP:dict,LAYOUT_CONTAINER_TAGS:dict) -> str:
    if not node:
        return ""
    
    # CRITICAL: Always enforce lower-casing immediately at entry point
    tag_lower = node.tag.lower().strip()


    #IMPORTANT:No styles tag after main-content.if found it will trigger warning
    if tag_lower == "style":
        warnings.warn("Styles inside and below main-content are not evaluated.Please link them out of main content and 'above it'",SyntaxWarning)
    
    html_tag = HTML_TAG_CONVERSION_MAP.get(tag_lower, tag_lower)

    attr_parts = []
    inner_text = "" 
    
    element_id = getattr(node, 'id', None)
    if element_id:
        attr_parts.append(f'id="{element_id}"')

    # Process attributes smoothly
    for k, v in node.attributes().items():
        k_lower = k.lower().strip()
        
        if k_lower == "id":
            continue

        if k_lower == "innertext":
            inner_text = v
        elif k_lower == "style-class":
            attr_parts.append(f'class="{v}"')
        else:
            attr_parts.append(f'{k}="{v}"')

    if tag_lower == "window" and element_id != view_window_active_id:
        attr_parts.append('style="display:none;"')
            
    attr_str = " " + " ".join(attr_parts) if attr_parts else ""

    # CASE A: Leaf Widgets - Close immediately
    if tag_lower not in LAYOUT_CONTAINER_TAGS:
        return f"<{html_tag}{attr_str}>{inner_text}</{html_tag}>\n"

    # CASE B: Layout Containers - Process internal tree nodes explicitly before closing
    child_content = ""
    current_child = node.firstChild
    while current_child:
        child_content += convert_node_to_html(current_child,view_window_active_id=view_window_active_id,LAYOUT_CONTAINER_TAGS=LAYOUT_CONTAINER_TAGS,HTML_TAG_CONVERSION_MAP=HTML_TAG_CONVERSION_MAP)
        current_child = current_child.nextSibling

    # Children are now safely locked inside the parent tag container!
    return f"<{html_tag}{attr_str}>\n{child_content}</{html_tag}>\n"



def find_main_content_node(node:PyUILayoutNode,style_sheets:list):
    """Scans the compiled tree to locate the <main-content> entry point."""
    if not node:
        return None
    
    if node.tag.lower().strip() == "style":
        #get the file attribute
        style_sheets.append(node.get('file'))

    if node.tag.lower().strip() == "main-content":
        return node,node.get('default-active-window')
        
    current_child = node.firstChild
    while current_child:
        found = find_main_content_node(current_child,style_sheets)
        if found:
            return found 
        current_child = current_child.nextSibling
        
    return None

def herf_resolver(file_name,project_root_dir):
    f = os.path.join(project_root_dir,"layouts","styles",file_name)
    if not os.path.isfile(f):
        raise FileNotFoundError('Style-sheet:'+f+' does not exists.')

    return os.path.join("styles",file_name)

def generate_full_html_document(root_node,project_dir,base_name,HTML_MAP:dict=None,LAYOUT_TAGS:dict=None) -> str:
    STYLEHEETS = []
    """Isolates layout from metadata and generates the clean boilerplate webpage."""
    main_content_node,default_active_window = find_main_content_node(root_node,style_sheets=STYLEHEETS)
    

    body_content = convert_node_to_html(main_content_node if main_content_node else root_node,default_active_window,HTML_TAG_CONVERSION_MAP=HTML_MAP,LAYOUT_CONTAINER_TAGS=LAYOUT_TAGS)
    
    stylesheet_html = ""
    for sheet in STYLEHEETS:
        stylesheet_html += f"<link href=\"{herf_resolver(sheet,project_dir)}\" rel=\"stylesheet\">"

    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Application View</title>
    <link href="styles/global.css" rel="stylesheet">
    """+stylesheet_html+"""
    <script src='JS/handler.js'></script>
    <script src='JS/connection.js'></script>
    <script src='JS/"""+base_name.replace('html','')+"""js'></script>
    </head>
"""+body_content+"""
</html>
"""


def save_html_file(node: PyUILayoutNode, file_path: str,project_dir:str,HTML_MAP=None,LAYOUT_TAGS=None):
    if HTML_MAP == None:
        HTML_MAP = HTML_TAG_CONVERSION_MAP_DEFAULT
    if LAYOUT_TAGS == None:
        LAYOUT_TAGS = LAYOUT_CONTAINER_TAGS_DEFAULT
    html_content = generate_full_html_document(node,project_dir,os.path.basename(file_path),HTML_MAP=HTML_MAP,LAYOUT_TAGS=LAYOUT_TAGS)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)