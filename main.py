from api.tools import build_classpath, download_file, lazy_download_file, normalize_path, run_process, send_get, get_args
import requests, json, os, tqdm, time, pathlib, zipfile, math
from api.java import download_java_manifests, download_java
from api.assets import download_assets, download_indexes
from api.natives import download_natives, unzip
from api.libs import download_libs
from api.game import download_game
from platform import system
import multiprocessing as mp
import subprocess

os_name = system().lower()
os_name = os_name.replace("darwin", "mac-os")
os_name = os_name if not os.path.exists("/storage") else "android"

# Setting defaults dirs

root_dir = pathlib.Path("./")
path_for_java = pathlib.Path(root_dir if os.name != "android" else pathlib.Path.home())

os.chmod(root_dir, mode=777)

game_root_dir = str(pathlib.Path(f"{root_dir}/.minecraft"))

if os.path.exists(game_root_dir):
	os.chmod(game_root_dir, mode=777)
else:
	os.makedirs(game_root_dir, mode=777, exist_ok=True)

ver_dir = pathlib.Path(game_root_dir + "/versions")
lib_dir = pathlib.Path(game_root_dir + "/libraries")
assets_dir = pathlib.Path(game_root_dir + "/assets")
java_dir = pathlib.Path(path_for_java + f"/{"" if os.name != "android" else "."}java")
game_dir = pathlib.Path(game_root_dir + "/home")

os.makedirs(ver_dir, mode=777, exist_ok=True)
os.makedirs(lib_dir, mode=777, exist_ok=True)
os.makedirs(assets_dir, mode=777, exist_ok=True)
os.makedirs(java_dir, mode=777, exist_ok=True)
os.makedirs(game_dir, mode=777, exist_ok=True)

###############
#  Functions  #
###############

def start_mine(
		version, version_data, mc_dir,
		java_path, username, Xms, Xmx, 
		width: int = 925, height: int = 525
	) -> str:
	global assets_dir, ver_dir
	jvm_args = [f"-Xms{Xms}M", f"-Xmx{Xmx}M", "-Dfile.encoding=UTF-8"]
	classpath = build_classpath(version, pathlib.Path(mc_dir), version_data)
	asset_index = version_data["assetIndex"]["id"]

	game_args = get_args(username, version, mc_dir, assets_dir, asset_index)

	main_class = version_data["mainClass"]
	natives_dir = normalize_path(os.path.abspath(f"{ver_dir}/{version}/natives/"))

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
			if f.lower().endswith('.dll'):
				print("  ", f)
	except Exception as e:
		print(f"Ошибка при просмотре natives: {e}")

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
			continue

		if not os.path.exists(f"{ver_dir}/{release}"):
			os.mkdir(f"{ver_dir}/{release}", mode=777)

		lazy_download_file(url, file)

		with open(file, 'r') as f:
			downloaded[release] = json.load(f)


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

	q3 = mp.Queue()
	p3 = mp.Process(target=download_natives, args=(q3, ver_dir, downloaded, os_name), name="downloading natives")
	p3.start()

	processes.append(p3)
	###################
	#  Download java  #
	###################
	content = send_get("https://launchermeta.mojang.com/v1/products/java-runtime/2ec0cc96c44e5a76b9c8b7c39df7210883d12871/all.json")

	os_ls = {
		"windows": "windows-x64",
		"linux": "linux",
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


	version = input("Select version of minecraft: ")
	username = input("Enter your username: ")
	if not version in downloaded:
		raise NameError(version, "not downloaded or not exists")

	mc_dir = normalize_path(game_dir + "/" + version)
	os.makedirs(mc_dir, mode=777, exist_ok=True)

	data = downloaded[version]

	java_codename = data["javaVersion"]["component"]

	debug = True

	java_run_path = normalize_path(java_dir + "/" + java_codename + f"/bin/java{'' if debug else 'w'}{'.exe' if os.name == 'nt' else ''}")

	# Xms - min mem
	# Xmx - max mem

	start_mine(
		version, data, mc_dir, java_run_path,
		username, Xms=4096, Xmx=4096,
		width=1280, height=720
	)

###########
#  START  #
###########

if __name__ == "__main__":
	main() # 210 строк