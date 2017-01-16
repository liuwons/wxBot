from setuptools import setup


setup(
    name='wxbot',
    version='0.1.0',
    description='Wechat unofficial bot framework.',
    url='https://github.com/liuwons/wxBot',
    author='Weston Liu',
    author_email='a@lwons.com',
    license='Apache 2.0',
    classifiers=[],
    packages=['wxbot'],
    install_requires=[
        'jsonpickle',
        'Pillow',
        'pyqrcode',
        'pypng',
        'requests',
    ],
)
