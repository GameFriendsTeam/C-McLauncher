import asyncio
import os
from api.tools import download_file

def download_game(q, ver_dir, releases: dict[str, str]):
	versions = {}
	ver_count = len(releases)
	current_ver_int = 0

	for version, data in releases.items():
		current_ver_int += 1
		url = data["downloads"]["client"]["url"]
		sha1 = data["downloads"]["client"]["sha1"]

		dir_for_ver = f"{ver_dir}/{version}"
		file_path = f"{dir_for_ver}/{version}.jar"

		os.makedirs(dir_for_ver, mode=777, exist_ok=True)

		versions[version] = file_path

		need_download = True
		if os.path.exists(file_path): continue

		if need_download:
			print(f"Downloading versions: {str(round(current_ver_int/ver_count*100))}%"+" "*10, end="\r", flush=True)
			asyncio.run(download_file(url, file_path))

	q.put(versions)