from setuptools import setup, find_packages

setup(
	name='slampy',
	version='1.0.0',
	url='https://github.com/sci-visus/slampy',
	author='ViSUS',
	author_email='scrgiorgio@gmail.com',
	description='slampy',
	packages=find_packages(),
	install_requires=[
		'numpy', 
		'matplotlib',
		'pymap3d',
		'pytz',
		'pyzbar',
		'scikit-image',
		'scipy',
		'pysolar',
		'json-tricks',
		'cmapy',
		'tifffile',
		'pyexiftool',
		'opencv-python',
		'opencv-contrib-python'
	],
)