from setuptools import setup, find_packages

setup(
    name='goat-lso',
    version="0.1",
    author='GÉANT Orchestration & Automation Team',
    author_email='TBD',
    description='Lightweight Ansible Runner Provioner',
    url='https://gitlab.geant.org/goat/gap/lso',
    packages=find_packages(),
    install_requires=[
        'jsonschema',
        'fastapi',
        'pydantic',
        'ansible',
        'requests',
        'uvicorn',
        'ncclient',
        'xmltodict'
    ],
    license='MIT',
    license_files=('LICENSE.txt',),
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Development Status :: 2 - Pre-Alpha'
    ],
    python_requires='>=3.10'
)
