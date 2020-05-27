import os, sys,argparse


# ////////////////////////////////////////////////
def Main(args):
	
	# no arguments
	if len(args)<=1:
		sys.exit(0)	
		
	parser = argparse.ArgumentParser(description="slam command.")
	parser.add_argument("--dim", type=int, help="Dimension of the dataset.", required=False,default=2)
	parser.add_argument("--directory", type=str, help="Directory of the dataset.", required=False,default="")
	args = parser.parse_args(args[1:])		
		
	# example: python -m slampy --dim 3  --directory D:\GoogleSci\visus_dataset\male\RAW\Fullcolor\fullbody
	if args.dim==3:
		from .slam_3d import Main as SlamMain
		SlamMain(args.directory)
		
	# -m slampy  --directory D:\GoogleSci\visus_slam\TaylorGrant (Generic)
	# -m slampy  --directory D:\GoogleSci\visus_slam\Alfalfa     (Generic)
	# -m slampy  --directory D:\GoogleSci\visus_slam\RedEdge     (micasense)
	# -m slampy "--directory D:\GoogleSci\visus_slam\Agricultural_image_collections\AggieAir uav Micasense example\test" (micasense)		
	else:
		from .slam_2d import Main as SlamMain
		SlamMain(args.directory)
		
	sys.exit(0)	


# //////////////////////////////////////////
if __name__ == "__main__":
	Main(sys.argv)