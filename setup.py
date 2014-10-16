from setuptools import setup, find_packages

setup(
    name='desk',
    version=__import__('desk').__version__,
    license="BSD",

    # install_requires=[
    #     "django>=1.4.0",
    # ],

    description="desk, service data manager",
    #long_description=open('README.rst').read(),

    author='Yves Serrano',
    author_email='ys@taywa.ch',

    url='http://github.com/yvess/desk',
    download_url='http://github.com/yvess/desk/downloads',

    include_package_data=True,

    packages=find_packages(),

    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        #'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ]
)
