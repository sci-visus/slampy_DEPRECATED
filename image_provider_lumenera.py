

import tifffile
import cv2

from OpenVisus.PyImage import *

from slampy.image_provider import *

# ///////////////////////////////////////////////////////////////////////////////////////////////
class ImageProviderLumenera(ImageProvider):
	
	#  constructor
	def __init__(self):
		super().__init__()
		
	# example: NIR_608.TIF  / RGB_608.TIF / Thermal_608.TIF returns 608
	# they are in different directories
	def getGroupId(self,filename):
		if not "RGB_" in filename: return ""  # only RGB right now
		filename=os.path.basename(filename)
		v=os.path.splitext(filename)[0].split("_")
		if len(v)<1 or not v[-1].isdigit(): return ""
		return v[-1]

	# generateImage
	def generateImage(self,img):
		multi = [numpy.array(tifffile.imread(filename)) for filename in img.filenames]
		multi = [ConvertImageToUint8(single) for single in multi] # TODO
		multi = self.mirrorY(multi)
		multi = self.swapRedAndBlue(multi)
		multi = self.undistortImage(multi)
		multi = self.alignImage(multi)
		return multi


# /////////////////////////////////////////////////////////////////////////////////////////////////////
def CreateInstance(metadata):
	exit_make =metadata["EXIF:Make"].lower()  if "EXIF:Make"  in metadata else ""
	exif_model=metadata["EXIF:Model"].lower() if "EXIF:Model" in metadata else ""
	if "lumenera" in exif_model or "lumenera" in exif_model:
		return ImageProviderLumenera()
	else:
		return None
