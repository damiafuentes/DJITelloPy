import setuptools

with open("README.md", "r", encoding="utf-8") as fd:
    long_description = fd.read()

# replace relative urls to example files with absolute urls to the main git repo
repo_code_url = "https://github.com/damiafuentes/DJITelloPy/tree/master"
long_description = long_description.replace("](examples/", "]({}/examples/".format(repo_code_url))

setuptools.setup(
    name='djitellopy',
    packages=['djitellopy'],
    version='2.4.0',
    license='MIT',
    description='Tello drone library including support for video streaming, swarms, state packets and more',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Jakob Löw',
    author_email='djitellopy@m4gnus.de',
    url='https://github.com/damiafuentes/DJITelloPy',
    download_url='https://github.com/damiafuentes/DJITelloPy/archive/2.4.0.tar.gz',
    keywords=['tello', 'dji', 'drone', 'sdk', 'official sdk'],
    install_requires=[
        'numpy',
        'opencv-python',
    ],
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)
