import json
import os
from pathlib import Path
from api.tools import get_filename_from_url, download_file, normalize_path
import multiprocessing as mp
import asyncio

def download_indexes(q: mp.Queue, indexes_dir: str, releases: dict[str, dict]) -> dict[str, str]:
	indexes = {}

	count = len(releases)
	current = 0

	if not os.path.exists(indexes_dir): os.makedirs(indexes_dir, exist_ok=True)

	for version, data in releases.items():
		current += 1

		asset_index = data["assetIndex"]
		asset_url = asset_index["url"]
		asset_filename = asset_index["id"]+".json"

		index_path = indexes_dir + "/" + asset_filename

		indexes[asset_filename] = indexes_dir
		if os.path.exists(index_path):
			continue

		print(f"Download assets stage 1/2: {str(round(current/count*100))}%"+" "*10, end="\r", flush=True)

		asyncio.run(download_file(asset_url, index_path))
		print(f"Downloaded {index_path}")

	assets = download_assets(str(Path(indexes_dir+"/../objects")), indexes)

	q.put((indexes, assets))
	return

def download_assets(assets_dir, downloaded):
	assets_dir = normalize_path(assets_dir)
	assets = {}
	count = len(downloaded)
	current = 0

	for name, path in downloaded.items():
		current += 1
		with open(normalize_path(path+"/"+name)) as f:
			data = json.load(f)
			objects = data["objects"]
			for obj_name, entry in objects.items():
				hash = entry["hash"]
				subdir = hash[0:2]
				file_path = normalize_path(assets_dir + "/" + subdir + "/" + hash)

				assets[obj_name] = file_path
				if os.path.exists(file_path):
					continue

				obj_url = "https://resources.download.minecraft.net/" + subdir + "/" + hash
				os.makedirs(assets_dir + "/" + subdir, exist_ok=True)
				print(f"Download assets stage 2/2: {str(round(current/count*100))}%"+" "*10, end="\r", flush=True)
				asyncio.run(download_file(obj_url, file_path))
				print(f"Downloaded {obj_name}")

			f.close()

	return assets