from setuptools import find_packages, setup

with open("readME.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="django-activitylog-jwt",
    version="2.0.0",
    description=(
        "Production-ready Django activity logging with async Celery processing, "
        "multi-database support (PostgreSQL, ClickHouse, MongoDB, ScyllaDB, MySQL), "
        "DRF APIs, real-time WebSocket/SSE streaming, RBAC, retention policies, "
        "tamper-proof integrity hashing, and JWT authentication."
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Nand Kishore",
    author_email="knand4930@gmail.com",
    license="MIT",
    url="https://github.com/knand4930/django-activitylog-jwt.git",
    packages=find_packages(exclude=["tests*"]),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: Django",
        "Framework :: Django :: 4.0",
        "Framework :: Django :: 4.1",
        "Framework :: Django :: 4.2",
        "Framework :: Django :: 5.0",
        "Framework :: Django :: 5.1",
        "Framework :: Django :: 5.2",
        "Framework :: Django :: 6.0",
        "Topic :: System :: Logging",
        "Topic :: Security",
    ],
    python_requires=">=3.8",
    # ------------------------------------------------------------------
    # Core (always required)
    # ------------------------------------------------------------------
    install_requires=[
        "Django>=4.0,<7.0",
        "djangorestframework>=3.15.0",
        "geoip2>=4.8.0",
        "maxminddb>=2.6.0",
    ],
    # ------------------------------------------------------------------
    # Optional feature groups
    # ------------------------------------------------------------------
    extras_require={
        # Async log processing
        "celery": [
            "celery>=5.3.0",
        ],
        # JWT auth (simplejwt preferred; legacy jwt also accepted)
        "jwt": [
            "djangorestframework-simplejwt>=5.3.1,<5.5; python_version < '3.9'",
            "djangorestframework-simplejwt>=5.5.1,<6.0; python_version >= '3.9'",
        ],
        # API filtering
        "filters": [
            "django-filter>=23.0",
        ],
        # Real-time WebSocket streaming
        "websocket": [
            "channels>=4.0.0",
            "channels-redis>=4.1.0",
        ],
        # ClickHouse analytics backend
        "clickhouse": [
            "clickhouse-driver>=0.2.7",
        ],
        # MongoDB backend
        "mongodb": [
            "pymongo>=4.6.0",
        ],
        # ScyllaDB / Cassandra backend
        "scylladb": [
            "cassandra-driver>=3.28.0",
        ],
        # Credential encryption (DatabaseConfig passwords)
        "encryption": [
            "cryptography>=42.0.0",
        ],
        # Excel export
        "excel": [
            "openpyxl>=3.1.0",
        ],
        # All optional features
        "all": [
            "celery>=5.3.0",
            "djangorestframework-simplejwt>=5.3.1,<5.5; python_version < '3.9'",
            "djangorestframework-simplejwt>=5.5.1,<6.0; python_version >= '3.9'",
            "django-filter>=23.0",
            "channels>=4.0.0",
            "channels-redis>=4.1.0",
            "clickhouse-driver>=0.2.7",
            "pymongo>=4.6.0",
            "cassandra-driver>=3.28.0",
            "cryptography>=42.0.0",
            "openpyxl>=3.1.0",
        ],
    },
)
