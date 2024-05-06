from setuptools import setup

with open("readME.md", "r") as f:
    description = f.read()

setup(
    name='django-activitylog-jwt',
    version='1.0.2',
    description='Get started with django-activitylog-jwt today to bolster the security and audit capabilities of your '
                'Django application while leveraging the power of JWT authentication.',
    author='Nand Kishore',
    author_email='knand4930@gmail.com',
    license='MIT',
    url='https://github.com/knand4930/django-activitylog-jwt.git',
    packages=['activitylog'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        'djangorestframework>=3.15.1',
        'djangorestframework-jwt>=1.11.0',
        'frozenlist>=1.4.1',
        'geoip2>=4.8.0',
        'idna>=3.7',
        'maxminddb>=2.6.1',
        'multidict>=6.0.5',
        'PyJWT>=1.7.1',
        'wheel>=0.43.0',
    ],
    long_description=description,
    long_description_content_type='text/markdown',
)
