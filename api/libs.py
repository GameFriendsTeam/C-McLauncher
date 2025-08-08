import os
from api.tools import download_file

def download_libs(q, lib_dir: str, releases: dict[str, dict]) -> dict[str, str]:
	libraries = {}

	ver_count = len(releases)
	current_ver_int = 0

	for version, ver_data in releases.items():
		current_ver_int += 1

		libs = ver_data["libraries"]
		libs_count = len(libs)
		current_lib_int = 0

		for lib in libs:
			current_lib_int += 1
			if (not "downloads" in lib or not "artifact" in lib["downloads"]):
				continue

			lib_url = lib["downloads"]["artifact"]["url"]
			artifact = lib["downloads"]["artifact"]
			# Безопасно получаем путь к файлу
			if "path" in artifact:
				lib_path = artifact["path"]
				file_name = os.path.basename(lib_path)
			else:
				from urllib.parse import urlparse
				file_name = os.path.basename(urlparse(lib_url).path)
				lib_path = file_name
			lib_full_path = lib_dir + "/" + lib_path
			lib_clean_path = os.path.dirname(lib_full_path)

			libraries[lib["name"]] = lib_full_path

			lib_sha1 = artifact.get("sha1")
			need_download = True
			if os.path.exists(lib_full_path):
				continue

			if need_download:
				os.makedirs(lib_clean_path, exist_ok=True)
				print(f"Downloading libraries: {str(round(current_lib_int/libs_count*100))}% | {str(round(current_ver_int/ver_count*100))}%"+" "*10, end="\r", flush=True)
				download_file(lib_url, lib_full_path)

	q.put(libraries)
	return