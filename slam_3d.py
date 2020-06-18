
import os,sys,pickle
import platform,subprocess,glob,datetime
import cv2
import numpy
import random
import threading
import time

from PyQt5 import QtCore 
from PyQt5.QtCore                     import QUrl
from PyQt5.QtWidgets                  import QApplication, QHBoxLayout, QLineEdit
from PyQt5.QtWidgets                  import QMainWindow, QPushButton, QVBoxLayout,QSplashScreen
from PyQt5.QtWidgets                  import QWidget
from PyQt5.QtWidgets                  import QTableWidget,QTableWidgetItem

from OpenVisus                        import *
from OpenVisus.gui                    import *

from slampy.extract_keypoints import *
from slampy.gui_utils         import *
from slampy.image_utils       import *


# ///////////////////////////////////////////////////////////////////
class Slam3D(Slam):

	# constructors
	def __init__(self,width,height,dtype,calibration,cache_dir):
		super(Slam3D,self).__init__()
		self.width              = width
		self.height             = height
		self.dtype              = dtype
		self.calibration        = calibration
		self.cache_dir          = cache_dir

		self.debug_mode         = False # True
		self.energy_size        = 1280 
		self.min_num_keypoints  = 3000
		self.max_num_keypoints  = 6000
		self.anms               = 1300
		self.max_reproj_error   = 0.01 
		self.ratio_check        = 0.8
		self.calibration.bFixed = False 
		self.ba_tolerance       = 0.005

		self.num_run            = 0
		self.images             = []
		self.extractor          = None

	# generateImage
	def generateImage(self,img):
		raise Exception("to implement")

	# addImage
	def addImage(self,img):
		self.images.append(img)
		camera=Camera()
		camera.id=img.id
		camera.color = Color.random()
		for filename in img.filenames:
			camera.filename.append(filename)
		super().addCamera(camera)

	# startAction
	def startAction(self,N,message):
		pass

	# advanceAction
	def advanceAction(self,I):
		pass

	# endAction
	def endAction(self):
		pass

	# showEnergy
	def showEnergy(self,camera,energy):
		pass

	# debugMatchesGraph
	def debugMatchesGraph(self):
		lines=[]
		for bGoodMatches in [False,True]:
			for A in self.cameras :
				local_cameras=A.getAllLocalCameras()
				for J in range(local_cameras.size()):
					B=local_cameras[J]
					edge=A.getEdge(B)
					if A.id < B.id:
						num_matches = edge.matches.size()
						lines.append("%d,%d,%d" % (A.id,B.id,num_matches))

		SaveTextDocument(GuessUniqueFilename(self.cache_dir+"/~matches%d.csv"), "\n".join(lines))

	# debugSolution
	def debugSolution(self):
		lines=["%d,%f,%f" % (camera.id,camera.homography(0,2),camera.homography(1,2)) for camera in self.cameras]
		SaveTextDocument(GuessUniqueFilename(self.cache_dir+"/~solution%d.csv"), "\n".join(lines))

	# doPostIterationAction
	def doPostIterationAction(self):
		self.debugSolution()
		self.debugMatchesGraph()

	# extractKeyPoints
	def extractKeyPoints(self,ConvertToIdx):

		t1=Time.now()

		# convert to idx and find keypoints (don't use threads for IO ! it will slow down things)
		# NOTE I'm disabling write-locks
		self.startAction(len(self.cameras),"Converting idx and extracting keypoints...")

		if not self.extractor:
			self.extractor=ExtractKeyPoints(self.min_num_keypoints,self.max_num_keypoints,self.anms)

		for I,(img,camera) in enumerate(zip(self.images,self.cameras)):
			self.advanceAction(I)

			# create idx and extract keypoints
			keypoint_filename = self.cache_dir+"/keypoints/%04d" % (camera.id,)
			idx_filename      = self.cache_dir+"/" + camera.idx_filename

			if not self.loadKeyPoints(camera,keypoint_filename) or not os.path.isfile(idx_filename):
				full = self.generateImage(img)
				Assert(isinstance(full, numpy.ndarray))

				if ConvertToIdx:
					dataset = LoadDataset(idx_filename)
					dataset.compressDataset(["zip"],Array.fromNumPy(full,TargetDim=3, bShareMem=True))

				energy=ConvertImageToGrayScale(full)
				energy=ResizeImage(energy, self.energy_size)
				(keypoints,descriptors)=self.extractor.doExtract(energy)

				vs=self.width  / float(energy.shape[1])
				if keypoints:
					camera.keypoints.clear()
					camera.keypoints.reserve(len(keypoints))
					for keypoint in keypoints:
						camera.keypoints.push_back(KeyPoint(vs*keypoint.pt[0], vs*keypoint.pt[1], keypoint.size, keypoint.angle, keypoint.response, keypoint.octave, keypoint.class_id))
					camera.descriptors=Array.fromNumPy(descriptors,TargetDim=2) 

				self.saveKeyPoints(camera,keypoint_filename)

				energy=cv2.cvtColor(energy, cv2.COLOR_GRAY2RGB)
				for keypoint in keypoints:
					cv2.drawMarker(energy, (int(keypoint.pt[0]), int(keypoint.pt[1])), (0, 255, 255), cv2.MARKER_CROSS, 5)
				energy=cv2.flip(energy, 0)
				energy=ConvertImageToUint8(energy)

				self.showEnergy(camera, energy)

			print("Done",camera.filenames[0],I,"of",len(self.images))

		print("done in",t1.elapsedMsec(),"msec")

	# findMatches
	def findMatches(self,camera1,camera2):

		if camera1.keypoints.empty() or camera2.keypoints.empty():
			camera2.getEdge(camera1).setMatches([],"No keypoints")
			return 0

		matches,H21,err=FindMatches(self.width,self.height,
			camera1.id,[(k.x, k.y) for k in camera1.keypoints],Array.toNumPy(camera1.descriptors), 
			camera2.id,[(k.x, k.y) for k in camera2.keypoints],Array.toNumPy(camera2.descriptors),
			self.max_reproj_error * self.width, self.ratio_check)

		if self.debug_mode and H21 is not None and len(matches)>0:
			points1=[(k.x, k.y) for k in camera1.keypoints]
			points2=[(k.x, k.y) for k in camera2.keypoints]
			DebugMatches(self.cache_dir+"/debug_matches/%s/%04d.%04d.%d.png" %(err if err else "good",camera1.id,camera2.id,len(matches)), 
				self.width, self.height, 
				Array.toNumPy(ArrayUtils.loadImage(self.cache_dir+"/energy/~%04d.tif" % (camera1.id,))), [points1[match.queryIdx] for match in matches], H21, 
				Array.toNumPy(ArrayUtils.loadImage(self.cache_dir+"/energy/~%04d.tif" % (camera2.id,))), [points2[match.trainIdx] for match in matches], numpy.identity(3,dtype='float32'))

		if err:
			camera2.getEdge(camera1).setMatches([],err)
			return 0

		matches=[Match(match.queryIdx,match.trainIdx, match.imgIdx, match.distance) for match in matches]
		camera2.getEdge(camera1).setMatches(matches,str(len(matches)))
		return len(matches)

	# findAllMatches
	def findAllMatches(self,nthreads=8):
		t2 = Time.now()
		jobs=[]
		for camera2 in self.cameras:
			for camera1 in camera2.getAllLocalCameras():
				if camera1.id < camera2.id:
					jobs.append(lambda pair=(camera1,camera2): self.findMatches(pair[0],pair[1]))

		self.startAction(len(jobs),"Finding all matches")
		results=RunJobsInParallel(jobs,advance_callback=lambda ndone: self.advanceAction(ndone))
		num_matches=sum(results)
		print("Found num_matches(", num_matches, ") matches in ", t2.elapsedMsec() ,"msec")
		self.endAction()

	# run
	def run(self):

		if self.num_run==0:
			self.extractKeyPoints()
			self.findAllMatches()
			self.removeDisconnectedCameras()
			self.debugMatchesGraph()

		tolerances=(10.0*self.ba_tolerance,1.0*self.ba_tolerance)
		self.startAction(len(tolerances),"Running adjustment")
		for I,tolerance in enumerate(tolerances):
			self.advanceAction(I)
			self.bundleAdjustment(tolerance)
			self.removeOutlierMatches(self.max_reproj_error * self.width)
			self.removeDisconnectedCameras()
			self.removeCamerasWithTooMuchSkew()
		self.endAction()

		self.num_run+=1
		print("Finished")
		
# //////////////////////////////////////////////////////////////////////////////
def CreatePushButton(text,callback=None, img=None ):
	ret=QPushButton(text)
	#ret.setStyleSheet("QPushButton{background: transparent;}");
	ret.setAutoDefault(False)
	if callback:
		ret.clicked.connect(callback)
	if img:
		ret.setIcon(QtGui.QIcon(img))
	return ret


# //////////////////////////////////////////////////////////////////////////////
class Slam3DWindow(QMainWindow):
	
	# constructor
	def __init__(self):
		super(Slam3DWindow, self).__init__()
		self.setWindowTitle("3d Stitching")
		self.image_directory=""
		self.cache_dir=""
		self.dataset=None
		self.createGui()

	# createGui
	def createGui(self):

		class Buttons : pass
		self.buttons=Buttons
		
		# create widgets
		self.viewer=Viewer()
		self.viewer.setMinimal()
		viewer_subwin = sip.wrapinstance(FromCppQtWidget(self.viewer.c_ptr()), QtWidgets.QMainWindow)	
		
		self.progress_bar=ProgressLine()

		self.preview=PreviewImage(preview_width=800)

		self.log = QTextEdit()
		self.log.setLineWrapMode(QTextEdit.NoWrap)
		
		p = self.log.viewport().palette()
		p.setColor(QPalette.Base, QtGui.QColor(200,200,200))
		p.setColor(QPalette.Text, QtGui.QColor(0,0,0))
		self.log.viewport().setPalette(p)
		
		main_layout=QVBoxLayout()
		
		# toolbar
		toolbar=QHBoxLayout()

		self.buttons.run_slam=CreatePushButton("Run",
			lambda: self.run())
			
		toolbar.addWidget(self.buttons.run_slam)
		toolbar.addLayout(self.progress_bar)

		toolbar.addStretch(1)
		main_layout.addLayout(toolbar)
		
		center = QSplitter(QtCore.Qt.Horizontal)
		center.addWidget(viewer_subwin)
		center.setSizes([100,200])
		
		main_layout.addWidget(center,1)
		main_layout.addWidget(self.log)

		central_widget = QFrame()
		central_widget.setLayout(main_layout)
		central_widget.setFrameShape(QFrame.NoFrame)
		self.setCentralWidget(central_widget)

	# processEvents
	def processEvents(self):
		if hasattr(self,"last_process_events") or self.last_process_events.elapsedMsec()<200: return
		QApplication.processEvents()
		time.sleep(0.00001)
		self.last_process_events=Time.now()

	# printLog
	def printLog(self,text):
		self.log.moveCursor(QtGui.QTextCursor.End)
		self.log.insertPlainText(text)
		self.log.moveCursor(QtGui.QTextCursor.End)	
		self.processEvents()

	# startAction
	def startAction(self,N,message):
		print(message)
		self.progress_bar.setRange(0,N)
		self.progress_bar.setMessage(message)
		self.progress_bar.setValue(0)
		self.progress_bar.show()
		self.processEvents()

	# advanceAction
	def advanceAction(self,I):
		self.progress_bar.setValue(max(I,self.progress_bar.value()))
		self.processEvents()

	# endAction
	def endAction(self):
		elf.progress_bar.hide()
		self.processEvents()

	# showEnergy
	def showEnergy(self,camera,energy):

		if self.slam.debug_mode:
			SaveImage(self.cache_dir+"/generated/%04d.%d.tif" % (camera.id,camera.keypoints.size()), energy)

		self.preview.showPreview(energy,"Extracting keypoints image(%d/%d) #keypoints(%d)" % (I,len(self.provider.images),len(camera.keypoints.size())))
		self.processEvents()

	# showMessageBox
	def showMessageBox(self,msg):
		print(msg)
		QMessageBox.information(self, 'Information', msg)

	# refreshViewer
	def refreshViewer(self):
		self.viewer.open(self.cache_dir+"/visus.idx")

	# generateImage
	def generateImage(self,img):
		t1=Time.now()
		print("Generating image",img.filenames[0])	
		ret = InterleaveChannels(self.provider.generateImage(img))
		print("done",img.id,"range",ComputeImageRange(ret),"shape",ret.shape, "dtype",ret.dtype,"in",t1.elapsedMsec()/1000,"msec")
		return ret

	# setCurrentDir
	def setCurrentDir(self,image_dir):
		
		# avoid recursions
		if self.image_directory==image_dir:
			return
			
		self.image_directory=image_dir
		self.log.clear()
		Assert(os.path.isdir(image_dir))
		os.chdir(image_dir)
		self.cache_dir=os.path.abspath("./VisusSlamFiles")
		self.provider=ImageProvider3d(self.cache_dir)
		os.makedirs(self.cache_dir,exist_ok=True)
		TryRemoveFiles(self.cache_dir+'/~*')
		T1=Time.now()

		full=self.generateImage(self.images[0])
		array=Array.fromNumPy(full,TargetDim=2)
		width  = array.getWidth()
		height = array.getHeight()
		dtype  = array.dtype

		self.slam=Slam3D(width,height,dtype,self.provider.calibration,self.cache_dir)
		self.slam.debug_mode=False
		self.slam.generateImage=self.generateImage
		self.slam.startAction=self.startAction
		self.slam.advanceAction=self.advanceAction
		self.slam.endAction=self.endAction
		self.slam.showEnergy=self.showEnergy

		for img in sekf.provider.images:
			self.slam.addImage(img)
		
		self.guessLocalCameras()
		self.slam.debugMatchesGraph()
		self.slam.debugSolution()
		self.saveDataset()
		self.dataset=LoadDataset(self.cache_dir+"/visus.idx");Assert(self.dataset)
		self.refreshViewer()

		self.setWindowTitle("%s num_images(%d) width(%d) height(%d) dtype(%s) " 
							 % (self.image_directory, len(self.provider.images),self.slam.width, self.slam.height, self.slam.dtype.toString()))


	# guessLocalCameras
	def guessLocalCameras(self):
		for I in range(len(self.slam.cameras)-1):
			camera1=self.slam.cameras[I  ]
			camera2=self.slam.cameras[I+1]
			camera1.addLocalCamera(camera2)

	# saveDataset
	def saveDataset(self):
		url=self.cache_dir+"/visus.idx"
		idxfile=IdxFile()
		idxfile.logic_box = BoxNi(PointNi(0,0,0),PointNi(self.slam.width,self.slam.height,len(self.slam.cameras)))
		field=Field("myfield", self.slam.dtype);
		field.default_compression = ""
		field.default_layout = "rowmajor"
		idxfile.fields.push_back(field)
		success = idxfile.save(url)
		Assert(success)

	# writeSlice
	def writeSlice(self,src,offset,Z):
		access=self.dataset.createAccess()
		query=BoxQuery(self.dataset,self.dataset.getDefaultField(),self.dataset.getDefaultTime(),ord('w'))
		query.logic_box=self.dataset.getLogicBox().getZSlab(Z,Z+1)
		self.dataset.beginQuery(query)
		Assert(query.isRunning())
		query.buffer=Array.fromNumPy(src,TargetDim=2)
		success=self.dataset.executeQuery(access,query)
		Assert(success)


	# run
	def run(self):

		T1=Time.now()

		if True:

			if self.slam.num_run==0:

				self.slam.extractKeyPoints()
				self.preview.hide()

				self.slam.findAllMatches()
				#self.slam.removeDisconnectedCameras()
				self.slam.debugMatchesGraph()
				self.slam.debugSolution()

			tolerances=(10.0*self.slam.ba_tolerance,1.0*self.slam.ba_tolerance)
			for I,tolerance in enumerate(tolerances):
				self.slam.bundleAdjustment(tolerance,"offset")
				self.slam.removeOutlierMatches(self.slam.max_reproj_error)
				#self.slam.removeDisconnectedCameras()
				#self.slam.removeCamerasWithTooMuchSkew()

		# load dataset for data conversion
		N=len(self.provider.images)
		Assert(N==len(self.slam.cameras))

		# for each image write the slice (can be written only after the bundle adjustment, since it depends on the offset)
		self.startAction(N,"Writing slices...")
		for I,img in enumerate(self.slam.images):

			# note: there are few slices that are totally black, going to use them as they are
			offset=(round(self.slam.cameras[I].homography(0,2)),round(self.slam.cameras[I].homography(1,2)))
			src=self.provider.generateImage(img)

			Z=img.id
			msg="Writing slice(%d/%d) offset(%f,%f) Z(%d)" % (I,len(self.provider.images),offset[0],offset[1],Z)
			print(msg)

			# apply offset
			if True:

				W,H = self.slam.width,self.slam.height

				# domain of generated image
				x1,x2 = 0,W
				y1,y2 = 0,H

				# find intersection with dataset LOGIC box
				logic_box=self.dataset.getLogicBox()
				X1,X2 = max([x1+offset[0],logic_box.p1[0]]),min([x2+offset[0],logic_box.p2[0]])
				Y1,Y2 = max([y1+offset[1],logic_box.p1[1]]),min([y2+offset[1],logic_box.p2[1]])

				# go back to generated image domain
				x1,x2=X1-offset[0],X2-offset[0]
				y1,y2=Y1-offset[1],Y2-offset[1]

				tmp=numpy.zeros((H,W,3),dtype='uint8')
				tmp[Y1:Y2,X1:X2,0:3]=src[y1:y2,x1:x2,0:3]
				src=tmp

			# uncomment if you want to see what's going on
			# SaveImage(cache_dir+"/offset/~slice%04d.orig.png" % (Z,),src)

			self.writeSlice(src,offset,Z)

			self.slam.preview.showPreview(cv2.flip(src, 0),msg)
			self.advanceAction(I)

		print("All done in",T1.elapsedMsec(),"msec")
		self.endAction()
		self.slam.preview.hide()
		self.refreshViewer()


	