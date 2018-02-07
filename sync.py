import datetime
import logging
import pathlib
import shutil
import threading

import requests

from upf_upload import login, upload_upf

log = logging.getLogger(__name__)


def _upload(files, email: str, password: str):
    if files:
        with requests.Session() as session:
            login(session, email, password)
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


def synchronize(input_path: str, output_path: str, email: str, password: str):
    files_to_upload = []

    output_dir = pathlib.Path(output_path)
    rootdir = pathlib.Path(input_path)
    
    for f in rootdir.rglob('*'):
        if f.is_file():
            new_file = _copy_file(f, output_dir)
            if new_file:
                files_to_upload.append(str(new_file))

    if files_to_upload:
        thread = threading.Thread(target = _upload, args = (files_to_upload, email, password))
        thread.start()
