import subprocess
import httpx
from api.tools import download_file
from loguru import logger

def download_fabric(q, game_dir, version):
	pass

def download_forge(q, game_dir, version):
	forge_version_full = get_latest_forge_for(version)

	installer_filename = f"forge={forge_version_full}-installer.jar"
	url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{forge_version_full}/{installer_filename}"

	installer_path = game_dir / "fi" / installer_filename

	try:
		download_file(url, str(installer_path), logger)

		subprocess.run(["java", "-jar", installer_path, "--installClient"], check=True, swd=game_dir)

		installer_path.unlink()
	except Exception as e:
		raise e

def get_latest_forge_for(version):
	try:
		manifest_url = ""
		response = httpx.get(manifest_url)
		response.raise_for_status()
		data = response.json()

		if not version in data:
			raise ValueError(f"Version {version} not found")
		
		latest = data[version].get("recommended")
		if latest:
			return f"{version}-{latest}"
		
		available = data[version].get("available")

		if available:
			return f"{version}-{available}"
		
		raise ValueError(f"Not found available forge version")

	except Exception as e:
		raise e