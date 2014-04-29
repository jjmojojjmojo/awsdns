from setuptools import setup, find_packages
setup(
    name = "awsdns",
    version = "0.1",
    packages = find_packages('src'),
    package_dir = {'':'src'},
    install_requires = [
        "boto",
        "twisted"
    ],
    entry_points = {
        'console_scripts': [
            'awsdns = awsdns:main'
        ],
    },
)
