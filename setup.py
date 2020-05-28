import os,sys,shutil,setuptools

PROJECT_NAME="slampy"
PROJECT_VERSION="1.0.1"

this_dir=os.path.dirname(os.path.abspath(__file__))

# /////////////////////////////////////////////////////////////
def FindFiles():
	# this are cached directories that should not be part of OpenVisus distribution
	shutil.rmtree('./build', ignore_errors=True)	
	shutil.rmtree('./dist', ignore_errors=True)	
	shutil.rmtree('./.git', ignore_errors=True)	
	shutil.rmtree('./{}.egg-info'.format(PROJECT_NAME), ignore_errors=True)	

	files=[]	
	for dirpath, __dirnames__, filenames in os.walk("."):
		for it in filenames:
			filename= os.path.abspath(os.path.join(dirpath, it))
			
			if "__pycache__" in filename: 
				continue
			
			if os.path.splitext(filename)[1] in [".ilk",".pdb",".pyc",".pyo"]: 
				continue
				
			files.append(filename)	
			
	return files

setuptools.setup(
	name=PROJECT_NAME,
	version=PROJECT_VERSION,
	url='https://github.com/sci-visus/slampy',
	author="visus.net",
	author_email="support@visus.net",
	description=PROJECT_NAME,
	packages=[PROJECT_NAME],
	package_dir={PROJECT_NAME:'.'},
	package_data={PROJECT_NAME: FindFiles()},
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