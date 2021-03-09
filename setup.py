import os
import re
import sys
from shutil import rmtree
from setuptools import setup, find_packages, Command

current = os.path.abspath(os.path.dirname(__file__))
def parse_requirements(filename):
    """ load requirements from a pip requirements file """
    lineiter = (line.strip() for line in open(filename))
    return [line for line in lineiter if line and not line.startswith("#")]
install_reqs = parse_requirements(os.path.join(current, "requirements.txt"))
requirements = [str(r) for r in install_reqs]

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open(os.path.join(current, "tycho", "__init__.py"), encoding="utf8") as f:
    version = re.search(r'__version__="(.*?)"', f.read()).group(1)

class PublishClass(Command):
    description = "Publish the package"
    user_options = []

    # This method must be implemented
    def initialize_options(self):
        pass

    # This method must be implemented
    def finalize_options(self):
        pass

    def run(self):
        try:
            print(f"-----> removing previous builds")
            rmtree(os.path.join(current, 'dist'))
            rmtree(os.path.join(current, 'build'))
        except Exception as e:
            print(f"-----> Exception: {e}")
            pass
        os.system('python setup.py sdist bdist_wheel --universal')
        os.system('twine upload dist/*')
        sys.exit()

setup(
    name="tycho-api",
    version=version,
    maintainer="Renci",
    maintainer_email="muralikarthik.k@renci.org",
    description="Tycho is an API, compiler, and executor for cloud native distributed systems.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/helxplatform/tycho.git",
    packages=['tycho', 'tycho.conf', 'tycho.sample', 'tycho.template', 'tycho.test'],
    package_data={'tycho':['*.yaml'],
                  'tycho.conf': ['*.yaml'],
                  'tycho.template': ['*.yaml'],
                  'tycho.test.templates': ['*.yaml']},
    include_package_data=True,
    entry_points={"console_scripts": ["tycho=tycho.api:main"]},
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    cmdclass={
        'publish': PublishClass,
    },
)
