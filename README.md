# PanonoUploader
PanonoUploader is a simple tool to perform synchronization tasks with Panono Cloud:
* Upload raw images from the camera to the cloud automatically
* Download new panoramas from the cloud to local storage.

## Getting started
You need Python 3.5+ with pip installed. First install the dependencies:
```bash
# You may need to use pip depending on your system
pip3 install -r requirements.txt
```

Next, you have to decide how the camera is recognized by your OS. If the content is automatically mounted in a path, you just have to monitor that path:
```bash
# In this command line, you have to replace all parameters with the appropriate values. Use python3 path_monitor.py -h for help
python3 path_monitor.py -e EMAIL -p PASSWORD -j /path/to/store/final/JPG/files /path/to/Panono/storage
/path/to/store/UPF/files
```

In the case the device storage is not mounted automatically, you can monitor the USB ports:
```bash
# Get more help with python3 usb_monitor.py -h
python3 usb_monitor.py -e EMAIL -p PASSWORD /path/to/store/UPF/files
```
