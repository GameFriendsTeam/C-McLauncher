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

		# Список нужных natives-файлов и их sha1
		expected_natives = []


		for lib in libs:
			current_local += 1
			# --- Старый формат (classifiers) ---
			if "natives" in lib and "classifiers" in lib["downloads"]:
				if not os_name in lib["natives"]:
					continue

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

				if os.path.exists(file_path):
					continue

				print(f"[DEBUG] Classifier Name: {classifier_name}")
				print(f"[DEBUG] URL: {url}")
				print(f"[DEBUG] File Name: {file_name}")
				print(f"[DEBUG] File Path: {file_path}")

				download_file(url, str(file_path))
				natives[version].append(file_path)

			# --- Новый формат Mojang: по ключу rules ---
			elif "rules" in lib:
				for rule in lib["rules"]:
					if rule.get("action") == "allow":
						if not os_name in rule.get("os", {}).get("name", ""):
							continue
						artifact = lib["downloads"].get("artifact")
						if artifact:
							url = artifact.get("url")
							path = artifact.get("path")
							if not url or not path:
								continue
							file_name = os.path.basename(path)
							file_path = target_dir + "/" + file_name

							if os.path.exists(file_path):
								continue

							print(f"[DEBUG] Artifact URL: {url}")
							print(f"[DEBUG] Artifact File Name: {file_name}")
							print(f"[DEBUG] Artifact File Path: {file_path}")

						download_file(url, str(file_path))
						natives[version].append(file_path)

	unzip(natives)
	q.put(natives)

def unzip(jar_files: dict[str, list[str]]):
	for version, jars in jar_files.items():
		for jar in jars:
			dir = os.path.dirname(jar)
			unzip_jar(jar, dir)
