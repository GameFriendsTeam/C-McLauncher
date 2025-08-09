import json
import os
from api.tools import download_file

def download_java_manifests(q, java_dir: str, runtime_data: dict[str, dict]) -> dict[str, str]:
	javas = {}

	for codename, data in runtime_data.items():
		if len(data) < 1:
			continue
		data = data[0]

		version = data["version"]["name"]
		url = data["manifest"]["url"]
		asset_sha1 = data["manifest"]["sha1"]

		jre_dir = java_dir + "/" + codename
		file_path = jre_dir + "/" + "/manifest.json"

		if os.path.exists(file_path):
			continue

		os.makedirs(jre_dir, exist_ok=True)

		download_file(url, file_path)

		with open(file_path, 'r') as f:
			javas[codename] = json.load(f)


	download_java(java_dir, javas)
	
	q.put(javas)

def download_java(dir_of_java: str, javas: dict[str, dict]):
	import stat, sys

	global_count = len(javas)
	current_global = 0

	for codename, java_data in javas.items():
		java_dir = dir_of_java + "/" + codename
		files = java_data["files"]

		current_global += 1
		local_count = len(files)
		current_local = 0

		for name, info in files.items():
			type = info["type"]
			full_path = java_dir + "/" + name

			current_local += 1

			if type == "directory":
				os.makedirs(full_path, exist_ok=True)
				continue
			elif type == "link":
				target = info["target"]

				if os.path.exists(full_path): os.remove(full_path)

				parent_dir = os.path.dirname(full_path)
				if not os.access(parent_dir, os.W_OK):
					print(f"Error: {parent_dir} - access denied")
					continue

				try:
					os.symlink(target, full_path)

					if not os.path.exists(target):
						raise FileNotFoundError(f"Target not found: {dir_of_java + '/' + target}")

				except PermissionError as e:
					print(f"Error: {full_path} - permission denied")

				except FileNotFoundError as e:
					print(f"Error: {dir_of_java + '/' + target} not exists")

				continue

			url = info["downloads"]["raw"]["url"]
			file_sha1_expected = info["downloads"]["raw"].get("sha1")


			if os.path.exists(full_path):
				continue
			print(f"Downloading java {str(round(current_local/local_count*100))}% | {str(round(current_global/global_count*100))}%", end="\r")
			download_file(url, full_path)
			print(f"Downloaded {full_path}")

			if os.name != "nt":
				try:
					# Только для файлов внутри bin/
					rel = os.path.relpath(full_path, java_dir)
					if rel.startswith("bin/") or rel.startswith("bin\\"):
						os.chmod(full_path, 0o755)
					else:
						os.chmod(full_path, 0o644)
				except Exception:
					pass