"""Check for overlapping photos between ODIR and retina_dataset_2016.

The duplicate-checking logic will be added next.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ODIR_DIR = PROJECT_ROOT / "data/Internal/ODIR-5K/Training Images"
RETINA_DIR = PROJECT_ROOT / "data/External/retina_dataset_2016"


import hashlib

def file_md5(path):
    """ Calculate a file's MD5 fingerprint. """
    fingerprint = hashlib.md5()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            fingerprint.update(chunk)

    return fingerprint.hexdigest()     


def collect_hashes(folder):
    if not folder.is_dir():
        raise FileNotFoundError(f"Folder not found:{folder}")

    hashes = {}

    for path in sorted(folder.rglob("*")):
        if path.is_file():
            fingerprint = file_md5(path)
            hashes.setdefault(fingerprint, []).append(path)

    return hashes  

def main():
    odir_hashes = collect_hashes(ODIR_DIR)
    retina_hashes = collect_hashes(RETINA_DIR)  

    matches = odir_hashes.keys() & retina_hashes.keys()   

    print(f"Matching fingerprints:{len(matches)}")

    for fingerprint in sorted(matches):
        print("\nMatch found:") 
        print("ODIR:", odir_hashes[fingerprint])
        print("Retina:", retina_hashes[fingerprint])

if __name__ == "__main__":
    main()        
