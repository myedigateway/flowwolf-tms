from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in flowwolf_tms/__init__.py
from flowwolf_tms import __version__ as version

setup(
	name="flowwolf_tms",
	version=version,
	description="Transport Management System",
	author="Flowwolf Inc.",
	author_email="anupam@flowwolf.io",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
