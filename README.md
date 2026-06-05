# DK64-NSO
Metadata unpacker, texture converter and script notater for the Nintendo Switch Online release of Donkey Kong 64. This repository does nto distribute any of the scripts or assets used for the operation of Donkey Kong 64 for Nintendo Switch Online. This is purely for research purposes

## How to operate
1. Install the requirements
```
pip install -r requirements.txt
```

2. Create an `input/` directory inside the repository root and place your metadata zip pack and decompiled script `.lua` file. If you only have one of these, the script will only perform the operations it can do.

3. Run `unpacker.py`. It will prompt you to input the version of your NSO data so that it can correctly transform your provided assets. Alternatively, you can supply the version as an arg to the python call

## Configuration Properties Reference

This document outlines the operational configurations, global variable mapping aliases, contextual enumerations (`enums`), and automated inline commenting systems defined in the configuration schema.

### Core Configuration Keys

| Property | Type | Description |
| :--- | :--- | :--- |
| `convert_hex` | `Boolean` | When enabled (`true`), all numbers in the lua file are changed to their hexadecimal representation. |
| `enum_insert_line` | `Integer` | Dictates the exact line index (Line `5`) inside the targeted output source file where generated enumeration structures should be injected. |

---

### Global Symbol Mappings (`symbol_replacement`)

These rules represent mapping the default variable names and some decompilation artifacts into more readable source code.

| Property | Type | Description |
| :--- | :--- | :--- |
| `original` | `String` | The original text to search for in a line. |
| `new` | `String` | The value that the original text should be replaced with. |

Note that the conversion of these variable names is done in line order, then for each line, it is ran in the order provided in the yaml. Therefore, any valid substrings of other replaced variable names should come after all entries it's a substring of.

---

### Game Engine Enumerations (`enums`)

Allows you to provide some enums for various values inside the lua script, making easier to read source code for those who don't want to memorize what gamemode 10 is. 

| Property | Type | Description |
| :--- | :--- | :--- |
| `name` | `String` | The name of the enum as a whole. This will be featured in the lua code. |
| `syms` | `Array of strings` | The variables that are associated with this enum. The unpacker will check for any equivalence or non-equivalence statements relative to the variable, and convert the number into it's more human readable form. |
| `funcs` | `Array of strings` | The function calls where the first argument is a member of the enum. Like syms, the unpacker will convert the first argument of any of those function calls to the appropriate enum member. |
| `table` | `Array of Objects` | The mapping table from enum member name to member value. |

---

### Static Code Insertion Triggers (`comments`)

When the unpacker has finished with most of the morphing process for the lua script, it will parse the comments object of your yaml for any comments it needs to add. The system it operates on is a line by line basis. To attach a comment, you must state a substring of a line which is unique enough to only place the comments relative to the desired line(s).

| Property | Type | Description |
| :--- | :--- | :--- |
| `find` | `String` | The substring you are wanting to search for in your script. |
| `comment` | `String` | The comment you wish to add. |
| `type` | `Strings` | The placement of the comment, one of `post`, `above` or `below`. |
| `extra_indent` | `Integer` | The extra indent of the comment that needs to be applied. Only valid for above/below comments. If missing from a comment entry, it will default to 0 for `above` comments, and 1 for `below` comments. |