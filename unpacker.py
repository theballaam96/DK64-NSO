import sys
from pathlib import Path
import os
import shutil
import zipfile
import yaml
from tools.rpt_converter import convert_rpt_to_png
import re

def unpackZip(version, file):
    temp_dir = Path("temp")
    if temp_dir.exists() and temp_dir.is_dir():
        print(f"Wiping existing {temp_dir}/ directory for a clean slate...")
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(file, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    # Replacement Textures
    rpt_files = list(temp_dir.rglob("*.rpt"))
    if rpt_files:
        os.makedirs(f"bin/{version}/textures", exist_ok=True)
        print(f"Found {len(rpt_files)} .rpt file(s):")
        for file in rpt_files:
            convert_rpt_to_png(str(file.resolve()), None, f"bin/{version}/textures")
    # Other configs
    target_extensions = {".meta", ".cfg", ".pcb", ".nro", ".spv"}
    found_files = [
        file for file in temp_dir.rglob("*") 
        if file.suffix.lower() in target_extensions
    ]
    if found_files:
        for file in found_files:
            destination = f"bin/{version}/{file.name}"
            
            # Copy the file
            shutil.copy2(file, destination)
            print(f"Copied: {file.name}")
            print(f" -> From: {file.resolve()}")
            print(f" -> To:   {destination}\n")

def convert_match_to_hex(match):
    """
    Callback function for re.sub. 
    Extracts the matched digits, converts to hex, and retains uppercase if desired.
    """
    # match.group(2) captures just the digits inside the boundary patterns
    number = int(match.group(2))
    
    # hex(number) returns '0x...', .upper() makes it '0X...' if you prefer uppercase hex
    hex_value = hex(number).upper().replace("0X","0x")
    
    # Reconstruct the string using the surrounding characters captured in group(1) and group(3)
    return f"{match.group(1)}{hex_value}{match.group(3)}"

def convertLua(version, lua_file):
    yaml_file = Path(f"lua_configs/{version}.yaml")
    yaml_data = None
    if yaml_file.exists():
        with open(yaml_file, "r") as file:
            # yaml.safe_load converts YAML into a Python dictionary
            yaml_data = yaml.safe_load(file)
    lines = []
    with open(lua_file, "r") as fh:
        lines = fh.readlines()
        for index, line in enumerate(lines):
            # Symbol Replacement
            for sym in yaml_data.get("symbol_replacement", []):
                if sym["original"] in lines[index]:
                    # print(f"Found {sym['original']} in {line}")
                    lines[index] = lines[index].replace(sym["original"], "" if sym["new"] is None else sym["new"])
            
            for enum_data in yaml_data.get("enums"):
                for sym in enum_data.get("syms", []):
                    if f"{sym} == " in lines[index]:
                        value_table = {}
                        for entry in enum_data.get("table", []):
                            value_table[entry["value"]] = f"{enum_data['name']}.{entry['name'].upper()}"
                        pattern = rf"({re.escape(sym)}\s*==\s*)(\d+)"

                        def lookup_replacement(match):
                            prefix = match.group(1)
                            val_index = int(match.group(2))
                            
                            try:
                                replacement_value = value_table[val_index]
                                return f"{prefix}{replacement_value}"
                            except KeyError:
                                # Fallback if the index in the file is out of bounds
                                return match.group(0)
                        lines[index] = re.sub(pattern, lookup_replacement, lines[index])
                    if f"{sym} ~= " in lines[index]:
                        value_table = {}
                        for entry in enum_data.get("table", []):
                            value_table[entry["value"]] = f"{enum_data['name']}.{entry['name'].upper()}"
                        pattern = rf"({re.escape(sym)}\s*~=\s*)(\d+)"

                        def lookup_replacement(match):
                            prefix = match.group(1)
                            val_index = int(match.group(2))
                            
                            try:
                                replacement_value = value_table[val_index]
                                return f"{prefix}{replacement_value}"
                            except KeyError:
                                # Fallback if the index in the file is out of bounds
                                return match.group(0)
                        lines[index] = re.sub(pattern, lookup_replacement, lines[index])
                for func in enum_data.get("funcs", []):
                    if f"{func}(" in lines[index]:
                        value_table = {}
                        for entry in enum_data.get("table", []):
                            value_table[entry["value"]] = f"{enum_data['name']}.{entry['name'].upper()}"
                        pattern = rf"({re.escape(func)}\s*\(\s*)(\d+)"

                        def lookup_replacement(match):
                            prefix = match.group(1)
                            val_key = int(match.group(2))
                            
                            try:
                                replacement_value = value_table[val_key]
                                return f"{prefix}{replacement_value}"
                            except KeyError:
                                # Fallback if the index in the file is out of bounds
                                return match.group(0)
                        lines[index] = re.sub(pattern, lookup_replacement, lines[index])

            if yaml_data["convert_hex"]:
                lines[index] = re.sub(r"(\s|\()(\d+)(\s|\))", convert_match_to_hex, lines[index])
    # Parse for any var = var lines
    new_lines = []
    for index, line in enumerate(lines):
        if not re.match(r"^([a-zA-Z_]\w*)\s*=\s*\1$", line.strip()):
            new_lines.append(line)
    lines = new_lines.copy()
    # Parse for any if/elif/else line followed by an end on the next
    new_lines = []
    for index, line in enumerate(lines):
        stripped_line = line.strip()
        skip_line = False
        if stripped_line[:3] == "if " or stripped_line[:4] == "else" or stripped_line[:7] == "elseif ":
            if lines[index + 1].strip() == "end":
                skip_line = True
        if not skip_line:
            new_lines.append(line)
    lines = new_lines.copy()
    if yaml_data["enums"]:
        enum_lines = []
        for enum_data in yaml_data["enums"]:
            enum_lines.append(f"local {enum_data['name']} = " + "{\n")
            for enm_entry in enum_data["table"]:
                enum_lines.append(f"\t{enm_entry['name'].upper()} = {enm_entry['value']},\n")
            enum_lines.append("}\n")
        insert_line = yaml_data.get("enum_insert_line", 0)
        if insert_line == 0:
            lines = enum_lines + lines
        else:
            lines = lines[:insert_line] + enum_lines + lines[insert_line:]
    # Handle comments
    new_lines = []
    for line in lines:
        new_lines.append(line)
        comment_index = len(new_lines) - 1
        for cmt in yaml_data.get("comments", []):
            if cmt["find"] in line:
                if cmt["type"] == "post":
                    new_lines[comment_index] = new_lines[comment_index].replace("\n", f" -- {cmt['comment']}\n")
                elif cmt["type"] == "below":
                    stripped_line = new_lines[comment_index].strip()
                    pre_amble = new_lines[comment_index].split(stripped_line)[0]
                    space_count = len(pre_amble)
                    used_char = pre_amble[0]
                    mult = 1
                    if used_char == " ":
                        mult = 4
                        space_count /= 4
                    extra = cmt.get("extra_indent", 1)
                    space_count += extra
                    pre_amble = used_char * int(space_count * mult)
                    new_lines.append(f"{pre_amble}-- {cmt['comment']}\n")
                elif cmt["type"] == "above":
                    stripped_line = new_lines[comment_index].strip()
                    pre_amble = new_lines[comment_index].split(stripped_line)[0]
                    space_count = len(pre_amble)
                    used_char = pre_amble[0]
                    mult = 1
                    if used_char == " ":
                        mult = 4
                        space_count /= 4
                    extra = cmt.get("extra_indent", 0)
                    space_count += extra
                    pre_amble = used_char * int(space_count * mult)
                    new_lines = new_lines[:comment_index] + [f"{pre_amble}-- {cmt['comment']}\n"] + new_lines[comment_index:]
                    comment_index += 1
    lines = new_lines.copy()
    with open(f"bin/{version}/script.lua", "w") as fh:
        for line in lines:
            fh.write(line)

def unpack(version):
    paths = ("bin", "temp")
    for p in paths:
        if os.path.exists(p):
            shutil.rmtree(p)
        os.mkdir(p)
    input_dir = Path("input")
    output_dir = Path(f"bin/{version}")
    if output_dir.exists() and output_dir.is_dir():
        print(f"Wiping existing {output_dir}/ directory for a clean slate...")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    action_taken = False
    first_zip = next(input_dir.glob("*.zip"), None)
    if first_zip:
        unpackZip(version, first_zip)
        action_taken = True
    first_lua = next(input_dir.glob("*.lua"), None)
    if first_lua:
        convertLua(version, first_lua)
        action_taken = True
    if not action_taken:
        print("No .zip or .lua files found to take action on in the input/ directory")

valid_versions = ("v1")
def isValidVersion(v) -> bool:
    if v is None:
        return False
    return v in valid_versions

if __name__ == "__main__":
    version = None
    if len(sys.argv) > 1:
        version = sys.argv[1]
    if not isValidVersion(version):
        attempted_version = None
        while not isValidVersion(attempted_version):
            print("Enter the version of the data in your input/ directory (eg. \"v1\")")
            print("Options:")
            print("- v1: June 4th 2026")
            attempted_version = input("Version: ")
            if not isValidVersion(attempted_version):
                print("")
                print("-----------------")
                print("- Invalid Input -")
                print("-----------------")
                print("")
        version = attempted_version
    unpack(version)