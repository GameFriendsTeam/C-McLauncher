import json
import os
from api.tools import get_filename_from_url, download_file, normalize_path
import multiprocessing as mp

def download_indexes(q: mp.Queue, indexes_dir: str, releases: dict[str, dict]) -> dict[str, str]:
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

		if os.path.exists(indexes_path):
			continue

		os.makedirs(indexes_dir, exist_ok=True)
		print(f"Downloading indexes: {str(round(current/count*100))}%"+" "*10, end="\r", flush=True)

		download_file(asset_url, indexes_path)

	q0 = mp.Queue()
	assets = download_assets(q0, indexes_dir+"/../objects", indexes)

	q.put((indexes, assets))

def download_assets(q: mp.Queue, assets_dir, downloaded):
	import concurrent.futures
	assets_dir = normalize_path(assets_dir)
	assets = {}
	count = len(downloaded)
	current = 0

	for name, path in downloaded.items():
		current += 1
		with open(path+"/"+name+".json") as f:
			data = json.load(f)
			objects = data["objects"]
			for obj_name, entry in objects.items():
				hash = entry["hash"]
				subdir = hash[0:2]

				file_path = assets_dir + "/" + subdir + "/" + hash
				assets[obj_name] = file_path

				need_download = True
				if os.path.exists(file_path):
					continue

				if need_download:
					obj_url = "https://resources.download.minecraft.net/" + subdir + "/" + hash
					os.makedirs(assets_dir + "/" + subdir, exist_ok=True)
					print(f"Downloading assets: {str(round(current/count*100))}%"+" "*10, end="\r", flush=True)
					download_file(obj_url, file_path)

			f.close()

	q.put(assets)