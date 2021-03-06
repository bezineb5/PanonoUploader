import argparse
import logging
import os
import pathlib
import time
from logging import handlers

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from sync import synchronize

log = logging.getLogger(__name__)

MOUNT_PREFIX = "Panono"
DEFAULT_LOG_DIRECTORY = "./logs"


class MTPMountWatcher(FileSystemEventHandler):
    def __init__(self, destination_path: str, email: str, password: str, jpeg_storage_path: str):
        self.destination_path = destination_path
        self.email = email
        self.password = password
        self.jpeg_storage_path = jpeg_storage_path

    def on_created(self, event):
        """Called when a file or directory is created.

        :param event:
            Event representing file/directory creation.
        :type event:
            :class:`DirCreatedEvent` or :class:`FileCreatedEvent`
        """

        if event is None or not event.is_directory:
            return
        
        src_path = pathlib.Path(event.src_path)
        if src_path.is_symlink() or not src_path.name.startswith(MOUNT_PREFIX):
            return

        log.info("Detected device, starting synchronisation: %s", src_path)

        synchronize(src_path, self.destination_path, self.email, self.password, 
                    self.jpeg_storage_path,
                    processing_callback=_notify_once_finished)


def _notify_once_finished():
    pass


def _monitor_path(monitored_path: str, destination_path: str, email: str, password: str, jpeg_storage_path: str):
    event_handler = MTPMountWatcher(destination_path, email, password, jpeg_storage_path)

    observer = Observer()
    observer.schedule(event_handler, monitored_path, recursive=False)
    observer.start()

    log.info("Started monitoring path: %s", monitored_path)
    try:
        while True:
            time.sleep(2.0)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


def _parse_arguments():
    parser = argparse.ArgumentParser(description='Downloads UPF from the Panono.')
    parser.add_argument('-e', '--email', dest="email", required=True, help='E-Mail used for loging in on panono.com')
    parser.add_argument('-p', '--password', dest="password", required=True, help='Password used for loging in on panono.com')
    parser.add_argument('-l', '--logs', dest="logs_path", required=False, help='Path to store the logs', default=DEFAULT_LOG_DIRECTORY)
    parser.add_argument('-j', '--jpg', dest="jpeg_storage_path", required=False, help='Path to store the equirectangular jpegs', default=None)
    parser.add_argument('monitored_path', help='Directory to monitor')
    parser.add_argument('destination', help='Storage directory')

    return parser.parse_args()


def _init_logging(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

    log_file = os.path.join(directory, "panono_uploader.log")
    handler = handlers.TimedRotatingFileHandler(log_file,
                                                        when="d",
                                                        interval=1,
                                                        backupCount=10)

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        handlers=[handler])

def main():
    args = _parse_arguments()
    _init_logging(args.logs_path)
    _monitor_path(args.monitored_path, args.destination, args.email, args.password, args.jpeg_storage_path)

if __name__ == '__main__':
    main()
