import argparse
import datetime
import logging
import pathlib
import shutil
import tempfile
import threading
import time

import requests

import sh
import usb1
from upf_upload import login, upload_upf

MOUNT_POINT = "/tmp/mtp-mount"

log = logging.getLogger(__name__)
args = None


def _upload(files):
    if files:
        with requests.Session() as session:
            login(session, args.email, args.password)
            for filename in files:
                log.info("Uploading %s", filename)
                upload_upf(session, filename)


def _copy_file(f: pathlib.Path, output_path: pathlib.Path):
    log.info("Processing: %s", f)
    statResult = f.stat()
    file_timestamp = datetime.datetime.fromtimestamp(statResult.st_mtime)

    # Build destination filename
    destination_dir = output_path.joinpath(
        str(file_timestamp.year),
        file_timestamp.date().isoformat())
    
    destination = destination_dir.joinpath(f.name)

    if destination.exists():
        log.info("File already exists: %s", destination)
        return None

    # Create directories if needed
    destination_dir.mkdir(parents=True, exist_ok=True)

    # Copy the file
    shutil.copy2(str(f), str(destination))

    return destination


def _synchronize(input_path: str, output_path: str):
    files_to_upload = []

    output_dir = pathlib.Path(output_path)
    rootdir = pathlib.Path(input_path)
    
    for f in rootdir.rglob('*'):
        if f.is_file():
            new_file = _copy_file(f, output_dir)
            if new_file:
                files_to_upload.append(str(new_file))

    if files_to_upload:
        thread = threading.Thread(target = _upload, args = (files_to_upload, ))
        thread.start()


def _mount_device(device):

    product_name = device.getProduct()
    if not product_name or not product_name.startswith("Panono"):
        return
    log.info("Panono detected: %s", product_name)

    #tmpdir = tempfile.TemporaryDirectory()
    #tmpdirname = tmpdir.name
    #print('created temporary directory', tmpdirname)
    tmpdirname = MOUNT_POINT
    # Create mount directories if needed
    tmpdir = pathlib.Path(tmpdirname)
    tmpdir.mkdir(parents=True, exist_ok=True)

    # Mount the device
    mtp_process = sh.go_mtpfs("-android=false", tmpdirname, _bg=True)
    log.info("Device mounted")
    time.sleep(1.0)

    # Synchronize the files
    _synchronize(tmpdirname, args.destination)

    # Unmount the device
    time.sleep(1.0)
    try:
        mtp_process.terminate()
    finally:
        sh.sudo("umount", tmpdirname)
    log.info("Device unmounted")


def _umount_device(device):
    pass


ACTION_HANDLERS = {
    'add': _mount_device,
    'remove': _umount_device,
}


def hotplug_callback(context, device, event):
    log.info("Device %s: %s" % (
        {
            usb1.HOTPLUG_EVENT_DEVICE_ARRIVED: 'arrived',
            usb1.HOTPLUG_EVENT_DEVICE_LEFT: 'left',
        }[event],
        device,
    ))
    # Note: cannot call synchronous API in this function.

    if event == usb1.HOTPLUG_EVENT_DEVICE_ARRIVED:
        thread = threading.Thread(target = _mount_device, args = (device, ))
        thread.start()


def monitor_devices():
    with usb1.USBContext() as context:
        if not context.hasCapability(usb1.CAP_HAS_HOTPLUG):
            log.error('Hotplug support is missing. Please update your libusb version.')
            return
        log.info('Registering hotplug callback...')
        opaque = context.hotplugRegisterCallback(hotplug_callback)
        log.info('Callback registered. Monitoring events, ^C to exit')
        try:
            while True:
                context.handleEvents()
        except (KeyboardInterrupt, SystemExit):
            log.info('Exiting')


def _parse_arguments():
    parser = argparse.ArgumentParser(description='Downloads UPF from the Panono.')
    parser.add_argument('-e', '--email', dest="email", required=True, help='E-Mail used for loging in on panono.com')
    parser.add_argument('-p', '--password', dest="password", required=True, help='Password used for loging in on panono.com')
    parser.add_argument('destination', help='Storage directory')

    return parser.parse_args()


def init_logging():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')


def main():
    global args
    init_logging()
    args = _parse_arguments()
    #_mount_device(None)
    monitor_devices()


if __name__ == '__main__':
    main()
