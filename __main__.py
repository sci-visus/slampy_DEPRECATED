import os, sys, argparse

from slampy.slam_2d import Slam2DWindow
from slampy.slam_3d import Slam3DWindow
from slampy.gui_utils import *
import datetime

# //////////////////////////////////////////////////////////////////////////////
class RedirectLog(QtCore.QObject):

	"""Redirects console output to text widget."""
	my_signal = QtCore.pyqtSignal(str)

	# constructor
	def __init__(self, filename="~visusslam.log", ):
		super().__init__()
		self.log=open(filename,'w')
		self.callback=None
		self.messages=[]
		sys.__stdout__     = sys.stdout
		sys.__stderr__     = sys.stderr
		sys.__excepthook__ = sys.excepthook
		sys.stdout=self
		sys.stderr=self
		sys.excepthook = self.excepthook

	# handler
	def excepthook(self, exctype, value, traceback):
		sys.stdout    =sys.__stdout__
		sys.stderr    =sys.__stderr__
		sys.excepthook=sys.__excepthook__
		sys.excepthook(exctype, value, traceback)

	# setCallback
	def setCallback(self, value):
		self.callback=value
		self.my_signal.connect(value)
		for msg in self.messages:
			self.my_signal.emit(msg)
		self.messages=[]

	# write
	def write(self, msg):
		msg=msg.replace("\n", "\n" + str(datetime.datetime.now())[0:-7] + " ")
		sys.__stdout__.write(msg)
		sys.__stdout__.flush()
		self.log.write(msg)
		if self.callback:
			self.my_signal.emit(msg)
		else:
			self.messages.append(msg)

	# flush
	def flush(self):
		sys.__stdout__.flush()
		self.log.flush()



# ////////////////////////////////////////////////
def Main(args):

	parser = argparse.ArgumentParser(description="slam command.")
	parser.add_argument("--dim", type=int, help="Dimension of the dataset.", required=False,default=2)
	parser.add_argument("--directory", "-d", type=str, help="Directory of the dataset.", required=False,default="")
	args = parser.parse_args(args[1:])
	
	print("Running slam","arguments", repr(args))

	# since I'm writing data serially I can disable locks
	os.environ["VISUS_DISABLE_WRITE_LOCK"]="1"
	ShowSplash()

	# -m slampy  --directory D:\GoogleSci\visus_slam\TaylorGrant (Generic)
	# -m slampy  --directory D:\GoogleSci\visus_slam\Alfalfa     (Generic)
	# -m slampy  --directory D:\GoogleSci\visus_slam\RedEdge     (micasense)
	# -m slampy "--directory D:\GoogleSci\visus_slam\Agricultural_image_collections\AggieAir uav Micasense example\test" (micasense)		
	win=Slam2DWindow()

	redirect_log=RedirectLog()
	redirect_log.setCallback(win.printLog)
	win.showMaximized()

	if args.directory:
		win.setCurrentDir(args.directory)  
	else:
	  win.chooseDirectory()

	HideSplash()
	QApplication.instance().exec()
	print("All done")
	sys.exit(0)	


# //////////////////////////////////////////
if __name__ == "__main__":
	Main(sys.argv)