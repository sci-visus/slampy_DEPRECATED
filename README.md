`

##  VisusSlam

On osx install prerequisites:

``` 
brew install exiftool zbar 
```

Install python dependencies:

```
python -m pip install --upgrade pip
python -m pip install matplotlib pymap3d pytz pyzbar scikit-image scipy pysolar json-tricks cmapy tifffile pyexiftool opencv-python opencv-contrib-python


```

Then install OpenVisus / slampy package:

``` 
python -m pip install --no-cache-dir --upgrade --force-reinstall OpenVisus
python -m OpenVisus configure

python -m pip install https://github.com/sci-visus/slampy

   
# ON MACOS ONLY, you may need to solve conflicts between Qt embedded in opencv2 and PyQt5 we are going to use:
python -m pip uninstall -y opencv-python          opencv-contrib-python
python -m pip install      opencv-python-headless opencv-contrib-python-headless 

python -m slam
```