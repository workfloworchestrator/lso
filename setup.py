from setuptools import setup, find_packages

setup(
    name='goat-larp',
    version='0.0.1',
    author='GÉANT Orchestration & Automation Team',
    author_email='TBD',
    description='Lightweight Ansible Runner Provioner',
    url='https://gitlab.geant.org/goat/gap/larp',
    packages=find_packages(),
    install_requires=[
        'jsonschema',
        'requests',
    ]
)
