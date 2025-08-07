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

		jre_dir = java_dir + "/" + codename
		file_path = jre_dir + "/" + "/manifest.json"

		if os.path.exists(file_path):
			with open(file_path, 'r') as f:
				javas[codename] = json.load(f)
			continue

		os.makedirs(jre_dir, mode=777, exist_ok=True)
		download_file(url, file_path)
		with open(file_path, 'r') as f:
			javas[codename] = json.load(f)


	download_java(java_dir, javas)
	
	q.put(javas)

def download_java(dir_of_java: str, javas: dict[str, dict]):
	for codename, java_data in javas.items():
		java_dir = dir_of_java + "/" + codename
		files = java_data["files"]

		for name, info in files.items():
			type = info["type"]
			full_path = java_dir + "/" + name

			if type == "directory":
				os.makedirs(full_path, mode=777, exist_ok=True)
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
						raise FileNotFoundError(f"Target not found: {target}")
					
				except PermissionError as e:
					print(f"Error: {full_path} - permission denied")

				except FileNotFoundError as e:
					print(f"Error: {target} not exists")

				continue

			url = info["downloads"]["raw"]["url"]

			if os.path.exists(full_path): continue
			download_file(url, full_path)