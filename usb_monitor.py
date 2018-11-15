import argparse
import logging
import pathlib
import threading
import time

import requests

import sh
import usb1
from sync import synchronize

MOUNT_POINT = "/tmp/mtp-mount"

log = logging.getLogger(__name__)
args = None

def _mount_device(device):
    try:
        product_name = device.getProduct()
    except:
        log.info("Unable to get product name of USB device, ignoring")
        return

    if not product_name or not product_name.startswith("Panono"):
        return
    log.info("Panono detected: %s", product_name)

    tmpdirname = MOUNT_POINT
    # Create mount directories if needed
    tmpdir = pathlib.Path(tmpdirname)
    tmpdir.mkdir(parents=True, exist_ok=True)

    # Mount the device
    mtp_process = sh.go_mtpfs("-android=false", tmpdirname, _bg=True)
    log.info("Device mounted on: %s", tmpdirname)
    time.sleep(1.5)

    # Synchronize the files
    synchronize(tmpdirname, args.destination, args.email, args.password)

    # Unmount the device
    time.sleep(1.0)
    try:
        mtp_process.terminate()
    finally:
        sh.sudo("umount", tmpdirname)
    log.info("Device unmounted")


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


def _init_logging():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')


def main():
    global args
    _init_logging()
    args = _parse_arguments()
    monitor_devices()


if __name__ == '__main__':
    main()
