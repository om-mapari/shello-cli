from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="bai-cli",
    version="1.0.0",
    author="Om Mapari",
    author_email="mapariom05@gmail.com",
    description="Shello CLI AI Assistant for Command Execution",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://app.gitlab.test.com/om.mapari/shello",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "python-dotenv>=1.0.0",
        "pydantic>=2.4.2",
        "rich>=13.6.0",
        "requests>=2.31.0",
        "urllib3>=2.0.7",
        "click>=8.0.0",
        "prompt_toolkit>=3.0.0",
        "keyring>=23.0.0",
        "pyperclip>=1.8.2",
    ],
    entry_points={
        "console_scripts": [
            "shello=cli:cli",
        ],
    },
)
