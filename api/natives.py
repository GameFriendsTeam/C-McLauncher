import os, json
from api.tools import download_file, unzip_jar
from urllib.parse import urlparse

def download_natives(q, ver_dir: str, releases: dict[str, dict], os_name: str) -> dict[str, list]:
	natives = {}

	global_count = len(releases)
	current_global = 0

	for version, data in releases.items():
		current_global += 1

		target_dir = f"{ver_dir}/{version}/natives"

		natives[version] = []

		libs = data["libraries"]

		local_count = len(libs)
		current_local = 0


		for lib in libs:
			current_local += 1

			# --- Старый формат (classifiers) ---
			if ("natives" in lib and "classifiers" in lib["downloads"] and os_name in lib["natives"]):
				classifier_name = lib["natives"][os_name]
				if "${" in classifier_name:
					classifier_name = classifier_name.replace("${arch}", "64")
				classifiers = lib["downloads"]["classifiers"]
				if not classifier_name in classifiers:
					continue
				classifier = classifiers[classifier_name]
				url = classifier["url"]
				if "path" in classifier:
					path = classifier["path"]
					file_name = os.path.basename(path)
				else:
					file_name = os.path.basename(urlparse(url).path)
				file_path = target_dir + "/" + file_name
				natives[version].append(file_path)
				if os.path.exists(file_path): continue
				os.makedirs(target_dir, mode=777, exist_ok=True)
				print(f"Downloading natives: {str(round(current_local/local_count*100))}% | {str(round(current_global/global_count*100))}%   ", end="\r", flush=True)
				download_file(url, file_path)
				continue


			# --- Новый формат Mojang: по ключу rules ---
			if "rules" in lib:
				for rule in lib["rules"]:
					if rule.get("action") == "allow":
						if not os_name in rule.get("os", {}).get("name", ""):
							continue

						# Если правило разрешает, загружаем артефакт
						artifact = lib["downloads"].get("artifact")
						if artifact:
							url = artifact.get("url")
							path = artifact.get("path")
							if not url or not path:
								continue
							file_name = os.path.basename(path)
							file_path = target_dir + "/" + file_name
							natives[version].append(file_path)
							if os.path.exists(file_path): continue
							os.makedirs(target_dir, mode=777, exist_ok=True)
							print(f"Downloading natives: {str(round(current_local/local_count*100))}% | {str(round(current_global/global_count*100))}%   ", end="\r", flush=True)
							download_file(url, file_path)
							continue

	unzip(natives)

	q.put(natives)

def unzip(natives: dict[str, list]):
	for version, R_natives in natives.items():

		for native in R_natives:
			dir = os.path.dirname(native)
			unzip_jar(native, dir)
