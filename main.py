from api.tools import build_classpath, download_file, increase_file_limits, normalize_path, run_process, send_get, get_args, setup_args
import requests, json, os, tqdm, time, pathlib, zipfile, math
from api.java import download_java_manifests, download_java
from api.assets import download_assets, download_indexes
from api.natives import download_natives, unzip
from api.libs import download_libs
from api.game import download_game
from api.auth import get_account
from platform import system
import multiprocessing as mp
import subprocess

os_name = system().lower()
os_name = os_name.replace("darwin", "mac-os")
os_name = os_name if not os.path.exists("/storage") else "android"

# Setting defaults dirs

root_dir = pathlib.Path("./")
path_for_java = pathlib.Path(root_dir if os.name != "android" else pathlib.Path.home())



game_root_dir = str(pathlib.Path(f"{root_dir}/.minecraft"))

if not os.path.exists(game_root_dir):
	os.makedirs(game_root_dir, exist_ok=True)

ver_dir = str(pathlib.Path(str(game_root_dir) + "/versions"))
lib_dir = str(pathlib.Path(str(game_root_dir) + "/libraries"))
assets_dir = str(pathlib.Path(str(game_root_dir) + "/assets"))
java_dir = str(pathlib.Path(str(path_for_java) + f"/{"" if os.name != "android" else "."}java"))
game_dir = str(pathlib.Path(str(game_root_dir) + "/home"))

os.makedirs(ver_dir, exist_ok=True)
os.makedirs(lib_dir, exist_ok=True)
os.makedirs(assets_dir, exist_ok=True)
os.makedirs(java_dir, exist_ok=True)
os.makedirs(game_dir, exist_ok=True)

###############
#  Functions  #
###############

def start_mine(
		uuid: str, username: str, assets_token: int, user_type: str,
		version, version_data, mc_dir,
		java_path, Xms, Xmx, 
		width: int = 925, height: int = 525
	) -> str:
	global assets_dir, ver_dir, game_root_dir
	jvm_args = [f"-Xms{Xms}", f"-Xmx{Xmx}", "-Dfile.encoding=UTF-8"]
	classpath = build_classpath(version, pathlib.Path(mc_dir), version_data, game_root_dir)
	asset_index = version_data["assetIndex"]["id"]

	game_args = get_args(
		username, version, mc_dir, assets_dir, asset_index,
		uuid, assets_token, user_type
	)

	main_class = version_data["mainClass"]
	natives_dir = normalize_path(os.path.abspath(f"{ver_dir}/{version}/natives"))

	cmd_line = [os.path.abspath(java_path)]
	cmd_line.extend(jvm_args)
	cmd_line.append(f"-Djava.library.path={natives_dir}")
	cmd_line.append("-cp")
	cmd_line.append(classpath)
	cmd_line.append(main_class)
	cmd_line.extend(game_args)

	cmd_line.append(f"--width={str(width)}")
	cmd_line.append(f"--height={str(height)}")

	print("")
	print("Команда запуска JVM:")
	print("\n".join(cmd_line))
	print("")

	# Вывод архитектуры JVM
	print("Проверка архитектуры JVM:")
	import subprocess
	try:
		result = subprocess.run([os.path.abspath(java_path), "-version"], capture_output=True, text=True)
		print(result.stderr.strip() or result.stdout.strip())
	except Exception as e:
		print(f"Ошибка при запуске java -version: {e}")

	# Вывод списка dll из папки natives
	print(f"\nСодержимое папки natives ({natives_dir}):")
	try:
		for f in os.listdir(natives_dir):
			if f.lower().endswith('.dll') or f.lower().endswith(".so"):
				print("  ", f)
	except Exception as e:
		print(f"Ошибка при просмотре natives: {e}")

	print("Increasing file limits (only for Linux)...")
	increase_file_limits()

	print("")
	subprocess.run(cmd_line)
	#return run_process(cmd_line)

def join_all(th_s):
	for th in th_s:
		if not th.is_alive: continue
		th.join()

##########
#  Main  #
##########

def main():
	global ver_dir, lib_dir, assets_dir, game_dir, os_name

	(arg_username, arg_version, uuid, assets_token,
	user_type, arg_debug, arg_xmx, arg_xms, woa,
	width, height) = setup_args()

	#####################
	#  Print base data  #
	#####################

	print(f"You're OS: {os_name}")
	print(F"Versions dir: {ver_dir}")
	print(f"Libraries dir: {lib_dir}")
	print(f"Assets dir: {assets_dir}")
	print(f"Game root dir: {game_dir}")

	#######################
	#  Request to mojang  #
	#######################

	content = send_get("https://launchermeta.mojang.com/mc/game/version_manifest.json")
	data = json.loads(content)["versions"]

	releases = {}
	downloaded = {}

	########################
	#  Parsing web source  #
	########################

	for ver in tqdm.tqdm(data, desc="Parsing"):
		if ver["type"] != "release": continue
		releases[ver["id"]] = ver["url"]

	#########################
	#  Initialize versions  #
	#########################


	for release, url in tqdm.tqdm(releases.items(), desc="Installing data"):
		file = f"{ver_dir}/{release}/{release}.json"

		if os.path.exists(f"{ver_dir}/{release}/{release}.json"):
			with open(file, 'r') as f:
				downloaded[release] = json.load(f)
				f.close()
			continue

		if not os.path.exists(f"{ver_dir}/{release}"):
			os.mkdir(f"{ver_dir}/{release}")

		download_file(url, file)

		with open(file, 'r') as f:
			downloaded[release] = json.load(f)
			f.close()


	##########################
	#  Downloading versions  #
	##########################
	processes = []

	q0 = mp.Queue()
	p0 = mp.Process(target=download_game, args=(q0, ver_dir, downloaded), name="Downloading version jar")
	p0.start()

	processes.append(p0)
	###########################
	#  Downloading libraries  #
	###########################

	q1 = mp.Queue()
	p1 = mp.Process(target=download_libs, args=(q1, lib_dir, downloaded), name="Downloading libraries")
	p1.start()

	processes.append(p1)
	#########################
	#  Downloading assets  #
	#########################

	q2 = mp.Queue()
	p2 = mp.Process(target=download_indexes, args=(q2, assets_dir+"/indexes", downloaded), name="Downloading assets")
	p2.start()

	processes.append(p2)
	#########################
	#  Downloading natives  #
	#########################

	os_name_for_natives = os_name if os_name != "android" else "linux"

	q3 = mp.Queue()
	p3 = mp.Process(target=download_natives, args=(q3, ver_dir, downloaded, os_name_for_natives), name="downloading natives")
	p3.start()

	processes.append(p3)
	###################
	#  Download java  #
	###################
	content = send_get("https://launchermeta.mojang.com/v1/products/java-runtime/2ec0cc96c44e5a76b9c8b7c39df7210883d12871/all.json")

	os_ls = {
		"windows": "windows-x64",
		"linux": "linux",
		"android": "linux",
		"mac-os": "mac-os-arm64"
	}

	data0 = json.loads(bytes(content).decode())[os_ls[os_name.lower()]]

	q4 = mp.Queue()
	p4 = mp.Process(target=download_java_manifests, args=(q4, java_dir, data0), name="Downloading java manifests")
	p4.start()

	processes.append(p4)
	#####################
	#  Start minecraft  #
	#####################
	print("Waiting game..."+" "*10)
	game_versions = q0.get()
	p0.join()
	p0.close()

	print("Waiting libraries..."+" "*10)
	libraries = q1.get()
	p1.join()
	p1.close()

	print("Waiting assets..."+" "*10)
	indexes, assets = q2.get()
	p2.join()
	p2.close()

	print("Waiting natives..."+" "*10)
	natives = q3.get()
	p3.join()
	p3.close()

	print("Waiting java..."+" "*10)
	javas = q4.get()
	p4.join()
	p4.close()

	if not woa:
		auth_enable = bool(input("You want auth? (y/n): ").strip().lower() == "y")
	else:
		auth_enable = False
	account_username = ""
	account_uuid = ""
	account_at = 0
	
	if auth_enable:
		account_data = get_account("eec03098-1390-4363-b06b-ac8e519fca70")
		account_username = account_data["username"]
		account_uuid = account_data["uuid"]
		account_at = account_data["access_token"]


	if arg_version != "":
		version = arg_version
	else:
		version = input("Select version of minecraft: ")

	if arg_username != "":
		username = arg_username
	else:

		if not auth_enable:
			username = input("Enter your username: ")
		else:
			username = account_username

	if not version in downloaded:
		raise NameError(version, "not downloaded or not exists")

	mc_dir = normalize_path(game_dir + "/" + version)
	os.makedirs(mc_dir, exist_ok=True)

	data = downloaded[version]

	java_codename = data["javaVersion"]["component"]

	if arg_debug:
		debug = True
	else:
		enable = bool(input("Enable log output? (y/n): ").strip().lower() == "y")
		debug = enable

	if arg_xmx != "":
		xmx = arg_xmx
	else:
		xmx = "2048M"

	if arg_xms != "":
		xms = arg_xms
	else:
		xms = "2048M"

	java_run_path = normalize_path(java_dir + "/" + java_codename + f"/bin/java{'' if debug else 'w'}{'.exe' if os.name == 'nt' else ''}")

	# Xms - min mem
	# Xmx - max mem

	uuid = account_uuid if auth_enable else "00000000-0000-0000-0000-000000000000"
	assets_token = account_at if auth_enable else 0
	user_type = "msa" if auth_enable else "legacy"

	start_mine(
		uuid, username, assets_token,
		user_type, version, data,
		mc_dir, java_run_path, xms, xmx,
		width, height
	)

###########
#  START  #
###########

if __name__ == "__main__":
	main() # 210 строк