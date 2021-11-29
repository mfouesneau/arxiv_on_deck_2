from setuptools import setup, find_packages
from distutils.util import convert_path

def get_version(package_name: str):
    """ Returns the version from the code """
    version = {}
    version_file = convert_path(f'{package_name}/version.py')
    with open(version_file) as f:
        exec(f.read(), version)
    return version['version']

def readme():
    with open('README.md') as f:
        return f.read()

package_name = "arxiv_vanity_on_deck"

setup(name = package_name,
    version = get_version(package_name),
    description = "A tool for computing photometry from spectra",
    long_description = readme(),
    author = "Morgan Fouesneau",
    author_email = "",
    url = "https://github.com/mfouesneau/arxiv_vanity_on_deck",
    packages = find_packages(),
    package_data = {},
    include_package_data = True,
    classifiers=[
      'Intended Audience :: Science/Research',
      'Operating System :: OS Independent',
      'Programming Language :: Python :: 3',
      'License :: OSI Approved :: MIT License',
      'Topic :: Scientific/Engineering :: Astronomy'
      ],
    zip_safe=False,
    python_requires=">=3.6",
    install_requires=["beautifulsoup4",
            "TexSoup",
            "pdf2image",
	        "myst-parser",
    ]
)