import argparse
import datetime
import pathlib
import shutil
import tempfile
import time

import requests

import pyudev
import sh

from upf_upload import login, upload_upf

args = None

MOUNT_POINT = "/tmp/mtp-mount"

def _upload(files):
    with requests.Session() as session:
        login(session, args.email, args.password)
        for filename in files:
            upload_upf(session, filename)


def _copy_file(f: pathlib.Path, output_path: pathlib.Path):
    print("Processing: ", str(f))
    statResult = f.stat()
    file_timestamp = datetime.datetime.fromtimestamp(statResult.st_mtime)

    # Build destination filename
    destination_dir = output_path.joinpath(
        str(file_timestamp.year),
        file_timestamp.date().isoformat())
    
    destination = destination_dir.joinpath(f.name)

    if destination.exists():
        print("File already exists: ", destination)
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


def _mount_device(device):
    #tmpdir = tempfile.TemporaryDirectory()
    #tmpdirname = tmpdir.name
    #print('created temporary directory', tmpdirname)
    tmpdirname = MOUNT_POINT

    # Mount the device
    mtp_process = sh.go_mtpfs(tmpdirname, _bg=True)
    time.sleep(1.0)

    # Synchronize the files
    _synchronize(tmpdirname, args.destination)

    # Unmount the device
    #mtp_process.terminate()


def _umount_device(device):
    pass


ACTION_HANDLERS = {
    'add': _mount_device,
    'remove': _umount_device,
}


def monitor_devices():
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by('usb')
    for device in iter(monitor.poll, None):
        print("{action}: {device}".format(action=device.action, device=device))
        action = ACTION_HANDLERS.get(device.action)
        if action:
            action(device)


def _parse_arguments():
    parser = argparse.ArgumentParser(description='Downloads UPF from the Panono.')
    parser.add_argument('-e', '--email', dest="email", required=True, help='E-Mail used for loging in on panono.com')
    parser.add_argument('-p', '--password', dest="password", required=True, help='Password used for loging in on panono.com')
    parser.add_argument('destination', help='Storage directory')

    return parser.parse_args()


def main():
    global args
    args = _parse_arguments()
    monitor_devices()


if __name__ == '__main__':
    main()
