from setuptools import setup, find_packages
setup(
    name = "awsdns",
    version = "0.2",
    packages = find_packages('src'),
    package_dir = {'':'src'},
    install_requires = [
        "boto",
        "twisted",
        "tx-logging",
    ],
    entry_points = {
        'console_scripts': [
            'awsdns = awsdns:main'
        ],
    },
)
