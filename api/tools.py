import subprocess, threading, zipfile, os, requests, time, pathlib
from urllib.parse import urlparse
import argparse

def normalize_path(p):
	if os.name == "nt":
		return str(pathlib.PurePath(p)).replace('/', '\\')

	return str(pathlib.PurePath(p)).replace('\\', '/')

def build_classpath(mc_ver, mc_dir, version_data, root_dir):
	cp_paths = []
	mc_dir = pathlib.Path(mc_dir)
	root_dir = str(root_dir)
	client_jar = root_dir + "/versions/" + mc_ver + f"/{mc_ver}.jar"
	cp_paths.append(normalize_path(client_jar))

	lib_versions = {}
	lib_paths = {}
	# natives_info больше не нужен

	def parse_lib_id(lib):
		name = lib.get("name", "")
		parts = name.split(":")
		if len(parts) == 3:
			group, artifact, version = parts
			return f"{group}:{artifact}", version
		return name, ""

	from packaging.version import parse as parse_version

	for lib in version_data["libraries"]:
		artifact = lib.get("downloads", {}).get("artifact")
		if not artifact:
			continue
		lib_id, version = parse_lib_id(lib)
		if not lib_id or not version:
			continue
		if lib_id not in lib_versions:
			lib_versions[lib_id] = []
			lib_paths[lib_id] = []
		lib_versions[lib_id].append(version)
		if "path" in artifact:
			lib_path = artifact["path"]
		else:
			lib_url = artifact["url"]
			lib_path = os.path.basename(urlparse(lib_url).path)
		if "natives" in lib:
			continue
		lib_paths[lib_id].append((version, normalize_path(root_dir + "/libraries/" + lib_path)))

	for lib_id, versions in lib_versions.items():
		if lib_id not in lib_paths:
			continue
		if len(versions) > 1:
			valid_versions = []
			for v in versions:
				try:
					_ = parse_version(v)
					valid_versions.append(v)
				except Exception:
					pass
			if valid_versions: best_version = max(valid_versions, key=lambda v: parse_version(v))
			else: best_version = versions[0]
		else: best_version = versions[0]
		for v, path in lib_paths[lib_id]:
			if v == best_version and pathlib.Path(path).exists():
				cp_paths.append(path)
				break

	return ";".join(cp_paths)

def run_process(command_line):
	startupinfo = subprocess.STARTUPINFO()
	startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
	startupinfo.wShowWindow = 0
	try:
		proc = subprocess.Popen(
			command_line,
			startupinfo=startupinfo,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			text=True
		)
		stdout, stderr = proc.communicate()
		if proc.returncode != 0:
			print(f"Process failed with code {proc.returncode}")
			print("STDOUT:", stdout)
			print("STDERR:", stderr)
		return proc.returncode == 0
	except Exception as e:
		print(f"Error starting process: {e}")
		return False

def get_args(
		username: str, version: str, mc_dir: str, assets_dir: str,
		asset_index: str, uuid: str = "00000000-0000-0000-0000-000000000000",
		assets_token: int = 0, user_type: str = "legacy"
	) -> list:
	game_args = ["--username", username]
	game_args.append("--version")
	game_args.append(version)
	game_args.append("--gameDir")
	game_args.append(os.path.abspath(mc_dir))
	game_args.append("--assetsDir")
	game_args.append(os.path.abspath(assets_dir))
	game_args.append("--assetIndex")
	game_args.append(asset_index)
	game_args.append("--uuid")
	game_args.append(uuid)
	game_args.append("--accessToken")
	game_args.append(str(assets_token))
	game_args.append("--userType")
	game_args.append(user_type)
	game_args.append("-Dminecraft.launcher.brand=java-minecraft-launcher")
	game_args.append("-Dminecraft.launcher.version=1.6.84-j")
	#game_args.append("--userProperties")
	#game_args.append("{}")
	game_args.append("--versionType")
	game_args.append("release")

	return game_args


def download_file(url: str, filename: str, s=3):
	filename = pathlib.Path(filename)
	dir_path = filename.parent
	if dir_path and not dir_path.exists(): dir_path.mkdir(parents=True, exist_ok=True)

	try:
		response = requests.get(url)
		response.raise_for_status()
		
		with open(filename, 'wb') as f: f.write(response.content)
		return
	
	except requests.exceptions.RequestException as e:
		print(f"Error downloading {filename}: {e}. Retrying in {s}s...")
		time.sleep(s)

	except PermissionError as e:
		print(f"[PermissionError] {e}")
		raise

def send_get(url: str, s: int = 3) -> object:
	content = None
	try:
		response = requests.get(url)
		response.raise_for_status()
		content = response.content
	except requests.exceptions.RequestException as e:
		time.sleep(s)
		content = send_get(url)

	return content


def unzip_jar(target_path, out_path):
	try:
		with zipfile.ZipFile(target_path, 'r') as z_object:
			if out_path:
				os.makedirs(out_path, exist_ok=True)
				z_object.extractall(out_path)
			else: z_object.extractall()

	except zipfile.BadZipFile: raise IOError(f"Error: '{target_path}' is not a valid ZIP (or JAR) file.")
	except FileNotFoundError: raise IOError(f"Error: JAR file not found at '{target_path}'.")
	except Exception as e: raise Exception(f"An unexpected error occurred: {e}")

def get_filename_from_url(url, default = "null"):
	try:
		parsed = urlparse(url)
		filename = os.path.basename(parsed.path)
		return filename
	except: return default

def file_sha1(path):
	import hashlib
	h = hashlib.sha1()
	with open(path, 'rb') as f:
		while True:
			chunk = f.read(8192)
			if not chunk: break
			h.update(chunk)
	return h.hexdigest()

def setup_args():
	parser = argparse.ArgumentParser(description='C-McLauncher')
	parser.add_argument("--username", "-u", type=str, default="", help="The username of the player.")
	parser.add_argument("--version", "-v", type=str, default="", help="The version of the game.")
	parser.add_argument("--uuid", "-i", type=str, default="00000000-0000-0000-0000-000000000000", help="The UUID of the player.")
	parser.add_argument("--assets-token", "-at", type=int, default=0, help="The assets token.")
	parser.add_argument("--user-type", "-ut", type=str, default="legacy", help="The user type.")
	parser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode.")
	parser.add_argument("-Xmx", type=str, default="", help="Maximum memory allocation.")
	parser.add_argument("-Xms", type=str, default="", help="Minimum memory allocation.")
	parser.add_argument("--without_auth", "-woa", action="store_true", help="Disable auth request.")
	parser.add_argument("--wight", "-wi", type=int, default=1280)
	parser.add_argument("--height", "-he", type=int, default=720)

	args = parser.parse_args()

	username = args.username
	version = args.version
	uuid = args.uuid
	assets_token = args.assets_token
	user_type = args.user_type
	debug = args.debug
	xmx = args.Xmx
	xms = args.Xms
	woa = args.without_auth
	wight = args.wight
	height = args.height

	return (
		username, version, uuid, assets_token,
		user_type, debug, xmx, xms, woa,
		wight, height
	)