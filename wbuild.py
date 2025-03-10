import re
import time
import html as ht
import sys
import os

scr_dir = os.path.dirname(os.path.abspath(__file__))

TYPES = [
    {
        "type": "section",
        "args": {
            "align":"justify",
            "bg": 1,
            "class": "",
            "notopmarg": False,
            "uid": "",
        }
    },
    {
        "type": "column",
        "args": {
            "align":"justify",
            "bg": 1,
            "class": "",
            "notopmarg": True,
            "uid": "",
        }
    },
    {
        "type": "header",
        "args": {
            "numbered": False,
            "label": "",
            "class": "",
            "notopmarg": False,
            "uid": "",
        }
    },
    {
        "type": "subheader",
        "args": {
            "label": "",
            "numbered": False,
            "class": "",
            "notopmarg": False,
            "uid": "",
        }
    },
    {
        "type": "subsubheader",
        "args": {
            "label": "",
            "numbered": False,
            "class": "",
            "notopmarg": False,
            "uid": "",
        }
    },
    {
        "type": "text",
        "args": {
            "align": "justify",
            "bg": 1,
            "class": "",
            "notopmarg": False,
            "uid": "",
        },
    },
    {
        "type": "code",
        "args": {
            "align": "left",
            "class": "",
            "notopmarg": False,
            "uid": "",
            "bg": 2
        }
    },
    {
        "type": "list",
        "args": {
            "orderall": False,
            "lvloffset": 4,
            "baseoffset": 2,
            "class": "",
            "notopmarg": False,
            "uid": "",
        }
    },
    {
        "type": "img",
        "args": {
            "src": "", # "/dir_path/image.png"
            "maxwidth": "100%", # css value
            "caption": "",
            "label": "",
            "italicize":True,
            "class":"",
            "notopmarg":False,
            "uid":"",
        }
    },
]
def build_doc_dict(txt: str) -> dict:
    global TYPES
    last_added_item = None
    parts = extract_top_level_tags(txt)
    doc = {
        "type":"section",
        "id":time.time_ns(),
        "args":{
            key: TYPES[0]["args"][key] for key in TYPES[0]["args"].keys()
        },
        "data":[],
    }

    for part in parts:
        if is_type_tag(part):
                # copy text into data
            tag = delete_leading_whitespace(part)
            last_added_item = process_tag(tag, doc, last_added_item)
        elif is_args(part):
            process_args(part, last_added_item)
        else:
            itm = process_data(part, doc, last_added_item)
            if not itm is None:
                last_added_item = itm

    return doc

def _style_html_from_argdict(argdict: dict) -> str:
    html = ""
    for key in argdict.keys():
        match key:
            case "align":
                html += f"text-align:{argdict[key]};"
            case "maxwidth":
                html += f"max-width:{argdict[key]};"
            case "notopmarg":
                if argdict[key]:
                    html += "margin-top: 0px;"
    return html

def _is_sec_or_col(part: dict) -> bool:
    return part["type"] == "section" or part["type"] == "column"

def _is_sec(part: dict) -> bool:
    return part["type"] == "section"

def _classes_from_argdict(part: dict) -> str:
    argdict = part["args"]
    bg = f"bg{argdict["bg"] if "bg" in argdict.keys() else 1}"
    col = ""
    if _is_sec_or_col(part):
        n_cols = len([_part for _part in part["data"] if _part["type"] == "column"])
        n_cols = n_cols if n_cols <= 3 else 3
        n_cols = n_cols if n_cols > 0 else 1
        col = f"columns{n_cols}"
    partclass = ""
    if part["type"] == "code":
        partclass = "code"
    return f"{bg} {col} {partclass} {argdict["class"]}"

def _html_from_header(header: dict, doc: dict) -> str:
    heading_size = len(re.findall(r"sub", header["type"])) + 1
    tag = f"h{heading_size}"
    html = f"<{tag} id='{header["id"]}'"
    styles = _style_html_from_argdict(header["args"])
    txt = header["args"]["label"]
    txt = escape_non_cmds(txt)
    txt = apply_text_cmds(txt, doc)

    if not _empty_or_ws_str(styles):
        html += f" style='{styles}'"
    return html + f">{txt}</{tag}>"

def _html_from_code(code: dict, mode="dark") -> str:
    datastr = code["data"]
    datastr = ht.escape(datastr).replace("\n", "<br>")
    html = f"<div class='{_classes_from_argdict(code)}' data-theme='{mode}'"
    html += f" id='{code["id"]}'>"
    html += f"<pre>{datastr}</pre></div>"
    return html

def _html_from_list(list_d: dict, doc: dict) -> str:
    dat = list_d["data"]
    # dat = escape_non_cmds(dat).replace("\n", "<br>")
    # dat = apply_text_cmds(dat, doc)
    html = f"<pre class='list {list_d["args"]["class"]}'>"

    n_levels = 3
    escaped_lvls = re.escape(str(n_levels))
    split_dat = re.split(r"(?:\n|\s?|^)(\*{1,"+escaped_lvls+r"}|#{1,"+escaped_lvls+r"}|-{1,"+escaped_lvls+r"})\)", dat)
    split_dat = [sd.strip() for sd in split_dat if sd.strip()]
    indicator = ""
    order_counter = [0,0,0] # count each level for numbering
    first_line = True
    for sd in split_dat:
        if re.match(r"^(\*{1,"+escaped_lvls+r"}|#{1,"+escaped_lvls+r"}|-{1,"+escaped_lvls+r"})$", sd):
            indicator = sd
        else:
            level = len(indicator)
            # prespace = " " * level * list_d["args"]["lvloffset"]
            prespace = " " * list_d["args"]["lvloffset"] * (level - 1) + list_d["args"]["baseoffset"] * " "

            symbol = "•" if indicator[0] == "*" else " "
            if indicator[0] == "#":
                symbol = ""
                for i in range(level):
                    if i == level - 1 and i < n_levels:
                        order_counter[i] += 1
                        # reset counter of higher levels
                        for j in range(i + 1, n_levels):
                            order_counter[j] = 0
                    symbol += f"{max(1,order_counter[i])}{"." if i < level - 1 else ""}"
            elif list_d["args"]["orderall"]:
                for i in range(level):
                    if i == level - 1 and i < n_levels:
                        order_counter[i] += 1
                        # reset counter of higher levels
                        for j in range(i + 1, n_levels):
                            order_counter[j] = 0
            presequence = prespace + symbol + " "
            presequence = ht.escape(presequence)
            sd = escape_non_cmds(sd)
            sd = apply_text_cmds(sd, doc)
            if not first_line:
                html += "<br>"
            else:
                first_line = False
            html += ht.escape(presequence) + sd
    html += "</pre>"
    return html


def _html_from_img(img: dict, doc: dict) -> str:
    styles = f" style='{_style_html_from_argdict(img["args"])}'"
    if styles == " style=''":
        styles = ""
    imghtml = f"<figure id='{img["id"]}' style='margin: 0;'>"
    imghtml += f"<img class='{_classes_from_argdict(img)}' src='{img["args"]["src"]}'{styles}>"
    captionhtml = ""
    caption = img["args"]["caption"]
    if caption != "":
        caption = escape_non_cmds(caption)
        caption = apply_text_cmds(caption, doc)
        captionhtml = (f"<figcaption style='margin-top: -1%'>"
            +f"{"<i>" if img["args"]["italicize"] else ""}{caption}"
            +f"{"</i>" if img["args"]["italicize"] else ""}</figcaption>")
    captionhtml += "</figure>"
    return imghtml + captionhtml

def _html_from_text(part: dict, doc: dict) -> str:
    datastr = part["data"]
    datastr = escape_non_cmds(datastr).replace("\n","<br>")
    datastr = apply_text_cmds(datastr, doc)
    return f"<p class='{part["args"]["class"]}' id='{part["id"]}'>" + datastr + "</p>"

def _empty_or_ws_str(string: str) -> bool:
    return re.match(r"^\s?$", string)

def _html_from_container(section: dict, mode="dark", doc:dict=None) -> str:
    """
        args:
            - section: dictionary for a section or column object
    """
    if doc is None:
        doc = section

    html = f"<div id='{section["id"]}' "
    cols = [part for part in section["data"] if _is_sec(part)]
    html += f"class='{_classes_from_argdict(section)}'"
    html += f" data-theme='{mode}'"
    styles = _style_html_from_argdict(section["args"])
    if not _empty_or_ws_str(styles):
        html += f" style='{styles}' "
    html += ">"
    for part in section["data"]:
        match part["type"]:
            case "section" | "column":
                html += _html_from_container(part, mode, doc)
            case "header" | "subheader" | "subsubheader":
                html += _html_from_header(part, doc)
            case "text":
                html += _html_from_text(part, doc)
            case "code":
                html += _html_from_code(part, mode)
            case "img":
                html += _html_from_img(part, doc)
            case "list":
                html += _html_from_list(part, doc)
    html += "</div>"
    return html

def _get_html_theme_button(mode: str):
    icon = f"./assets/moon.png"
    if mode == "dark":
        icon = f"./assets/sun.png"
    html = "<button class='theme-btn' onclick='switchTheme()'>"
    html += f"<img src='{icon}' alt='Toggle theme'></button>"
    return html


def _get_js_imports():
    return f"<script src='./js/toggle_theme.js'></script>"

def html_from_dict(section: dict, mode="dark") -> str:
    """
        args:
            - section: dictionary for a section or column object
    """
    html = "<!DOCTYPE html><html><head>"
    style_path = os.path.abspath(os.path.join(scr_dir, "base_styles.css"))
    html += "<style>" + open(f"{style_path}").read() + "</style>"
    html += "</head>"
    html += f"<body class='bg1' data-theme='{mode}'x>"
    html += _html_from_container(section, mode)
    html += _get_html_theme_button(mode)
    html += _get_js_imports()
    html += "</body></html>"
    return html

def create_doc_item(tag: str, data: str="") -> dict:
    global TYPES
    t_idx = [item["type"] for item in TYPES].index(tag)
    type_info = TYPES[t_idx]
    if type_info["type"] == "section" or type_info["type"] == "column":
        data = []
    # if type(data) == str:
    #     data = escape(data)
    item_dict = {
        "type": type_info["type"],
        "id": time.time_ns(),
        "args": {arg:type_info["args"][arg] for arg in type_info["args"]},
        "data": data,
    }
    return item_dict

def process_tag(tagstr: str, doc: dict, last_added_item: dict | None) -> dict:
    global TYPES
    tag = tagstr[1:-1]
    item_dict = create_doc_item(tag)
    # if _is_sec(item_dict) and not last_added_item is None:
    #     # attach to parent of previously added, if it's a section we start a new one
    #     _, last_added_item = search_section(doc, last_added_item["id"])
    add_to_doc(item_dict, doc, last_added_item)
    # doc["data"].append(item_dict)
    return item_dict

def process_args(argstr: str, last_added_item: dict) -> None:
    global TYPES
    if last_added_item is None:
        raise TypeError(f"Last added item is none, but trying to add args {argstr}")
    # alter last item in doc dict with new args
    argdict = parse_args(argstr)
    for arg, argval in argdict.items():
        t_idx = [item["type"] for item in TYPES].index(last_added_item["type"])
        type_info = TYPES[t_idx]
        if arg in type_info["args"].keys():
            val = argval
            valtype = type(type_info["args"][arg])
            if valtype == int:
                val = int(argval)
            elif valtype == float:
                val = float(argval)
            elif valtype == bool:
                val = bool(argval)
            elif valtype == str:
                val = val.strip()
            last_added_item["args"][arg] = val

def search_uid(section: dict, uid: str) -> tuple | None:
    """
        section can be section or document
    """
    if section["args"]["uid"] == uid:
        return section, None
    for part in section["data"]:
        if part["args"]["uid"] == uid:
            return part, section
        elif _is_sec_or_col(part):
            in_part = search_uid(part, uid)
            if not in_part is None:
                return in_part
    return None

def search_section(section: dict, ident: int) -> tuple | None:
    if section["id"] == ident:
        return (section, None)
    for part in section["data"]:
        if part["id"] == ident: 
            return (part, section)
        elif _is_sec_or_col(part):
            in_sec = search_section(part, ident)
            if not in_sec is None:
                return in_sec
    return None

def add_to_doc(itemdesc: dict, doc: dict, last_added: dict | None) -> None:
    if last_added is None:
        doc["data"].append(itemdesc)
        return

    res = search_section(doc, last_added["id"])
    if res is None:
        raise ValueError(f"Object with id {last_added["id"]} not found")
    _, parent = res
    if _is_sec(itemdesc):
        # if new item is section, append new section to doc
        doc["data"].append(itemdesc)
        return
    elif _is_sec_or_col(itemdesc):
        # last_added can either be a section, column or other
        # if new item is column, 
        if _is_sec(last_added): # if last_added is a section: add to last_added
            last_added["data"].append(itemdesc)
        elif _is_sec_or_col(last_added): # if last_added is a column: add to parent
            parent["data"].append(itemdesc)
        else: # if last_added is an item:
            if _is_sec(parent): # if parent is section: add to parent
                parent["data"].append(itemdesc)
            else: # if parent is a column: add to parent of col
                _, newparent = search_section(doc, parent["id"])
                newparent["data"].append(itemdesc)
        return
    if _is_sec(last_added):
        last_added["data"].append(itemdesc)
    elif _is_sec_or_col(last_added):
        last_added["data"].append(itemdesc)
        # _, _parent = search_section(doc, last_added["id"])
    else:
        parent["data"].append(itemdesc)

def process_data(datastr: str, doc: dict, last_added_item: dict) -> dict | None:
    """
        Returns: created text dict or None
    """
    if (not last_added_item is None 
        and last_added_item["type"] in ["code", "list"] 
        and last_added_item["data"] == ""):
        datastr = datastr[1:-1].strip()
        last_added_item["data"] = datastr
        return None
    else:
        if ((not last_added_item is None) and last_added_item["type"] == "text"
            and last_added_item["data"] == ""):
            last_added_item["data"] = datastr
            return last_added_item
        else:
            created = create_doc_item("text", datastr)
            add_to_doc(created, doc, last_added_item)
            return created

def apply_text_cmds(text: str, doc: dict) -> str:
    commands = extract_text_cmds(text)
    if len(commands) == 0:
        return text
    for cdict in commands:
        match cdict["cmd"]:
            case "link":
                link = cdict["arg1"]
                if len(link) == 0:
                    raise ValueError(f"Empty link: {cdict}")
                if link[0] == "#":
                    sres = search_uid(doc, link[1:])
                    if sres is None:
                        raise ValueError(f"Can't find doclink: {link}")
                    linkdest, _ = sres
                    link = f"#{linkdest["id"]}"
                text = text.replace(cdict["string"], 
                    f"<a class='link' href='{link}'"+
                    f"{f" target='_blank'" if link[0] != "#" else ""}"+
                    f">{cdict["arg2"] if not cdict["arg2"] in ["", None] else link}"+
                    "</a>")
            case "bold":
                text = text.replace(cdict["string"],
                    f"<strong>{cdict["arg1"]}</strong>")
            case "italic":
                text = text.replace(cdict["string"],
                    f"<i>{cdict["arg1"]}</i>")
            case "textcode":
                text = text.replace(cdict["string"],
                    "<span class='textcode' style='display:inline'>"+
                    f"{cdict["arg1"] if (not cdict["arg1"] in ["", None]) else (cdict["arg2"] 
                        if not cdict["arg2"] in ["", None] else "")}</span>")
            case "showarg":
                uid = cdict["arg1"]
                argname = cdict["arg2"]
                res = search_uid(doc, uid)
                if res is None:
                    raise ValueError(f"uid not found: {uid}")
                if not argname in res[0]["args"].keys():
                    raise ValueError(f"Argument {argname} not in {res[0]["type"]} (uid {uid})")
                repl_txt = res[0]["args"][argname]
                # repl_txt = escape_non_cmds(repl_txt)
                # repl_txt = apply_text_cmds(repl_txt, doc)
                if argname == "label":
                    repl_txt = f"<a class='link' href='#{res[0]["id"]}'>{repl_txt}</a>"
                text = text.replace(cdict["string"],
                    repl_txt)
    return text

def restore_command(match):
    command = match.group(1)
    arg1 = ht.unescape(match.group(2) or "")
    arg2 = ht.unescape(match.group(3) or "")
    
    if arg2:
        return f"\\{command}{{{ht.escape(arg1)}}}{{{ht.escape(arg2)}}}"
    else:
        return f"\\{command}{{{ht.escape(arg1)}}}"
        
def escape_non_cmds(text: str) -> str:
    pattern = r"\\(\w+)(?:\{([^{}]*)\})?(?:\{([^{}]*)\})?"
    escaped_text = ht.escape(text)

    return re.sub(pattern, restore_command, escaped_text)

def delete_leading_whitespace(tag: str):
    pattern = r"\n\s*"
    return re.sub(pattern, "", tag)

def is_type_tag(text: str) -> bool:
    global TYPES
    tagptn = r"^\[[a-zA-Z0-9]+\]$"
    match = re.match(tagptn, text)
    if match is None:
        return False
    nows = re.sub(r"\s", "", match.string)
    return nows[1:-1] in [item["type"] for item in TYPES]

def is_args(text: str) -> bool:
    argptn = r'^\[\s*([\w-]+=[^\[\],]+)(?:\s*,\s*([\w-]+=[^\[\],]+))*\s*\]$'
    return re.match(argptn, text)

def parse_args(text: str) -> dict | None:
    pattern = r'(\w+)=([^,\]]+)'
    matches = re.findall(pattern, text)

    result = {key: value for key, value in matches}
    return result

def format_whitespaces(text: str) -> str:
    open_bracks = 0
    escape = False
    esc_idx = 0
    indices_to_rm = [] # tuples (min, max excluded)
    whitespace_streak = 0
    for c_idx, char in enumerate(text):
        if char == "\\" and not escape:
            escape = True
            esc_idx = c_idx

        if not escape and char == "[":
            open_bracks += 1
            if open_bracks == 1 and whitespace_streak > 0 and c_idx > 0:
                idx_range = (esc_idx, c_idx)
                indices_to_rm.append(idx_range)

        if not escape and char == "]":
            open_bracks = max(0, open_bracks - 1)

        if re.match(r"\s", str(char)):
            if whitespace_streak == 0:
                esc_idx = c_idx
            whitespace_streak += 1
        else:
            # non whitespace
            if (char in "[]" and escape) or not char in "[]":
                if (whitespace_streak > 0 and text[esc_idx - 1] in "[]" 
                    and text[esc_idx - 2] != "\\") and open_bracks == 0:
                    indices_to_rm.append((esc_idx, c_idx))
            whitespace_streak = 0

        if esc_idx == c_idx - 1:
            escape = False
    for idx_range in reversed(indices_to_rm):
        text = text[:idx_range[0]] + text[idx_range[1]:]
    return text

def rm_empties(strarrs: list) -> list:
    return [string for string in strarrs if not re.match(r'^\s?$', string)]


def extract_top_level_tags(text):
    """
    Extracts all top-level tags from the input text while preserving text and nested structures.
    A "top-level tag" is a tag that is not nested inside another.
    Ignores tags inside curly braces {}.
    """
    result = []
    buffer = ""
    tag_stack = []
    curly_stack = []
    tag_id = 0
    text = format_whitespaces(text)
    length = len(text)

    while tag_id < length:
        char = text[tag_id]
        # Handle escaped brackets (e.g., \[ or \])
        if char == "\\" and tag_id + 1 < length and text[tag_id + 1] in "[]{}":
            buffer += text[tag_id + 1]  # Add the escaped character
            tag_id += 2
            continue
        if char == "{":
            curly_stack.append(tag_id)
            buffer += char
        elif char == "}":
            if curly_stack:
                curly_stack.pop()
                buffer += char
        # Detect an opening bracket for a new tag, but only if NOT inside {}
        elif char == "[" and not curly_stack:
            if not tag_stack:  # If no open tags, flush buffer to results
                if buffer.strip(): 
                    result.append(buffer.strip())
                buffer = ""

            tag_stack.append(tag_id)
            buffer += char
        # Detect a closing bracket, possibly ending a top-level tag, but only if NOT inside {}
        elif char == "]" and not curly_stack:
            if tag_stack:
                buffer += char
                tag_stack.pop()
                if not tag_stack:
                    result.append(buffer.strip())
                    buffer = ""
        else:
            buffer += char
        tag_id += 1
    if buffer.strip():
        result.append(buffer.strip())

    result = rm_empties(result)
    return result

def extract_text_cmds(text):
    """
        Captures commands in the form
             *backslash*keyword{arg1}{arg2},
        where arg1 and arg2 are optional based on the keyword.
        Nested braches are disallowed, but escaped ones are ignored.

        Keywords:
         link{url}{text: optional}
         bold{text}
         italic{text}
         textcode{text}
         showargs{uid}{argname}

        Returns a list of dicts with keys:
            - cmd: The command keyword.
            - arg1: The first argument.
            - arg2: The second argument.
            - string: The matched substring.
    """
    commands = []
    pattern = r"\\(\w+)"
    i = 0
    length = len(text)

    while i < length:
        match = re.search(pattern, text[i:])
        if not match:
            break

        cmd_start = i + match.start()
        cmd_end = i + match.end()
        cmd = match.group(1)

        # Check that the match is not part of \word{arg}{arg}
        before_match = text[:cmd_start].rstrip()
        after_match = text[cmd_end:].lstrip()

        if (
            (re.search(r"\\\w+\{$", before_match)  # Check if it's preceded by \word{ (without escape)
            or re.search(r"\\\w+\{[^{}]*\}\{$", before_match))  # Check if it's part of \word{ignored}{ 
            and after_match.startswith("}")):
            i = cmd_end
            continue

        i = cmd_end

        args = []
        while i < length and text[i] == '{':  # Process arguments
            arg_start = i + 1
            arg_end = arg_start
            depth = 1

            while arg_end < length and depth > 0:
                if text[arg_end] == "{" and (arg_end == 0 or text[arg_end - 1] != "\\"):
                    depth += 1
                elif text[arg_end] == "}" and (arg_end == 0 or text[arg_end - 1] != "\\"):
                    depth -= 1
                arg_end += 1

            if depth == 0:
                arg = text[arg_start:arg_end - 1]  # Exclude outer braces
                arg = arg.replace(r"\{", "{").replace(r"\}", "}")  # Unescape braces
                args.append(arg)
                i = arg_end  # Move past the closing brace

        orig_text = text[cmd_start:i]  # Extract the full matched command

        # Ensure that if there's only one argument but it's a full command, it stays in arg1
        if len(args) == 1 and args[0].startswith("\\"):
            args.append(None)  # Ensure arg2 is None

        # Add extracted command to results
        commands.append({
            "cmd": cmd,
            "arg1": args[0] if len(args) > 0 else None,
            "arg2": args[1] if len(args) > 1 else None,
            "string": orig_text
        })
    return commands

if __name__ == "__main__":
    path_to_file = f"{scr_dir}/syntax.txt"
    save_path = f"{scr_dir}/output.html"
    mode = "light"
    view_built_site = False
    if len(sys.argv) > 1:
        path_to_file = sys.argv[1]
    if len(sys.argv) > 2:
        save_path = sys.argv[2]
        for i in range(3, len(sys.argv)):
            if sys.argv[i].lower() in ["-light", "-dark"]:
                mode = sys.argv[i][1:]
            elif sys.argv[i].lower() == "-view":
                view_built_site = True

    sample_txt = open(path_to_file, "r").read()
    save_to = open(save_path, "w")
    doc = build_doc_dict(sample_txt)
    print(doc)
    # for part in doc["data"]:
    html = html_from_dict(doc, mode=mode)
    save_to.write(html)
    if view_built_site:
        os.system(f"open '{save_path}'")