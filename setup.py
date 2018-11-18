from distutils.core import setup

setup(
    name='djitellopy',  # How you named your package folder (MyLib)
    packages=['djitellopy'],  # Chose the same as "name"
    version='1.1',  # Start with a small number and increase it with every change you make
    license='MIT',  # Chose a license from here: https://help.github.com/articles/licensing-a-repository
    description='DJI Tello drone python interface using the official Tello SDK including the video stream.',
    # Give a short description about your library
    author='Damià Fuentes Escoté',  # Type in your name
    author_email='damiafuentes@hotmail.com',  # Type in your E-Mail
    url='https://github.com/damiafuentes',  # Provide either the link to your github or to your website
    download_url='https://github.com/damiafuentes/TelloSDKPy/archive/v_1.1.tar.gz',  # I explain this later on
    keywords=['tello', 'dji', 'drone', 'sdk', 'official sdk'],  # Keywords that define your package best
    install_requires=[  # I get to this in a second
        'numpy',
        'opencv-python',
        'pygame',
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
        'Intended Audience :: Developers',  # Define that your audience are developers
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',  # Again, pick a license
        'Programming Language :: Python :: 2.7',  # Specify which pyhton versions that you want to support
        'Programming Language :: Python :: 3',  # Specify which pyhton versions that you want to support
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
