from setuptools import setup, find_packages

setup(
    name="threads_poster",
    version="1.1.8",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "motor",
        "openai",
        "pytz",
        "python-dotenv",
        "aiohttp",
        "asyncio",
        "tenacity",
        "colorlog",
        "pymongo",
    ],
    python_requires=">=3.10",
    author="ThreadsPoster Team",
    author_email="threadsposter@gmail.com",
    description="Threads 自動回覆與內容發布系統",
    license="MIT",
    url="https://github.com/chenweichiang/Luna-Threads-OpenAI-Post-system",
) 