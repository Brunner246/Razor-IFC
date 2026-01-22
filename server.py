import sys
import os
import uvicorn

src_path = os.path.join(os.path.dirname(__file__), "src")
sys.path.insert(0, src_path)

# Ensure subprocesses (ProcessPoolExecutor) can find the package on Windows
# This is crucial because 'spawn' does not inherit sys.path modifications
os.environ["PYTHONPATH"] = src_path + os.pathsep + os.environ.get("PYTHONPATH", "")

if __name__ == "__main__":
    uvicorn.run("ifc_splitter.presentation.api.main:app", host="localhost", port=8000, reload=True)
