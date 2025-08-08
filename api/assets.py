import json
import os
from api.tools import get_filename_from_url, download_file, normalize_path
import multiprocessing as mp

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

		if os.path.exists(indexes_path):
			continue

		os.makedirs(indexes_dir, exist_ok=True)
		print(f"Downloading indexes: {str(round(current/count*100))}%"+" "*10, end="\r", flush=True)

		download_file(asset_url, indexes_path)

	q0 = mp.Queue()
	assets = download_assets(q0, indexes_dir+"/../objects", indexes)

	q.put((indexes, assets))

def download_assets(q, assets_dir, downloaded):
	import concurrent.futures
	assets_dir = normalize_path(assets_dir)
	assets = {}
	download_tasks = []
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
				obj_sha1 = hash
				need_download = True
				if os.path.exists(file_path):
					continue
				if need_download:
					obj_url = "https://resources.download.minecraft.net/" + subdir + "/" + hash
					os.makedirs(assets_dir + "/" + subdir, exist_ok=True)
					download_tasks.append((obj_url, file_path, current, count))

	def download_one(args):
		url, file_path, cur, total = args
		print(f"Downloading assets: {str(round(cur/total*100))}%"+" "*10, end="\r", flush=True)
		download_file(url, file_path)

	if download_tasks:
		with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
			list(executor.map(download_one, download_tasks))
	return assets