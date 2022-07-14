from setuptools import setup, find_packages

requires = [
    'pyglet',
    'grpcio',
    'grpcio-tools',
    'numpy',
    ]

setup(
    name='ahriman',
    version='0.1',
    packages=find_packages(),
    description='Ahriman game client',
    author='Fran Marelli',
    package_data={
        # If any package contains *.txt or *.rst files, include them:
        '': ['*.txt', '*.rst', '*.md'],
        },
    classifiers=[
        'Programming Language :: Python :: 3.6',
        ],
    install_requires=requires,
    entry_points={
        'console_scripts': [
            'ahriman = ahriman:main',
            ],

        },
    )
