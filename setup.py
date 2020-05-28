import sys,os,setuptools

def FindFiles():
	ret=[]	
	for dirpath, __dirnames__, filenames in os.walk("."):
		for it in filenames:
			ret.append(os.path.abspath(os.path.join(dirpath, it)))	
	return ret

setuptools.setup(
	name='slampy',
	version='1.0.1',
	url='https://github.com/sci-visus/slampy',
	author="visus.net",
	author_email="support@visus.net",
	description='slampy',
	packages=['slampy'],
	package_dir={'slampy':'.'},
	package_data={'slampy': FindFiles()},
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