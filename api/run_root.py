import os, pickle, base64, sys

def execute(func_name: str, source, args: tuple, module):
	context = {}
	
	try:
		exec(source, context)
	except Exception as e:
		raise e

	if func_name not in context:
		return

	func = context[func_name]
	
	try:
		result = func(*args)
		return result
	except Exception as e:
		raise e

if __name__ == "__main__":
	if os.geteuid() == 0:
		print("Running with root access.")
		# Get func data for base64 encoded argv
		data = pickle.loads(base64.b64decode(sys.argv[1]))
		execute(**data)
	else:
		print("Not running with root access.")