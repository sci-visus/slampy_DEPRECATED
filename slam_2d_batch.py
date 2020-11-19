import os, sys, argparse, datetime

from slampy.slam_2d import Slam2D

from slampy.gui_utils import *
from slampy.extract_keypoints import *
from slampy.google_maps       import *
from slampy.gps_utils         import *
from slampy.find_matches      import *
from slampy.gui_utils         import *
from slampy.image_provider    import *
from slampy.image_utils       import *

# //////////////////////////////////////////////////////////////////////////////////////////////
class Slam2DBatch:

	# constructor
	def __init__(self, color_matching=False):
		self.image_dir=""
		self.cache_dir=""
		self.color_matching=color_matching

	# generateImage
	def generateImage(self,img):
		t1=Time.now()
		print("Generating image",img.filenames[0])	
		ret = InterleaveChannels(self.provider.generateImage(img))
		print("done",img.id,"range",ComputeImageRange(ret),"shape",ret.shape, "dtype",ret.dtype,"in",t1.elapsedMsec(),"msec")
		return ret

	# setImageDirectory
	def setImageDirectory(self, image_dir, cache_dir=None):
		
		if not cache_dir:
			cache_dir=os.path.abspath(os.path.join(image_dir,"./VisusSlamFiles"))

		# avoid recursions
		if self.image_dir==image_dir:
			return
			
		assert(os.path.isdir(image_dir))
		self.image_dir=image_dir
		self.cache_dir=cache_dir
		os.makedirs(self.cache_dir,exist_ok=True)
		self.provider=CreateProvider(self.image_dir, self.cache_dir)
		
		TryRemoveFiles(self.cache_dir+'/~*')

		full=self.generateImage(self.provider.images[0])
		array=Array.fromNumPy(full,TargetDim=2)
		width  = array.getWidth()
		height = array.getHeight()
		dtype  = array.dtype

		self.slam=Slam2D(width,height,dtype, self.provider.calibration,self.cache_dir,color_matching=self.color_matching)
		self.slam.debug_mode=False
		self.slam.generateImage=self.generateImage

		for img in self.provider.images:
			camera=self.slam.addCamera(img)
			self.slam.createIdx(camera)

		self.slam.initialSetup()

	# run
	def run(self):
		self.slam.run()

# ////////////////////////////////////////////////
def Main(args):

	parser = argparse.ArgumentParser(description="slam command.")
	parser.add_argument("--directory", "-d", type=str, help="Directory of the dataset.", required=True,default="")
	args = parser.parse_args(args[1:])		
	
	print("Running slam","arguments", repr(args))

	# since I'm writing data serially I can disable locks
	os.environ["VISUS_DISABLE_WRITE_LOCK"]="1"

	batch = Slam2DBatch(color_matching=True)
	batch.setImageDirectory(args.directory)
	batch.run()
	
	print("All done")
	sys.exit(0)	


# //////////////////////////////////////////
if __name__ == "__main__":
	Main(sys.argv)