import fnmatch
import os


def find_files(root, patterns):
    matches = []
    for dirpath, _, files in os.walk(root):
        for name in files:
            for pattern in patterns:
                if fnmatch.fnmatch(name, pattern):
                    matches.append(os.path.join(dirpath, name))
    return matches
