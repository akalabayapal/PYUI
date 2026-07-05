import os
import ctypes
import pickle
import colorama
from PYUI.pyuinode import PyUILayoutNode
from pathlib import Path


# Absolute path of the current script
script_path = Path(__file__).resolve().parent

# Add this directory to the safe DLL search path (Windows only)
if os.name == 'nt':
    os.add_dll_directory(str(script_path))

# =========================================================
# 1. C-TYPES STRUCT MAPPING (Volatile C Memory Layout)
# =========================================================
class DOMNodeStruct(ctypes.Structure):
    pass

DOMNodeStruct._fields_ = [
    ("tag", ctypes.c_char_p),
    ("attrcount", ctypes.c_int),
    ("attrKey", ctypes.POINTER(ctypes.c_char_p)),
    ("attrVal", ctypes.POINTER(ctypes.c_char_p)),
    ("innerText", ctypes.c_char_p),
    ("isLeaf", ctypes.c_bool),
    ("isRoot", ctypes.c_bool),
    ("firstChild", ctypes.POINTER(DOMNodeStruct)),
    ("nextSibling", ctypes.POINTER(DOMNodeStruct))
]

# Load DLL
dll_path = os.path.abspath(os.path.join(script_path,"dll/xmlparser.dll"))
c_engine = ctypes.CDLL(dll_path)
c_engine.parse_xml_to_tree.argtypes = [ctypes.c_char_p]
c_engine.parse_xml_to_tree.restype = ctypes.POINTER(DOMNodeStruct)
c_engine.free_c_tree.argtypes = [ctypes.POINTER(DOMNodeStruct)]


# =========================================================
# 2. STRICTOR TAG VALIDATION RULE HASHMAP
# =========================================================
TAG_RULES_HASHMAP_DEFAULT = {
    "pyui": set(), 
    "metadata": set(),
    "version": set(),
    "form-settings": set(),
    "title": set(),
    "width": set(),
    "height": set(),
    "resizable": set(),


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
    "Para":{"id", "style-class", "layout", "padding","innerText"},
    
    # --- NEW MEDIA TAGS ---
    "Img": {"id", "style-class", "src", "alt", "width", "height"},
    "Video": {"id", "style-class", "src", "controls", "autoplay", "loop", "muted", "poster", "width", "height"},
    "Audio": {"id", "style-class", "src", "controls", "autoplay", "loop", "muted"},

    # ---- DATA GRID -------- #
    "Datagrid":{"id","style-class"},
    "row":{"id","style-class"},
    "data":{"id","style-class","innerText"}

}

CACHE_COMPONENTS = {}

class IMPORT_STATE:
    processing = 1
    done_processing = 2

class CircularDependcencyError(Exception):
    pass

# =========================================================
# 3. PURE PYTHON SERIALIZABLE NODE STRUCT
# =========================================================

#=========================================================
#Resolve any file and return a c_node_ptr
#=========================================================
def handleComponentandReturnCptr(in_file):
    # 1. Process text mutations
    clean_xml = preprocessor(in_file)
    
    # 2. Drop into custom C-Parser DLL space
    c_root_ptr = c_engine.parse_xml_to_tree(clean_xml.encode('utf-8'))
    if not c_root_ptr:
        raise RuntimeError(f"C Compilation Core rejected layout file:{in_file} parsing.")
    
    return c_root_ptr


class InvalidPropError(Exception):
    pass

#================================================
#handle the props sent via file
#================================================
def processParams(v:str,props:dict):
    if not '{' in v:
        return v #no need to process params without props
    
    iscurlyStarted = False
    iscurlyEnded = False
    buffer = ""
    key = ""
    for n,char in enumerate(v+" "):
        if char == '{':
            if  n == 0:
                iscurlyStarted = True
            elif v[n-1] == "/":

                buffer += char
            elif iscurlyStarted == True:
                #it is just something inside {} just add to buffer
                key += char
            
            elif iscurlyEnded == True and iscurlyStarted == True:
                buffer += char
            else:
                 iscurlyStarted = True


        elif char == "}":

            if n == 0:
                buffer += char
            elif v[n-1] == "/":
                if iscurlyStarted == True:

                    key  += char
                    
                else:
                    buffer += char
     
            elif iscurlyStarted == True:

                iscurlyStarted = False
                iscurlyEnded = False

                try:
                    buffer += props[key.strip()]
                except KeyError:
                    raise InvalidPropError(f'The prop:{key} is used but not explicitly defined in parent layout file add {key}="some_value" to fix it.')
                key = ""
                
        elif char == "/" and (v[n+1] == "{" or v[n+1] == "}"):
            continue
        else:
            if iscurlyStarted == True and iscurlyEnded == False:
                key += char
            else:
                buffer += char

    return buffer.strip()


    


        
# =========================================================
# 4. THE COMPILER BAKE & INDEX PASS
# =========================================================
def bake_strict_c_tree_to_python(c_node_ptr,id_windows, id_index_map: dict,project_dir:str,mangling="",processProps={},isbuildscript=False,temp_cache={},TAG_RULES_HASHMAP={}) -> PyUILayoutNode:
    
    '''
    c_node_ptr: C Xml parser node pointer
    id_windows: Id of the windiws
    project_dir: Searches for the relative paths like components JS css from this path
    mangling: Used inside the components
    processprops: The props for components

    isbuildscript --> True --> uses the temp_cache important for the HotReload for cache storing only inside one build cycle
    |
    ----------------> False --> uses the global cache for the components storage/cache
    
    '''
    
    
    if not c_node_ptr:
        return None
    
    c_node = c_node_ptr.contents
    tag = c_node.tag.decode('utf-8').strip() if c_node.tag else ""
    
    
    # 1. Catch illegal tags via your active guardrail
    if tag not in TAG_RULES_HASHMAP:
        raise SyntaxError(f"[Compiler Error] Illegal/unregistered tag structure found: <{tag}>")
        
    allowed_attributes = TAG_RULES_HASHMAP[tag]


    # 2. Extract inner text safely
    raw_inner_text = c_node.innerText.decode('utf-8').strip() if c_node.innerText else ""
    if raw_inner_text.strip() in ["TEXT", "<TEXT>"]:
        raw_inner_text = ""

    

    #3. If the tag is form setting we need to capture them separately and store them out of bin file into small settings key in dict

    py_node = PyUILayoutNode(tag, raw_inner_text)

    isResolveInclude = False

    if tag == "Component":
    
        file = None
        name = None

        # 5. Pull attributes securely for include
        for i in range(c_node.attrcount):
            k:str = c_node.attrKey[i].decode('utf-8').strip()
            v = c_node.attrVal[i].decode('utf-8').strip()
        
            if mangling != '':
                v = processParams(v,processProps)
            if k == "file":
                f = os.path.join(project_dir,'layouts','components',v)
                if os.path.exists(f):
                    file = f
                else:
                    raise FileNotFoundError(
                        f"[Compiler Error] Include file can not be found!\n"
                        f"-> Given include:{f} can not be resolved correctly."
                        )
            elif k == "name":
                    name = v
    
            processProps[k] = v #for parsing 
        
        if file == None:
            Warning("[Compiler Include Warning] Can not resolve include without file tag.")
        if name == None or name.strip() == "":
            raise SyntaxError("[Compiler Include Error] name tag not found/empty in include.\n" \
            "-> It is advised to use name for proper id separation between components and to stop id collisions")

        mangling = name
       

        if isbuildscript:
            if file in temp_cache:
                component_c_ptr,import_state = temp_cache[file]
                if import_state == IMPORT_STATE.processing:
                    raise CircularDependcencyError(
                 f"[Compiler Error] Circular Dependency Detected!\n"
                f"-> Given include:{file} can not be resolved correctly.As it may trigger a infinite circular import."
            )
                temp_cache[file][1] = IMPORT_STATE.processing #Change to processing tag
              

            else:

                component_c_ptr = handleComponentandReturnCptr(file)
                temp_cache[file] = [component_c_ptr,IMPORT_STATE.processing]
           
        else:
            if (not file in CACHE_COMPONENTS):
                # Pull the C root pointer of the sub-component
                component_c_ptr = handleComponentandReturnCptr(file)
                CACHE_COMPONENTS[file] = [component_c_ptr,IMPORT_STATE.processing]
                

            else:
                component_c_ptr,import_state = CACHE_COMPONENTS[file]
                if import_state == IMPORT_STATE.processing:
                    raise CircularDependcencyError(
                 f"[Compiler Error] Circular Dependency Detected!\n"
                f"-> Given include:{file} can not be resolved correctly.As it may trigger a infinite circular import."
            )
                CACHE_COMPONENTS[file][1] = IMPORT_STATE.processing #Change to processing tag
    

        tag_inner = component_c_ptr.contents.firstChild.contents.tag.decode('utf-8').strip() if c_node.tag else ""

        #check if inital tag is Contents enforcing it is useful else throw error
        if tag_inner != "ComponentFile":
            raise SyntaxError(
                 f"[Compiler Error] Include file must be wrapped inside ComponentFile tag!\n"
                f"-> Given include:{f} can not be resolved correctly."
            )
        
        # Step into the component file's root payload
        real_component_root = component_c_ptr.contents.firstChild.contents.firstChild
        
        # Process and return the sub-tree directly, passing name as mangling prefix
        # This replaces the <Component> tag with the actual inner nodes seamlessly
        baked_component_tree = bake_strict_c_tree_to_python(real_component_root, id_windows, id_index_map, project_dir, mangling=name,processProps=processProps,isbuildscript=isbuildscript,temp_cache=temp_cache,TAG_RULES_HASHMAP=TAG_RULES_HASHMAP)

        # 2. Grab the sibling that was waiting AFTER the <Component> tag in the parent container
        sibling_ptr = c_node.nextSibling
        if sibling_ptr and sibling_ptr.contents.tag and sibling_ptr.contents.tag.decode('utf-8') in ["TEXT", "<TEXT>"]:
            sibling_ptr = sibling_ptr.contents.nextSibling

        # 3. If a sibling exists, traverse to the end of the new component tree and stitch it on
        if sibling_ptr and baked_component_tree:
            # Crawl to the absolute right-most sibling of the newly injected sub-tree
            last_sibling = baked_component_tree
            while last_sibling.nextSibling:
                last_sibling = last_sibling.nextSibling
            
            # Stitch the parent's remaining layout tags right onto the end of the component chain
            last_sibling.nextSibling = bake_strict_c_tree_to_python(sibling_ptr, id_windows, id_index_map, project_dir, mangling=name,processProps=processProps,isbuildscript=isbuildscript,temp_cache=temp_cache,TAG_RULES_HASHMAP=TAG_RULES_HASHMAP)

        #Change the cache back to done processing back to normal
        if isbuildscript:
            temp_cache[file][1] = IMPORT_STATE.done_processing
        else:
            CACHE_COMPONENTS[file][1] = IMPORT_STATE.done_processing

        return baked_component_tree
        
    

    #Pull attributes securely
    for i in range(c_node.attrcount):
        k:str = c_node.attrKey[i].decode('utf-8').strip()
        v = c_node.attrVal[i].decode('utf-8').strip()

        if mangling.strip() != "":
            v = processParams(v,processProps)

        if k not in allowed_attributes:
            raise ValueError(
                f"[Compiler Error] Critical parameter boundary violation!\n"
                f"-> Tag Primitive <{tag}> contains unauthorized/excess attribute definition: '{k}'"
            )
        if k == "id":
            if mangling.strip() != "":
                v = mangling+"_"+v

            py_node.id = v
            if v:
                if v in id_index_map:
                    raise RuntimeError(f"[Compiler Error] Duplicate ID detected: '{v}'")
                id_index_map[v] = py_node
                if tag == "window":
                    id_windows.append(v)
        elif k.strip() == "style-class":
            py_node.style_class = v

            for style_class in v.split(" "):
                 py_node.style_class_arr[style_class] = True

        py_node._attributes[k] = v

        
    # =========================================================
    # FIX: STEP OVER INTERNAL LEAF MARKERS LOCALLY
    # =========================================================
    # Check if the child node points to an unneeded internal text block marker
    child_ptr = c_node.firstChild
  
   
    if child_ptr and child_ptr.contents.tag and child_ptr.contents.tag.decode('utf-8') in ["TEXT", "<TEXT>"]:
        child_ptr = child_ptr.contents.nextSibling # Skip it safely!

    # Check if the sibling node points to an unneeded internal text block marker
    sibling_ptr = c_node.nextSibling
    if sibling_ptr and sibling_ptr.contents.tag and sibling_ptr.contents.tag.decode('utf-8') in ["TEXT", "<TEXT>"]:
        sibling_ptr = sibling_ptr.contents.nextSibling # Skip it safely!

    # 4. Process safe recursive layout pointers
    if child_ptr:
        py_node.firstChild = bake_strict_c_tree_to_python(child_ptr,id_windows, id_index_map,project_dir,mangling=mangling,isbuildscript=isbuildscript,temp_cache=temp_cache,TAG_RULES_HASHMAP=TAG_RULES_HASHMAP)
        
    if sibling_ptr:
        py_node.nextSibling = bake_strict_c_tree_to_python(sibling_ptr,id_windows, id_index_map,project_dir,mangling=mangling,isbuildscript=isbuildscript,temp_cache=temp_cache,TAG_RULES_HASHMAP=TAG_RULES_HASHMAP)
        
    return py_node



def process_settings_node(node:PyUILayoutNode,settings:dict):
  
    current_child:PyUILayoutNode = node.firstChild
    while current_child:
        settings[current_child.tag] = current_child.innerText
        current_child = current_child.nextSibling
 
    
def find_form_settings_content_node(node:PyUILayoutNode,settings):
    """Scans the compiled tree to locate the <form-settings> entry point."""
    if not node:
        return None
    
    
    if node.tag.lower().strip() == "form-settings":
        process_settings_node(node,settings)
    
        
    current_child = node.firstChild
    while current_child:
        found = find_form_settings_content_node(current_child,settings)
        current_child = current_child.nextSibling
        


# =========================================================
# 5. UNIFIED BUILD PIPELINE
# =========================================================
def preprocessor(in_file: str) -> str:
    """Cleans up formatting issues, spaces, and formatting ticks before parsing."""
    if not os.path.exists(in_file):
        raise FileNotFoundError(f'DEBUG: Layout configuration file {in_file} is missing.')

    with open(in_file, 'r', encoding='utf-8') as f:
        raw_xml = f.read()
        
    # Strip layout lines to structural data
    clean_xml = "".join(line.strip() for line in raw_xml.splitlines())
    return clean_xml

def compile_layout(in_file: str, out_file: str,PROJECT_DIR:str,isBuildSript=False,TAG_RULES_HASHMAP=None):
    """Executes preprocessor passes, processes tree layouts, and saves verified bytecode."""
    print(colorama.Fore.GREEN+"[PyUI Master Compiler]"+colorama.Fore.RESET+" Running build pipeline...")
    
    
    c_root_ptr = handleComponentandReturnCptr(in_file)

    # Initialize the fast-lookup map container to track IDs globally
    id_index_map = {}
    #store the form settings in another dictionary for runtime access without traversal
    settings = {}
    id_windows = []
    try:
        # Step over the C parser's internal <ROOT> node to target your real <pyui> data element container
        real_user_root = c_root_ptr.contents.firstChild
        temp_cache = {}

        if TAG_RULES_HASHMAP == None:
            TAG_RULES_HASHMAP = TAG_RULES_HASHMAP_DEFAULT
        # 3. Bake and audit tree parameters via Python state checking rules, passing our index map pointer
        if isBuildSript:
            baked_tree = bake_strict_c_tree_to_python(real_user_root,id_windows, id_index_map,PROJECT_DIR,isbuildscript=isBuildSript,temp_cache=temp_cache,TAG_RULES_HASHMAP=TAG_RULES_HASHMAP)

        else:
            baked_tree = bake_strict_c_tree_to_python(real_user_root,id_windows, id_index_map,PROJECT_DIR,isbuildscript=isBuildSript,TAG_RULES_HASHMAP=TAG_RULES_HASHMAP)

        find_form_settings_content_node(baked_tree,settings=settings)

        
        # Combine layout tree, flat identity map and form settings inside the unified binary distribution package
        distribution_bundle = {
            "layout_tree": baked_tree,
            "id_index_map": id_index_map,
            "form_settings":settings,
            "id_windows":id_windows
        }

        # 4. Serialize out perfectly validated application byte representation
        with open(out_file, 'wb') as f:
            pickle.dump(distribution_bundle, f, protocol=pickle.HIGHEST_PROTOCOL)
            
        print(colorama.Fore.GREEN+"[Success]"+colorama.Fore.RESET+f" Pure layout bytecode + ID Hashmap packed smoothly -> {out_file}")

        print(f" -> Number of indexed components Indexed Components: {len(list(id_index_map.keys()))}")
        if isBuildSript:
            cache = list(temp_cache.keys())
            return baked_tree,cache
        else:
            return baked_tree
        
        
    finally:
        # 5. Safely clean up unmanaged volatile heap components
        c_engine.free_c_tree(c_root_ptr)
    

