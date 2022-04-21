import re
from os import path
from pathlib import Path

from jupyter_packaging import get_data_files, npm_builder, wrap_installers
from setuptools import find_packages, setup

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

with open(path.join(this_directory, "itables/version.py")) as f:
    version_file = f.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    version = version_match.group(1)

setup_args = dict(
    name="itables",
    version=version,
    author="Marc Wouts",
    author_email="marc.wouts@gmail.com",
    description="Interactive Tables in Jupyter",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mwouts/itables",
    packages=find_packages(exclude=["tests"]),
    package_data={
        "itables": ["require_config.js", "datatables_template.html", "samples/*.csv"]
    },
    tests_require=["pytest"],
    install_requires=["IPython", "pandas"],
    license="MIT",
    zip_safe=False,
    include_package_data=True,
    python_requires=">=3.6",
    platforms="Linux, Mac OS X, Windows",
    keywords=["Jupyter", "JupyterLab", "JupyterLab3"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Framework :: Jupyter",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)

HERE = Path(__file__).parent.resolve()

lab_path = HERE / "itables" / "labextension"

# Representative files that should exist after a successful build
ensured_targets = [str(lab_path / "package.json"), str(lab_path / "static/style.js")]

labext_name = "jupyterlab-itables"

data_files_spec = [
    (
        "share/jupyter/labextensions/%s" % labext_name,
        "labextension",
        "**",
    ),
    ("share/jupyter/labextensions/%s" % labext_name, ".", "install.json"),
]


post_develop = npm_builder(
    build_cmd="install:extension", source_dir="src", build_dir=lab_path
)
setup_args["cmdclass"] = wrap_installers(
    post_develop=post_develop, ensured_targets=ensured_targets
)
setup_args["data_files"] = get_data_files(data_files_spec)

if __name__ == "__main__":
    setup(**setup_args)
