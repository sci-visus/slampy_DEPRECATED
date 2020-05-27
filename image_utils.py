import os,sys,glob,threading,platform,sysconfig,re,time,subprocess, errno, fnmatch, shutil
import numpy,cv2

# ////////////////////////////////////////////////////////////////////////////////
def FindImages(template="./**/*.*",recursive=True,image_extensions=('.jpg','.png','.tif','.bmp')):
	
	ret=[]
	for filename in glob.glob(template,recursive=recursive):
		
		# look for extension, must be an image
		if image_extensions:
			ext=	os.path.splitext(filename)[1].lower()
			if not ext in image_extensions:
				continue
			
		ret.append(filename)
		
	return ret

# ////////////////////////////////////////////////////////////////////////////////
def MatrixToNumPy(value):
	ret=numpy.eye(3, 3, dtype=numpy.float32)
	for R in range(3):
		for C in range(3):
			ret[R,C]=value.getRow(R)[C]
	return ret

# //////////////////////////////////////////////
def InterleaveChannels(channels):
	
	first=channels[0]
		
	N=len(channels)		
	
	if N==1: 
		return first	
	
	ret=numpy.zeros(first.shape + (N,),dtype=first.dtype)
	
	# 2D arrays
	if len(first.shape)==2:
		for C in range(N):
			ret[:,:,C]=channels[C]
				
	# 3d arrays
	elif len(first.shape)==3:
		for C in range(N):
			ret[:,:,:,C]=channels[C]
		
	else:
		raise Exception("internal error")
	

	return ret 
	

# ////////////////////////////////////////////////////////////////////////////////
def ConvertImageToGrayScale(img):
	if len(img.shape)>=3 and img.shape[2]==3:
		return cv2.cvtColor(img[:,:,0:3], cv2.COLOR_RGB2GRAY)
	else:
		return img[:,:,0] 

# ////////////////////////////////////////////////////////////////////////////////
def ResizeImage(src,max_size):
	H,W=src.shape[0:2]
	vs=max_size/float(max([W,H]))
	if vs>=1.0: return src
	return cv2.resize(src, (int(vs*W),int(vs*H)), interpolation=cv2.INTER_CUBIC)
		
# ////////////////////////////////////////////////////////////////////////////////
def ComputeImageRange(src):
	if len(src.shape)<3:
		return (numpy.amin(src)),float(numpy.amax(src))
	return [ComputeImageRange(src[:,:,C]) for C in range(src.shape[2])]

					
# ////////////////////////////////////////////////////////////////////////////////
def ConvertImageToUint8(img):
	if img.dtype==numpy.uint8: return img
	return (NormalizeImage32f(img) * 255).astype('uint8')


# ////////////////////////////////////////////////////////////////////////////////
def SaveImage(filename,img):
	os.makedirs(os.path.dirname(filename), exist_ok=True)
	if os.path.isfile(filename):
		os.remove(filename)

	if len(img.shape)>3:
		raise Exception("cannot save 3d image")

	num_channels=img.shape[2] if len(img.shape)==3 else 1

	# opencv supports only grayscale, rgb and rgba
	if num_channels>3:
		img=img[:,:,0:3]
		num_channels=3

	# opencv does not support saving of 2 channel images
	if num_channels==2:
		R,G=img[:,:,0],img[:,:,1]
		B=numpy.zeros(R.shape,dtype=R.dtype)
		img=InterleaveChannels([R,G,B])

	cv2.imwrite(filename, img)

# ////////////////////////////////////////////////////////////////////////////////
def SaveUint8Image(filename,img):
	SaveImage(filename, ConvertImageToUint8(img))	

