from setuptools import find_packages, setup

setup(
    name="goat-lso",
    version="0.21",
    author="GÉANT Orchestration & Automation Team",
    author_email="goat@geant.org",
    description="Lightweight Service Orchestrator",
    url="https://gitlab.software.geant.org/goat/gap/lso",
    packages=find_packages(),
    install_requires=[
        "ansible_merge_vars~=5.0.0",
        "ansible-runner~=2.3.4",
        "ansible~=8.6.1",
        "dictdiffer~=0.9.0",
        "fastapi~=0.104.1",
        "GitPython~=3.1.40",
        "httpx~=0.25.1",
        "jinja2==3.1.2",
        "jmespath~=1.0.1",
        "jsonschema~=4.20.0",
        "junos-eznc~=2.6.8",
        "jxmlease~=1.0.3",
        "ncclient~=0.6.13",
        "netaddr~=0.8.0",
        "pydantic~=2.0.3",
        "requests~=2.31.0",
        "ruamel.yaml~=0.18.5",
        "uvicorn[standard]~=0.22.0",
        "xmltodict~=0.13.0",
    ],
    license="MIT",
    license_files=("LICENSE.txt",),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Framework :: FastAPI",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Telecommunications Industry",
    ],
)
