import tempfile
import time
import pathlib
import datetime
import shutil

import pyudev
import sh


def _copy_file(f: pathlib.Path, output_path: pathlib.Path):
    statResult = f.stat()
    file_timestamp = datetime.datetime.fromtimestamp(statResult.st_mtime)

    # Build destination filename
    destination_dir = output_path.joinpath(
        str(file_timestamp.year),
        file_timestamp.date.isoformat())
    
    destination = destination_dir.joinpath(f.name)

    if destination.exists():
        print("File already exists: ", destination)
        return

    # Create directories if needed
    destination_dir.mkdir(parents=True, exist_ok=True)

    # Copy the file
    shutil.copy2(str(f), str(destination))


def _synchronize(input_path: str, output_path: str):
    output_dir = pathlib.Path(output_path)
    rootdir = pathlib.Path(input_path)
    for f in rootdir.rglob('*'):
        if f.is_file():
            _copy_file(f, output_dir)


def _mount_device(device):
    with tempfile.TemporaryDirectory() as tmpdirname:
        print('created temporary directory', tmpdirname)

        # Mount the device
        mtp_process = sh.go_mtpfs(tmpdirname, _bg=True)
        time.sleep(1.0)

        # Synchronize the files

        # Unmount the device
        mtp_process.terminate()


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


def main():
    monitor_devices()


if __name__ == '__main__':
    main()
