from enum import IntEnum, auto
import zlib

def readFile(file_data,start,end):
	return int.from_bytes(file_data[start:end],"big")

def readFileSigned(file_data,start):
	val = int.from_bytes(file_data[start:start+2],"big")
	if val > 0x7FFF:
		val = val - 0x10000
	return val

def analyzeFile(data, folder_name, file_index):
	header_info = []
	base_info = []
	cutscene_info = []
	point_info = []
	info_l = 0x30
	read_l = 0
	for x in range(0x18):
		header_info_count = readFile(data,read_l,read_l+2)
		if (header_info_count > 0):
			for y in range(header_info_count):
				info = {
					"unk0": readFile(data,info_l,info_l+2),
				}
				header_info.append(info)
				info_l += 0x12
		read_l += 2
		#print(header_info_count)
	base_count = readFile(data,info_l,info_l+2)
	info_l += 2
	if base_count > 0:
		for x in range(base_count):
			info = {
				"x": readFile(data,info_l+0x10,info_l+0x12),
				"y": readFile(data,info_l+0x12,info_l+0x14),
				"z": readFile(data,info_l+0x14,info_l+0x16),
			}
			base_info.append(info)
			info_l += 0x1C
	cutscene_count = readFile(data,info_l,info_l+2)
	info_l += 2
	#print(f"Cutscene Count: {cutscene_count}")
	if cutscene_count > 0:
		for x in range(cutscene_count):
			subcount = readFile(data,info_l,info_l+0x2)
			info_l += 2
			master_a = []
			master_b = []
			if subcount > 0:
				for y in range(subcount):
					master_a.append(readFile(data,info_l,info_l+2))
					master_b.append(readFile(data,info_l+2,info_l+4))
					info_l += 4
			master = {
				"index": x,
				"count":subcount,
				"point_sequence": master_a,
				"point_durations": master_b,
			}
			cutscene_info.append(master)
	cutscene_point_count = readFile(data,info_l,info_l+2)
	#print(f"Point Count: {cutscene_point_count}")
	count_copy = cutscene_point_count
	info_l += 2
	repeat = 0
	unk0_list = []
	seg_idx = 0
	while count_copy != 0:
		command = readFile(data,info_l+1,info_l+2)
		unk0_item = readFile(data,info_l,info_l+1)
		if unk0_item not in unk0_list:
			unk0_list.append(unk0_item)
		info = {
			"unk0": unk0_item,
			"command": command,
			"segment": seg_idx
		}
		seg_idx += 1
		orig = count_copy
		count_copy -= 1
		if command == 1:
			info["read"] = data[info_l+4:info_l+10]
			info_l += 10
		elif command == 2:
			info["read"] = data[info_l+4:info_l+12]
			info_l += 12
		elif command == 3 or command == 13:
			info["read"] = data[info_l+4:info_l+16]
			info_l += 16
		elif command == 4:
			read_lst = []
			point_lst = []
			unk_count = readFile(data,info_l+4,info_l+6)
			info_l += 0x20
			for y in range(unk_count):
				read_lst.append(data[info_l:info_l+0xE])
				point_item = {
					"x": readFileSigned(data,info_l),
					"y": readFileSigned(data,info_l+2),
					"z": readFileSigned(data,info_l+4),
					"rot":{
						"x1":readFile(data,info_l+6,info_l+7),
						"y1":readFile(data,info_l+8,info_l+9),
						"x2":readFile(data,info_l+10,info_l+11),
					},
					"zoom":readFile(data,info_l+12,info_l+13),
					"roll":readFile(data,info_l+13,info_l+14),
					"unk":[
						hex(readFile(data,info_l+7,info_l+8)),
						hex(readFile(data,info_l+9,info_l+10)),
						hex(readFile(data,info_l+11,info_l+12)),
					]
				}
				point_lst.append(point_item)
				info_l += 0xE
			info["read"] = read_lst
			info["points"] = point_lst
		elif command == 5:
			read_lst = []
			point_lst = []
			unk_count = readFile(data,info_l+4,info_l+6)
			info_l += 0x14
			for y in range(unk_count):
				read_lst.append(data[info_l:info_l+0x8])
				point_item = {
					"x": readFileSigned(data,info_l),
					"y": readFileSigned(data,info_l+2),
					"z": readFileSigned(data,info_l+4),
					"zoom": readFile(data,info_l+6,info_l+7),
					"roll": readFile(data,info_l+7,info_l+8),
				}
				point_lst.append(point_item)
				info_l += 0x8
			info["read"] = read_lst
			info["points"] = point_lst
		elif command == 10 or command == 15 or command == 16:
			info["read"] = data[info_l+4:info_l+18]
			info_l += 18
		elif command == 12:
			info["read"] = data[info_l+4:info_l+6]
			info_l += 6
		else:
			count_copy += 1
			info_l += 4
		point_info.append(info)
	for point in point_info:
		command = point["command"]
		if command == 10 or command == 15 or command == 16 or command == 17:
			point["code"] = ["LevelStateBitfield = LevelStateBitfield | 0x2000"]
		elif command == 6:
			point["code"] = ["nextCutscenePart()"]
		elif command == 11:
			point["code"] = ["cancel cutscene something"]
		elif command == 12:
			point["code"] = [f"playSong({int.from_bytes(point['read'],'big')})"]
		elif command == 14:
			point["code"] = ["playCutsceneInMap()"]
		elif command == 13:
			command_info = {
				"sub_command": int.from_bytes(point["read"][0:4],"big")
			}
			params = []
			param_count = int((len(point["read"]) - 4) / 2)
			for a in range(param_count):
				params.append(int.from_bytes(point["read"][4+(2*a):6+(2*a)],"big"))
			command_info["params"] = params
			sub_command = command_info["sub_command"]
			# code = parseSubCommand(sub_command,params)
			# point["code"] = code
		#print(point)
	file_count = 0
	unused_segments = []
	for pt in point_info:
		unused_segments.append(pt["segment"])
	print(file_index, [x["count"] for xi, x in enumerate(cutscene_info) if xi < 7])

class VersionInfo:
    def __init__(self, name: str, pointer_offset: int):
        self.name = name
        self.pointer_offset = pointer_offset
        
class Version(IntEnum):
    us = 0
    pal = auto()
    jp = auto()
    lodgenet = auto()
    kiosk = auto()

versions = [
    VersionInfo("us", 0x101C50),
    VersionInfo("pal", 0x1038D0),
    VersionInfo("jp", 0x1039C0),
    VersionInfo("lodgenet", 0x1037C0),
    VersionInfo("kiosk", 0x1A7C20),
]

maps = [
    "Test Map",  # 0
    "Funky's Store",
    "DK Arcade",
    "K. Rool Barrel: Lanky's Maze",
    "Jungle Japes: Mountain",
    "Cranky's Lab",
    "Jungle Japes: Minecart",
    "Jungle Japes",
    "Jungle Japes: Army Dillo",
    "Jetpac",
    "Kremling Kosh! (very easy)",  # 10
    "Stealthy Snoop! (normal, no logo)",
    "Jungle Japes: Shell",
    "Jungle Japes: Lanky's Cave",
    "Angry Aztec: Beetle Race",
    "Snide's H.Q.",
    "Angry Aztec: Tiny's Temple",
    "Hideout Helm",
    "Teetering Turtle Trouble! (very easy)",
    "Angry Aztec: Five Door Temple (DK)",
    "Angry Aztec: Llama Temple",  # 20
    "Angry Aztec: Five Door Temple (Diddy)",
    "Angry Aztec: Five Door Temple (Tiny)",
    "Angry Aztec: Five Door Temple (Lanky)",
    "Angry Aztec: Five Door Temple (Chunky)",
    "Candy's Music Shop",
    "Frantic Factory",
    "Frantic Factory: Car Race",
    "Hideout Helm (Level Intros, Game Over)",
    "Frantic Factory: Power Shed",
    "Gloomy Galleon",  # 30
    "Gloomy Galleon: K. Rool's Ship",
    "Batty Barrel Bandit! (very easy)",
    "Jungle Japes: Chunky's Cave",
    "DK Isles Overworld",
    "K. Rool Barrel: DK's Target Game",
    "Frantic Factory: Crusher Room",
    "Jungle Japes: Barrel Blast",
    "Angry Aztec",
    "Gloomy Galleon: Seal Race",
    "Nintendo Logo",  # 40
    "Angry Aztec: Barrel Blast",
    "Troff 'n' Scoff",  # 42
    "Gloomy Galleon: Shipwreck (Diddy, Lanky, Chunky)",
    "Gloomy Galleon: Treasure Chest",
    "Gloomy Galleon: Mermaid",
    "Gloomy Galleon: Shipwreck (DK, Tiny)",
    "Gloomy Galleon: Shipwreck (Lanky, Tiny)",
    "Fungi Forest",
    "Gloomy Galleon: Lighthouse",
    "K. Rool Barrel: Tiny's Mushroom Game",  # 50
    "Gloomy Galleon: Mechanical Fish",
    "Fungi Forest: Ant Hill",
    "Battle Arena: Beaver Brawl!",
    "Gloomy Galleon: Barrel Blast",
    "Fungi Forest: Minecart",
    "Fungi Forest: Diddy's Barn",
    "Fungi Forest: Diddy's Attic",
    "Fungi Forest: Lanky's Attic",
    "Fungi Forest: DK's Barn",
    "Fungi Forest: Spider",  # 60
    "Fungi Forest: Front Part of Mill",
    "Fungi Forest: Rear Part of Mill",
    "Fungi Forest: Mushroom Puzzle",
    "Fungi Forest: Giant Mushroom",
    "Stealthy Snoop! (normal)",
    "Mad Maze Maul! (hard)",
    "Stash Snatch! (normal)",
    "Mad Maze Maul! (easy)",
    "Mad Maze Maul! (normal)",  # 69
    "Fungi Forest: Mushroom Leap",  # 70
    "Fungi Forest: Shooting Game",
    "Crystal Caves",
    "Battle Arena: Kritter Karnage!",
    "Stash Snatch! (easy)",
    "Stash Snatch! (hard)",
    "DK Rap",
    "Minecart Mayhem! (easy)",  # 77
    "Busy Barrel Barrage! (easy)",
    "Busy Barrel Barrage! (normal)",
    "Main Menu",  # 80
    "Title Screen (Not For Resale Version)",
    "Crystal Caves: Beetle Race",
    "Fungi Forest: Dogadon",
    "Crystal Caves: Igloo (Tiny)",
    "Crystal Caves: Igloo (Lanky)",
    "Crystal Caves: Igloo (DK)",
    "Creepy Castle",
    "Creepy Castle: Ballroom",
    "Crystal Caves: Rotating Room",
    "Crystal Caves: Shack (Chunky)",  # 90
    "Crystal Caves: Shack (DK)",
    "Crystal Caves: Shack (Diddy, middle part)",
    "Crystal Caves: Shack (Tiny)",
    "Crystal Caves: Lanky's Hut",
    "Crystal Caves: Igloo (Chunky)",
    "Splish-Splash Salvage! (normal)",
    "K. Lumsy",
    "Crystal Caves: Ice Castle",
    "Speedy Swing Sortie! (easy)",
    "Crystal Caves: Igloo (Diddy)",  # 100
    "Krazy Kong Klamour! (easy)",
    "Big Bug Bash! (very easy)",
    "Searchlight Seek! (very easy)",
    "Beaver Bother! (easy)",
    "Creepy Castle: Tower",
    "Creepy Castle: Minecart",
    "Kong Battle: Battle Arena",
    "Creepy Castle: Crypt (Lanky, Tiny)",
    "Kong Battle: Arena 1",
    "Frantic Factory: Barrel Blast",  # 110
    "Gloomy Galleon: Puftoss",
    "Creepy Castle: Crypt (DK, Diddy, Chunky)",
    "Creepy Castle: Museum",
    "Creepy Castle: Library",
    "Kremling Kosh! (easy)",
    "Kremling Kosh! (normal)",
    "Kremling Kosh! (hard)",
    "Teetering Turtle Trouble! (easy)",
    "Teetering Turtle Trouble! (normal)",
    "Teetering Turtle Trouble! (hard)",  # 120
    "Batty Barrel Bandit! (easy)",
    "Batty Barrel Bandit! (normal)",
    "Batty Barrel Bandit! (hard)",
    "Mad Maze Maul! (insane)",
    "Stash Snatch! (insane)",
    "Stealthy Snoop! (very easy)",
    "Stealthy Snoop! (easy)",
    "Stealthy Snoop! (hard)",
    "Minecart Mayhem! (normal)",
    "Minecart Mayhem! (hard)",  # 130
    "Busy Barrel Barrage! (hard)",
    "Splish-Splash Salvage! (hard)",
    "Splish-Splash Salvage! (easy)",
    "Speedy Swing Sortie! (normal)",
    "Speedy Swing Sortie! (hard)",
    "Beaver Bother! (normal)",
    "Beaver Bother! (hard)",
    "Searchlight Seek! (easy)",
    "Searchlight Seek! (normal)",
    "Searchlight Seek! (hard)",  # 140
    "Krazy Kong Klamour! (normal)",
    "Krazy Kong Klamour! (hard)",
    "Krazy Kong Klamour! (insane)",
    "Peril Path Panic! (very easy)",
    "Peril Path Panic! (easy)",
    "Peril Path Panic! (normal)",
    "Peril Path Panic! (hard)",
    "Big Bug Bash! (easy)",
    "Big Bug Bash! (normal)",
    "Big Bug Bash! (hard)",  # 150
    "Creepy Castle: Dungeon",
    "Hideout Helm (Intro Story)",
    "DK Isles (DK Theatre)",
    "Frantic Factory: Mad Jack",
    "Battle Arena: Arena Ambush!",
    "Battle Arena: More Kritter Karnage!",
    "Battle Arena: Forest Fracas!",
    "Battle Arena: Bish Bash Brawl!",
    "Battle Arena: Kamikaze Kremlings!",
    "Battle Arena: Plinth Panic!",  # 160
    "Battle Arena: Pinnacle Palaver!",
    "Battle Arena: Shockwave Showdown!",
    "Creepy Castle: Basement",
    "Creepy Castle: Tree",
    "K. Rool Barrel: Diddy's Kremling Game",
    "Creepy Castle: Chunky's Toolshed",
    "Creepy Castle: Trash Can",
    "Creepy Castle: Greenhouse",
    "Jungle Japes Lobby",
    "Hideout Helm Lobby",  # 170
    "DK's House",
    "Rock (Intro Story)",
    "Angry Aztec Lobby",
    "Gloomy Galleon Lobby",
    "Frantic Factory Lobby",
    "Training Grounds",
    "Dive Barrel",
    "Fungi Forest Lobby",
    "Gloomy Galleon: Submarine",
    "Orange Barrel",  # 180
    "Barrel Barrel",
    "Vine Barrel",
    "Creepy Castle: Crypt",
    "Enguarde Arena",
    "Creepy Castle: Car Race",
    "Crystal Caves: Barrel Blast",
    "Creepy Castle: Barrel Blast",
    "Fungi Forest: Barrel Blast",
    "Fairy Island",
    "Kong Battle: Arena 2",  # 190
    "Rambi Arena",
    "Kong Battle: Arena 3",
    "Creepy Castle Lobby",
    "Crystal Caves Lobby",
    "DK Isles: Snide's Room",
    "Crystal Caves: Army Dillo",
    "Angry Aztec: Dogadon",
    "Training Grounds (End Sequence)",
    "Creepy Castle: King Kut Out",
    "Crystal Caves: Shack (Diddy, upper part)",  # 200
    "K. Rool Barrel: Diddy's Rocketbarrel Game",
    "K. Rool Barrel: Lanky's Shooting Game",
    "K. Rool Fight: DK Phase",
    "K. Rool Fight: Diddy Phase",
    "K. Rool Fight: Lanky Phase",
    "K. Rool Fight: Tiny Phase",
    "K. Rool Fight: Chunky Phase",
    "Bloopers Ending",
    "K. Rool Barrel: Chunky's Hidden Kremling Game",
    "K. Rool Barrel: Tiny's Pony Tail Twirl Game",  # 210
    "K. Rool Barrel: Chunky's Shooting Game",
    "K. Rool Barrel: DK's Rambi Game",
    "K. Lumsy Ending",
    "K. Rool's Shoe",
    "K. Rool's Arena",  # 215
    "UNKNOWN 216",
    "UNKNOWN 217",
    "UNKNOWN 218",
    "UNKNOWN 219",
    "UNKNOWN 220",
    "UNKNOWN 221",
]

def getROMData(rom_path: str, folder: str) -> tuple:
    version = -1
    with open(rom_path,"rb") as fh:
        endianness = int.from_bytes(fh.read(1),"big")
        if endianness != 0x80:
            print("File is little endian. Convert to big endian and re-run")
            return (None, None, None, False)
        else:
            fh.seek(0x3D)
            release_or_kiosk = int.from_bytes(fh.read(1),"big")
            region = int.from_bytes(fh.read(1),"big")
            if release_or_kiosk == 0x50:
                version = Version.kiosk # Kiosk
            else:
                if region == 0x45:
                    version = Version.us # US
                elif region == 0x4A:
                    version = Version.jp # JP
                elif region == 0x50:
                    version = Version.pal # PAL
                elif region == 0x47:
                    version = Version.lodgenet # Lodgenet
                else:
                    print("Invalid version")
                    return (None, None, None, False)
            version_info = versions[version]
            pointer_table_offset = version_info.pointer_offset
            append = version_info.name
        if version < Version.us or version > Version.kiosk:
            print("Invalid version")
            return (None, None, None, False)
    return (pointer_table_offset, version, None, version >= Version.us and version <= Version.lodgenet)

file_path = "/home/tballaam/Documents/ROMs/dk64.z64"
pointer_table_offset, version, dump_path, valid = getROMData(file_path, "cutscenes")
if valid:
	cutscene_table_index = 8
	if version == Version.kiosk:
		cutscene_table_index = 7
	with open(file_path,"rb") as romfile:
		romfile.seek(pointer_table_offset + (cutscene_table_index * 4))
		pointer_table = pointer_table_offset + int.from_bytes(romfile.read(4),"big")&0x7FFFFFFF
		romfile.seek(pointer_table_offset + (cutscene_table_index * 4) + (32*4))
		tbl_size = int.from_bytes(romfile.read(4),"big")
		for map_id in range(tbl_size-1):
			map_name = maps[map_id];
			romfile.seek(pointer_table + (4 * map_id))
			file_location = pointer_table_offset + int.from_bytes(romfile.read(4),"big")&0x7FFFFFFF
			romfile.seek(pointer_table + 4 + (4 * map_id))
			file_end = pointer_table_offset + int.from_bytes(romfile.read(4),"big")&0x7FFFFFFF
			file_size = file_end - file_location
			romfile.seek(file_location)
			compress = romfile.read(file_size)
			if int.from_bytes(compress[0:1],"big") == 0x1F and int.from_bytes(compress[1:2],"big") == 0x8B:
				data = zlib.decompress(compress, 15+32)
				# print(f"[{map_id+1}/{tbl_size-1}] Analyzing: {map_name}")
				analyzeFile(data,f"{dump_path}/{map_name}",map_id)
			else:
				data = compress
				print(f"[{map_id+1}/{tbl_size-1}] Ignoring: {map_name}")