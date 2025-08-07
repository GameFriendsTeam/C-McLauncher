import json
import os
from api.tools import get_filename_from_url, download_file, file_sha1

def download_indexes(q, indexes_dir: str, releases: dict[str, dict]) -> dict[str, str]:
	indexes = {}

	count = len(releases)
	current = 0

	for version, data in releases.items():
		current += 1

		asset_url = data["assetIndex"]["url"]
		asset_filename = get_filename_from_url(asset_url)
		indexes_path = indexes_dir + "/" + asset_filename
		indexes[asset_filename.split(".json", 1)[0]] = indexes_dir
		asset_sha1 = data["assetIndex"].get("sha1")

		need_download = True
		if os.path.exists(indexes_path):
			if asset_sha1:
				try:
					if file_sha1(indexes_path) == asset_sha1:
						need_download = False
				except Exception:
					pass
			else:
				need_download = False

		if need_download:
			os.makedirs(indexes_dir, mode=777, exist_ok=True)
			print(f"Downloading indexes: {str(round(current/count*100))}%", end="\r", flush=True)
			download_file(asset_url, indexes_path)
			# Проверяем sha1 после скачивания
			if asset_sha1:
				try:
					if file_sha1(indexes_path) != asset_sha1:
						download_file(asset_url, indexes_path)
				except Exception:
					pass

	assets = download_assets(indexes_dir+"/../objects", indexes)

	q.put((indexes, assets))

def download_assets(objects_dir: str, indexes: dict[str, str]) -> dict[str, str]:
	assets = {}

	global_count = len(indexes)
	current_global = 0

	for name, path in indexes.items():
		current_global += 1

		with open(path+"/"+name+".json") as f:
			data = json.load(f)

			objects = data["objects"]

			local_count = len(objects)
			current_local = 0

			for obj_name, entry in objects.items():
				current_local += 1
				hash = entry["hash"]

				subdir = hash[0:2]
				file_path = objects_dir + "/" + subdir + "/" + hash

				assets[obj_name] = file_path
				obj_sha1 = hash
				need_download = True
				if os.path.exists(file_path):
					try:
						if file_sha1(file_path) == obj_sha1:
							need_download = False
					except Exception:
						pass

				if need_download:
					obj_url = "https://resources.download.minecraft.net/" + subdir + "/" + hash
					os.makedirs(objects_dir + "/" + subdir, mode=777, exist_ok=True)
					print(f"downloading assets: {str(round(current_local/local_count*100))}% | {str(round(current_global/global_count*100))}%   ", end="\r", flush=True)
					download_file(obj_url, file_path)
					# Проверяем sha1 после скачивания
					try:
						if file_sha1(file_path) != obj_sha1:
							download_file(obj_url, file_path)
					except Exception:
						pass

	return assets