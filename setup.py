from setuptools import setup, find_packages

setup(
    name="threads_poster",
    version="1.0.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "motor",
        "openai",
        "pytz",
        "python-dotenv",
    ],
    python_requires=">=3.8",
) 