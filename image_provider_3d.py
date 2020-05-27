
from slampy.image_provider import *

# /////////////////////////////////////////////////////////////
class ImageProvider3d(ImageProvider):

	# constructor
	def __init__(self):
		super(ImageProvider3d,self).__init__()

		exts=('.jpg','.png','.tif','.bmp','.raw')
		all_images=[it for it in FindImages(image_extensions=exts) if not "~" in it and not "VisusSlamFiles" in it]
		Assert(all_images)

		# all_images=all_images[0:30]

		# i need a specs.txt file with the following content: <width> <height> <dtype>
		ext=os.path.splitext(all_images[0])[1]
		if ext==".raw":
			v=LoadTextDocument('specs.txt').split(" ")[0:3]
			self.width=int(v[0])
			self.height=int(v[1])
			self.dtype=v[2]
		else:
			img=ret=cv2.imread(filename,-1)
			self.height=img.shape[0]
			self.width=img.shape[1]
			self.dtype='%s[%d]' % (img.dtype,img.shape[2] if len(img.shape)>2 else 1,)

		print("ImageProvider3d",self.width,self.height,self.dtype)

		# guessing calibration (NOTE: calibration is not used at all, at least for now)
		fov=60.0
		f=self.width * (0.5 / math.tan(0.5* math.radians(fov)))
		cx,cy=self.width*0.5,self.height*0.5
		self.calibration=Calibration(f,cx,cy)

		for filename in all_images:
			self.addImage([filename])


	# generateImage
	def generateImage(self,img):

		filename=img.filenames[0]
		ext=os.path.splitext(filename)[1]

		# raw
		if ext==".raw":
			ret=ArrayUtils.loadImage(filename,["--dtype",self.dtype,"--dims","%d %d" % (self.width,self.height)])
			ret=ArrayUtils.interleave(ret)
			# ret=ArrayUtils.mirror(ret,0)
			# ret=ArrayUtils.mirror(ret,1)
			ret=Array.toNumPy(ret)
		# other images
		else:
			ret=cv2.imread(filename,-1) # -1 is IMREAD_UNCHANGED  
			Assert

		return ret
