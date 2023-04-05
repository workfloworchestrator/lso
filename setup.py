from setuptools import setup, find_packages

setup(
    name='goat-ansible-api',
    version='0.0.1',
    author='GÉANT Orchestration & Automation Team',
    author_email='TBD',
    description='GOAT Ansible API',
    url='https://gitlab.geant.org/goat/gap/ansible-api',
    packages=find_packages(),
    install_requires=[
        'jsonschema',
        'requests',
    ]
)
