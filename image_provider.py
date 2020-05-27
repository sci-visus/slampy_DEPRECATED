import time
import pickle
import numpy
import cv2
import statistics
import math
import json
import datetime
import importlib

from OpenVisus                   import *
from OpenVisus.PyImage           import *

from slampy.multi_sensor_alignment   import *
from slampy.google_maps              import *
from slampy.gps_utils                import *
from slampy.metadata_reader          import *

# ///////////////////////////////////////////////////////////////////
class PythonSlamImage:

	# constructor
	def __init__(self,id=0,filenames=[],metadata={}):
		self.id=id
		self.filenames=filenames
		self.metadata=metadata
		self.lon=0.0
		self.lat=0.0
		self.alt=0.0
		self.yaw=None

# //////////////////////////////////////////////////////////////////////////////
class ImageProvider:

	# constructor
	def __init__(self):
		self.progress_bar=None
		self.width=0
		self.height=0
		self.dtype=""	
		self.calibration=Calibration()
		self.images=[]
		self.panels=[]
		self.fixed_focal_lenght=False
		self.fixed_central_point=False
		self.multi_sensor_alignment=None
		self.xmap=None
		self.ymap=None

		# the offset for all yaws in respect to the north pole
		# in radians
		# 0 means north
		# +math.pi/2 means east
		# -math.pi/2 means west
		# math.pi==-math.pi means south
		self.camera_yaw=0.0

	# startAction
	def startAction(self,N,message):
		if self.progress_bar:
			self.progress_bar.setRange(0,N)
			self.progress_bar.setMessage(message)
			self.progress_bar.setValue(0)
			self.progress_bar.show()

	# advanceAction			
	def advanceAction(self,I):
		if self.progress_bar:
			self.progress_bar.setValue(I)
	
	# endAction
	def endAction(self):
		if self.progress_bar:
			self.progress_bar.hide()

	# findGroups
	# example: IMG_0000_1.tif  / IMG_0000_2.tif / IMG_0000_3.tif / IMG_0000_4.tif / IMG_0000_5.tif
	def findGroups(self, all_images):
		groups={}
		for filename in sorted(all_images):
			GroupId=self.getGroupId(filename)


			if GroupId=="":  
				continue

			if not GroupId in groups: 
				groups[GroupId]=[]

			groups[GroupId].append(filename)
		ordered=[]
		for key in sorted(groups.keys()):
			ordered.append(groups[key])
		groups=ordered
		return groups

	# loadMetadata
	def loadMetadata(self,ncomponent=0):

		cached_filename=self.cache_dir+"/metadata"

		try:
			cached_metadata=pickle.load(open(cached_filename,"rb"))	
		except :
			cached_metadata={}
	
		reader=MetadataReader()
		N=len(self.images)

		self.startAction(N,'Reading Metadata, please wait')

		for I,img in enumerate(self.images):
			filename=img.filenames[ncomponent]
			img.metadata=cached_metadata[filename] if filename in cached_metadata else reader.readMetadata(filename)
			self.advanceAction(I)
			time.sleep(0.00001)

		self.endAction()
		print("Finished")	

		reader.close()			
		
		# save metadata
		cached_metadata={}
		for img in self.images:
			filename=img.filenames[ncomponent]
			cached_metadata[filename]=img.metadata
		os.makedirs(os.path.dirname(cached_filename),exist_ok=True)
		pickle.dump(cached_metadata, open(cached_filename,"wb"))	

	# findMetadata
	def findMetadata(self,img, names, prefixes=["Telemetry:", "SensorConfig:", "Composite:", "EXIF:", "XMP:"]):
		for name in names:
			for prefix in prefixes:
				full_key=prefix+name
				if full_key in img.metadata:
					return full_key
		return None

	# loadSensorCfg
	def loadSensorCfg(self,sensor_filename="sensor.cfg"):

		content=LoadTextDocument(sensor_filename)
		if not content:
			print("no sensor config")
			return False

		print("Using",sensor_filename)
		lines=[line.strip() for line in content.splitlines() if len(line.strip())]
		for line in lines:
			if line[0]=="#": continue # comment
			key,value=[it.strip() for it in line.split(" ",2)]
			for img in self.images:
				img.metadata["SensorCfg:"+key]=value	

	# loadTelemetry
	def loadTelemetry(self,ncomponent=0,tememetry_filename="telemetry.dat"):

		content=LoadTextDocument(tememetry_filename)
		if not content:
			print("no telemetry")
			return False

		print("Using",tememetry_filename)
		lines=[line.strip() for line in content.splitlines() if len(line.strip())]

		records={}
		for L,line in enumerate(lines[1:]):
			values=[it.strip() for it in line.split("\t") if len(it.strip())]

			if L==0:
				names=values
				print("names",names)
				continue

			key=values[0]
			record={}
			for name,value in zip(names,values): 
				record[name]=value
			records[key]=record
			print("Telemetry new record","key",key,record)
				
		for img in self.images:
			key=os.path.basename(img.filenames[ncomponent])
			if key in records:
				lat=ParseDouble(records[key]["lat"])
				lon=ParseDouble(records[key]["lon"])
				alt=ParseDouble(records[key]["alt"])
				yaw=ParseDouble(records[key]["yaw(gps)"])
				img.metadata["Telemetry:GPSLatitude" ]=lat
				img.metadata["Telemetry:GPSLongitude"]=lon
				img.metadata["Telemetry:GPSAltitude" ]=alt	
				img.metadata["Telemetry:Yaw"         ]=yaw	


	# findPanels
	def findPanels(self):
		pass
		
	# printMetadata
	def printMetadata(self,img):
		print("image has the following metadata")
		for key,value in img.metadata.items():
			print("\t",key,"=",value)

	# guessGPS
	def guessGPS(self):

		print("Extracting GPS")

		LAT=self.findMetadata(self.images[0], ["GPSLatitude" ,"Latitude" ]) 
		LON=self.findMetadata(self.images[0], ["GPSLongitude","Longitude"]) 
		ALT=self.findMetadata(self.images[0], ["GPSAltitude" ,"Altitude" ])

		if LAT is None: raise Exception("missing latitude  from metadata")
		if LON is None: raise Exception("missing longitude from metadata")
		if ALT is None: raise Exception("missing altitude  from metadata")

		print("Using GPS",LAT,LON,ALT)
		for img in self.images:
			try:
				img.lat=ParseDouble(img.metadata[LAT])
				img.lon=ParseDouble(img.metadata[LON])
				img.alt=ParseDouble(img.metadata[ALT])
				print("image",img.filenames[0],"lat",img.lat,"lon",img.lon,"alt",img.alt)
			except:
				print("WARNING","image",img.filenames[0],"does not have",LAT,LON,ALT)

		# interpolating (could happen for some images)
		N=len(self.images)
		for I,img in enumerate(self.images):

			def wrong(img):
				return img.lat==0.0 or img.lon==0.0 or img.alt==0.0
			
			if not wrong(self.images[I]):
			  continue

			A,B=I-1,I+1
			while A>=0 and wrong(self.images[A]): A-=1
			while B<N  and wrong(self.images[B]): B+=1
			if 0<=A and A<B and B<N: 
				alpha=(I-A)/float(B-A)
				img.lat=(1-alpha)*self.images[A].lat + alpha*self.images[B].lat
				img.lon=(1-alpha)*self.images[A].lon + alpha*self.images[B].lon
				img.alt=(1-alpha)*self.images[A].alt + alpha*self.images[B].alt	
				print("WARNING","interpolating GPS",img.filenames[0],"lat",img.lat,"lon",img.lon,"alt",img.alt)
			else:
				raise Exception("cannot interpolate GPS for",img.filenames[0])

		return True

	# guessYaw
	def guessYaw(self):

		img=self.images[0]
		YAW=self.findMetadata(img,["Yaw","GimbalYaw","GimbalYawDegree"])

		if YAW:
			print("using metadata yaw",YAW)
		else:
			print("Guessing yaw from flight direction")

		for I,img in enumerate(self.images):

			if YAW is not None:

				if YAW in img.metadata:
					img.yaw=ParseDouble(img.metadata[YAW])
					print(img.filenames[0], YAW,img.yaw)
				else:
					img.yaw=self.images[I-1].yaw
					print(img.filenames[0], "missing",YAW,"using last one",img.yaw)
			else:

				def computeDir(img1,img2):
					x1,y1=GPSUtils.gpsToLocalCartesian(img1.lat, img1.lon,self.images[0].lat,self.images[0].lon)
					x2,y2=GPSUtils.gpsToLocalCartesian(img2.lat, img2.lon,self.images[0].lat,self.images[0].lon)
					dir = Point3d(x2,y2,img2.alt) - Point3d(x1,y1,img1.alt)
					dir.z=0
					dir=dir.normalized()
					X,Y,Z = Point3d(1, 0, 0),Point3d(0, 1, 0),Point3d(0, 0, 1)
					return -math.atan2((Y.cross(dir)).dot(Z), dir.dot(Y))

				yaws=[]
				if I>0:                  yaws.append(computeDir(self.images[I-1],img))
				if I<len(self.images)-1: yaws.append(computeDir(img,self.images[I+1]))
				img.yaw=sum(yaws) / len(yaws) 
				print(img.filenames[0], "yaw from flight direction",img.yaw)

		# forcing radians (i don;t know if in metadata are degrees or radiant)
		if YAW:

			m=min([img.yaw for img in self.images])
			M=max([img.yaw for img in self.images])

			if "radians" in YAW.lower():
				print("Yaws are in radians")

			elif "degrees" in YAW.lower():
				print("Yaws are in degres, converting them to radians")
				for img in self.images: 
					img.yaw=math.radians(img.yaw)

			elif m<-2*math.pi or M>+2*math.pi:
				print("Yaws are in range", m, M, "and I'm guessing them to be in degrees, forcing to radians")
				for img in self.images: 
					img.yaw=math.radians(img.yaw)

			else:
				print("Yaws are in range",m, M, "and I'm guessing them to be in radians")

		print("Normalizing and adding camera_yaws",self.camera_yaw)
		for img in self.images:
			img.yaw=self.camera_yaw+img.yaw
			while img.yaw > +math.pi: img.yaw-=2*math.pi
			while img.yaw < -math.pi: img.yaw+=2*math.pi
			print(img.filenames[0], "yaw_radians",img.yaw, "yaw_degrees",math.degrees(img.yaw))

	# setPlane
	def setPlane(self,value):
		print("Setting plane to",value)
		good=[]
		for I,img in enumerate(self.images):
			old_alt=img.alt
			img.alt-=value	
			print("\t",img.filenames[0],"GPS Corrected","Altitude",old_alt,"to ",img.alt)
			if img.alt<1.0: 
				print("dropping",img.filenames[0], "because too low")
			else:
				good.append(img)

		self.images=good

	# guessPlane
	def guessPlane(self):

		img=self.images[0]

		# could be I have some images on the floor (i.e. panels)
		if len(self.panels):
			ALT=self.findMetadata(img,["GPSAltitude"])
			if ALT:
				value=min([ParseDouble(image.metadata[ALT]) for image in self.panels])
				print("Guessing plane",value,"from panels")
				return self.setPlane(value)
				 
		# guess for absolute/relative altitude
		ABS=self.findMetadata(img,["AbsoluteAltitude"])
		REL=self.findMetadata(img,["RelativeAltitude"])
		if ABS and REL:
			elevations=[ParseDouble(image.metadata[ABS])-ParseDouble(image.metadata[REL]) for image in self.images]
			value=statistics.median(elevations)
			print("Guessing plane",value, ABS, REL)
			return self.setPlane(value)
			 
		# check if exists a plane.txt File
		plane_filename=self.cache_dir+"/plane.txt"
		plane_content=LoadTextDocument(plane_filename)
		if plane_content:
			value=ParseDouble(plane_content)
			print("Loading plane",value," from plane_filename",plane_filename)
			return self.setPlane(value)
			 
		# use google api
		if True:
			lats=[image.lat for image in self.images]
			lons=[image.lon for image in self.images]
			elevations=GoogleGetTerrainElevations(lats,lons)
			
			# can just fail because no token
			if elevations:
				value=statistics.median(elevations)
				print("Guessing plane",value,"from google maps API")
				SaveTextDocument(plane_filename,str(value))
				return self.setPlane(value)

		# pretend the field is at 0 meter from sea level
		if True:
			value=0.0
			print("Guessing plane",value,"zero sea level as last resort")
			return self.setPlane(value)
			 
	# guessUnitScale
	def guessUnitScale(self, img, names):
		UNIT=self.findMetadata(img, names)
		if UNIT:  
			unit=img.metadata[UNIT]

			 #1 = None  2 = inches  3 = cm  4 = mm  5 = um
			if isinstance(unit,int) or (isinstance(unit,str) and unit.isdigit()):
				return {2: 25.400, 3: 10.000, 4:  1.000, 5: 0.001}[int(unit)]
			else:
				return {"inches": 25.400,"cm": 10.000,"mm": 1.000, "um":0.001}[str(unit)]

		return 1.0

	# guessFocalLength
	def guessFocalLength(self):
		print("Guessing focal length...")
		img=self.images[0]

		FOC=self.findMetadata(img,["FocalLength", "PerspectiveFocalLength"])
		if FOC: 
			foc=ParseDouble(img.metadata[FOC])
			scale = self.guessUnitScale(img, ['FocalLengthUnits','PerspectiveFocalLengthUnits'])
			ret=foc * scale
			print("focal length", ret, FOC, foc, "scale", scale)
			return ret

		return 0.0

	# guessSensorSizeLat
	def guessSensorSizeLat(self, ImageWidth):

		print("Guessing sensor size lat")
		img=self.images[0]

		SIZE=self.findMetadata(img,["SensorSizeLat"])
		if SIZE:
			size=ParseDouble(img.metadata[SIZE])
			ret=size
			print("sensor size lat", ret, SIZE, size)
			return ret

		PITCH=self.findMetadata(img,["PixelPitch"])
		if PITCH:
			pitch=ParseDouble(img.metadata[PITCH])
			ret=ImageWidth * pitch  * 0.001 # um to mm
			print("sensor size lat", ret, PITCH, pitch)
			return ret

		RES=self.findMetadata(img,["FocalPlaneXResolution", "PerspectiveFocalPlaneXResolution"])
		if RES:
			res= ParseDouble(img.metadata[RES]) 
			scale = self.guessUnitScale(img, ['FocalPlaneResolutionUnit','PerspectiveFocalPlaneResolutionUnit'])
			ret=ImageWidth / (res *scale)
			print("sensor size lat", ret,RES, res, "scale",scale)
			return ret
		
		return 0.0

	# guessSensorSizeLon
	def guessSensorSizeLon(self, ImageHeight):

		print("Guessing sensor size lon")
		img=self.images[0]

		SIZE=self.findMetadata(img,["SensorSizeLon"])
		if SIZE:
			size=ParseDouble(img.metadata[SIZE])
			ret=slon
			print("sensor size lon is", ret, SIZE, size)
			return ret

		PITCH=self.findMetadata(img,["PixelPitch"])
		if PITCH:
			pitch=ParseDouble(img.metadata[PITCH]) 
			ret=ImageHeight * pitch * 0.001 # um to mm
			print("sensor size lon is", ret, PITCH, pitch)
			return ret

		RES=self.findMetadata(img,["FocalPlaneYResolution", "PerspectiveFocalPlaneYResolution"])
		if RES:
			res  = ParseDouble(img.metadata[RES]) 
			scale = self.guessUnitScale(img, ['FocalPlaneResolutionUnit','PerspectiveFocalPlaneResolutionUnit'])
			ret = ImageHeight / (res * scale)
			print("sensor size lon is", ret, RES, res, "scale",scale)
			return ret
		
		return 0.0


	# guessCalibrationFocal
	def guessCalibrationFocal(self,ImageWidth,ImageHeight):

		print("Guessing calibration focal...")
		img=self.images[0]

		CAL=self.findMetadata(img,['CalibratedFocalLength','PerspectiveCalibratedFocalLength'])
		if CAL:
			cal=ParseDouble(img.metadata[CAL])
			ret=cal
			self.fixed_focal_lenght=True
			print("Calibration focal (f1)", ret, CAL, cal)
			return ret

		FocalLength   = self.guessFocalLength()
		SensorSizeLat = self.guessSensorSizeLat(ImageWidth)
		if FocalLength!=0 and SensorSizeLat!=0:
			ret =  FocalLength * (ImageWidth / SensorSizeLat) 
			print("Calibration focal (f2)",ret, "FocalLength", FocalLength, "SensorSizeLat", SensorSizeLat)
			return ret

		FOV=self.findMetadata(img,["FOV", "Fov", "SensorFOV", "SensorFov"])
		if FOV:
			fov=ParseDouble(img.metadata[FOV])
			ret=ImageWidth * (0.5 / math.tan(0.5* math.radians(fov)))
			print("Calibration focal (f3)",ret, FOV, fov)
			return ret

		# last resort, use a default_fov (more or less the range is [0.8*ImageWidth 1.3*ImageWidth])
		if True:
			DEFAULT_FOV=60 #0.86 * ImageWidth
			ret=ImageWidth * (0.5 / math.tan(0.5* math.radians(DEFAULT_FOV)))
			print("Calibration focal (f4)", ret, "DEFAULT_FOV", DEFAULT_FOV)
			return ret

	# guessCalibrationCentralPoint
	def guessCalibrationCentralPoint(self,ImageWidth,ImageHeight):

		img=self.images[0]

		CX=self.findMetadata(img,['CalibratedOpticalCenterX'])
		CY=self.findMetadata(img,['CalibratedOpticalCenterY'])
		if CX and CY:
			cx=ParseDouble(img.metadata[CX])
			cy=ParseDouble(img.metadata[CY])
			print("Calibration center point",cx,cy,CX,cx,CY,cy)
			self.fixed_central_point=True
			return (cx,cy)

		PP=self.findMetadata(img,['PrincipalPoint'])
		if PP:
			PrincipalPoint = img.metadata[PP].split(',')
			SensorSizeLat  = self.guessSensorSizeLat(ImageWidth)
			SensorSizeLon  = self.guessSensorSizeLon(ImageHeight)
			if len(PrincipalPoint)>=2 and SensorSizeLat!=0.0 and SensorSizeLon!=0.0:
				cx = ParseDouble(PrincipalPoint[0]) * (ImageWidth  / SensorSizeLat) 
				cy = ParseDouble(PrincipalPoint[1]) * (ImageHeight / SensorSizeLon) 
				print("Calibration center point",(cx,cy),PP,repr(PrincipalPoint),"SensorSizeLat", SensorSizeLat,"SensorSizeLon", SensorSizeLon)
				return (cx,cy)

		# last resort, center of image
		if True:
			cx=ImageWidth *0.5
			cy=ImageHeight*0.5	
			print("Calibration center point",cx,cy,"ImageWidth",ImageWidth,"ImageHeight",ImageHeight)
			return (cx,cy)

	# guessCalibration
	def guessCalibration(self,multi):
		# check all same size
		Assert(len(set([single.shape for single in multi]))==1)
		ImageWidth,ImageHeight=multi[0].shape[1],multi[0].shape[0]
		f     = self.guessCalibrationFocal(ImageWidth,ImageHeight)
		cx,cy = self.guessCalibrationCentralPoint(ImageWidth,ImageHeight)
		print("f",repr(f),"cx",repr(cx),"cy",repr(cy))
		self.calibration=Calibration(f,cx,cy)
		print("Guessed calibration",self.calibration.f,self.calibration.cx,self.calibration.cy)	

	# createUndistortLenMap	
	def createUndistortLenMap(self,multi):
		pass

	# findMultiAlignment
	def findMultiAlignment(self,multi):
		if len(multi)==1: return
		print("Finding multi sensor alignment...")
		self.multi_sensor_alignment=MultiSensorAlignment(multi, self.images[0].alt, self.calibration, self.cache_dir) 
		print("Found multi sensor alignment")

	# addImage
	def addImage(self, filenames):
		self.images.append(PythonSlamImage(len(self.images),filenames))
		print("Added image",repr(filenames))	

	# setImages
	def setImages(self,all_images):

		groups=self.findGroups(all_images)
		num_per_group=max([len(group) for group in groups])
		print("Number image for group",num_per_group)
		groups=[group for group in groups if len(group)==num_per_group]

		for filenames in groups:
			self.addImage(filenames)
			
		if not self.images:
			raise Exception("cannot find any image")	

		print("Loading metadata...")
		self.loadMetadata()

		print("Loading sensor config...")
		self.loadSensorCfg()

		print("Loading telemetry...")
		self.loadTelemetry()

		print("Fiding panels...")
		self.findPanels()

		print("Print metadata...")
		self.printMetadata(self.images[0])

		print("Guessing gps...")
		self.guessGPS()

		print("Guessing plane...")
		self.guessPlane()

		print("Guessing yaw...")
		self.guessYaw()

		multi=self.generateImage(self.images[0])
		print("First multi image generated",[(single.shape,single.dtype) for single in multi])

		self.guessCalibration(multi)
		self.createUndistortLenMap(multi)
		self.findMultiAlignment(multi) 

	# undistortImage
	def undistortImage(self,multi):
		if self.xmap is None or self.ymap is None: return multi
		return [cv2.remap(single, self.xmap, self.ymap, cv2.INTER_LINEAR) for single in multi]

	# alignImage
	def alignImage(self,multi):
		if self.multi_sensor_alignment is None: return multi
		return self.multi_sensor_alignment.doAlign(multi)

	# mirrorY
	def mirrorY(self,multi):
		return [cv2.flip(single, 0) for single in multi]

	# swapRedAndBlue
	def swapRedAndBlue(self,multi):

		def getNumberOfChannels(img):
			return img.shape[2] if len(img.shape)>=3 else 1

		if len(multi)>=3 and getNumberOfChannels(multi[0])==1 and getNumberOfChannels(multi[2])==1:
			multi[0],multi[2]=multi[2],multi[0]

		for single in multi:
			if getNumberOfChannels(single)>=3:
				single[:,:,0],single[:,:,2]=single[:,:,2].copy(),single[:,:,0].copy()

		return multi

# ////////////////////////////////////////////////////////////////////////////////////////
def CreateProvider(cache_dir,progress_bar=None):
	
	image_dir=os.getcwd()
	
	all_images=[it for it in FindImages() if not "~" in it and not "VisusSlamFiles" in it]
	if not all_images:
		return None

	print("Found all images\n","\n".join([str((I,filename)) for I,filename in enumerate(all_images)]))

	reader=MetadataReader()
	
	provider_names=[os.path.splitext(os.path.basename(it))[0] for it in glob.glob(os.path.dirname(__file__) + "/image_provider_*.py")]
	provider_names.remove("image_provider_3d")
	provider_names.remove("image_provider_generic") # must be the last one
	provider_names.append("image_provider_generic")
	print("Provider names",provider_names)

	provider_modules=[importlib.import_module("slampy."+it) for it in provider_names]

	# try with some images in the middle (more probability of taking the flight images)
	provider_instance=None
	maybe_flight=all_images[int(max(len(all_images)/2-1,0)):][:2]
	for filename in maybe_flight:

		metadata=reader.readMetadata(filename)

		print("Trying to create provider from metatada")
		for key,value in metadata.items():
			print("\t",key,"=",value)

		for module in provider_modules:
			print("Trying",module.__name__)
			provider_instance=getattr(module, "CreateInstance")(metadata)
			if provider_instance: 
				print("Detected",module.__name__)
				break

		if provider_instance:
			break

	reader.close()

	if not provider_instance:
		raise Exception("cannot find a good provider")

	provider_instance.cache_dir=cache_dir
	provider_instance.progress_bar=progress_bar	
	provider_instance.setImages(all_images)
	return provider_instance
