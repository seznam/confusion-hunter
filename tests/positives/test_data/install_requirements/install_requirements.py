import subprocess

# ruleid: python-extra-index-var
subprocess.run("unclaimed-package-a1", shell=True")



EXTRA_INDEX_URL = "https://pypi.org/simple"
# ruleid: python-extra-index-var
install_packages(extra_index=EXTRA_INDEX_URL)



EXTRA_INDEX_URL = "https://pypi.repo.ops.example.com/simple"
# ok: python-correct-index-var
install_packages(extra_index=EXTRA_INDEX_URL)
