import json
import os
from api.tools import get_filename_from_url, download_file, file_sha1, normalize_path
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

	q0 = mp.Queue()
	assets = download_assets(q0, indexes_dir+"/../objects", indexes)

	q.put((indexes, assets))

def download_assets(q, assets_dir, downloaded):
	assets_dir = normalize_path(assets_dir)
	"""
	Параллельная загрузка ассетов с помощью ThreadPoolExecutor.
	"""
	import concurrent.futures
	from api.tools import file_sha1, lazy_download_file
	assets = {}
	assets_to_download = []
	# Собираем все объекты для скачивания
	for name, path in downloaded.items():
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
					try:
						if file_sha1(file_path) == obj_sha1:
							need_download = False
					except Exception:
						pass
				if need_download:
					obj_url = "https://resources.download.minecraft.net/" + subdir + "/" + hash
					os.makedirs(assets_dir + "/" + subdir, mode=777, exist_ok=True)
					assets_to_download.append((obj_url, file_path, obj_sha1))

	def download_one(args):
		url, path, sha1 = args
		try:
			lazy_download_file(url, path)
			# Проверяем sha1 после скачивания
			from api.tools import file_sha1 as check_sha1
			if check_sha1(path) != sha1:
				lazy_download_file(url, path)
		except Exception as e:
			print(f"Ошибка при скачивании {url}: {e}")

	if assets_to_download:
		with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
			list(executor.map(download_one, assets_to_download))
	return assets