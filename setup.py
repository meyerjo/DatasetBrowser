import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.txt')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'hoedown',
    'matplotlib',
    'numpy',
    'pyramid',
    'pyramid_chameleon',
    'pyramid_debugtoolbar',
    'waitress',
    'python-Levenshtein',
    'jsonpickle',
    'pdfkit',
    'markdown'
]

extra_requires = {
    'matfiles_extractor': ['h5py', 'Cython']
}


setup(name='DatasetBrowser',
      version='0.0',
      description='DatasetBrowser',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='Johannes Meyer',
      author_email='',
      url='',
      keywords='web pyramid pylons',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      extras_require=extra_requires,
      tests_require=requires,
      test_suite="datasetbrowser",
      entry_points="""\
      [paste.app_factory]
      main = datasetbrowser:main
      """,
      )
