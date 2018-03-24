import argparse
import datetime
import logging
import pathlib
import os
import shutil
import threading
import time

import requests

from cloud import api, helpers

log = logging.getLogger(__name__)

def _upload(files, email: str, password: str, jpeg_storage_path: str, processing_callback):
    has_uploaded_images = False

    if files:
        with requests.Session() as session:        
            api.login(session, email, password)
            for filename in files:
                log.info("Uploading %s", filename)
                api.upload_upf(session, filename)
                has_uploaded_images = True

            if has_uploaded_images:
                _wait_until_all_tasks_are_done(session, processing_callback)
                if jpeg_storage_path:
                    download_new_panoramas(jpeg_storage_path, email, password)

    return has_uploaded_images


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


def _wait_until_all_tasks_are_done(session: requests.Session, callback):
    if callback is None or session is None:
        return

    while(True):
        try:
            tasks = api.list_tasks(session)
            if tasks.get("count", 0) == 0:
                callback()
                return
        except requests.exceptions.RequestException:
            log.info("Exception while calling panono cloud.")

        time.sleep(25.0)


def download_new_panoramas(local_path: str, email: str, password: str):
    base_path = pathlib.Path(local_path)

    with requests.Session() as session:
        user_info = api.login(session, email, password)
        username = helpers.username(user_info)

        for item in api.list_all_panoramas(session, username):
            if item.get("type") != "panorama":
                continue
            
            id = item.get("id")
            if not id:
                log.warning("No ID found for panorama")
                continue

            data_subset = item.get("data")
            if not data_subset:
                continue

            try:
                created_at = datetime.datetime.strptime(data_subset.get("created_at"), '%Y-%m-%dT%H:%M:%S.%fZ')
            except ValueError as e:
                log.exception("Unable to parse date: %s", data_subset.get("created_at"))
                raise e

            # Check if the panorama doesn't already exist
            filename = base_path.joinpath("{date}/{id}.jpg".format(id=id, date=created_at.date().isoformat()))
            if filename.exists():
                continue
            
            # Get the details of the panorama
            self_url = item.get("self")
            if not self_url:
                continue

            # Select the largest equirectangular image
            image_details = api.call_self_url(session, self_url)
            if not image_details:
                continue
            data = image_details.get("data")
            if not data:
                continue
            images_sources = data.get("images")
            if not images_sources:
                continue
            equirectangulars = images_sources.get("equirectangulars")
            if not equirectangulars:
                continue

            selected = None
            max_size = 0
            for equi in equirectangulars:
                size = equi.get("width", 0) * equi.get("height", 0)
                if size > max_size:
                    max_size = size
                    selected = equi

            if not selected:
                continue

            image_url = selected.get("url")
            if not image_url:
                continue

            # Create directories if needed
            filename.parent.mkdir(parents=True, exist_ok=True)

            # Download the file
            try:
                log.info("Downloading %s to %s", image_url, filename)
                r = requests.get(image_url, stream=True)
                r.raise_for_status()
                with open(filename, 'wb') as image_file:
                    for chunk in r.iter_content(chunk_size=1024):
                        image_file.write(chunk)
            except:
                # Delete any unfinished file
                if filename.exists():
                    log.info("Deleting unfinished file: %s", filename)
                    try:
                        os.remove(str(filename))
                    finally:
                        pass

                raise


def synchronize(input_path: str, output_path: str, email: str, password: str, jpeg_storage_path: str, processing_callback=None):
    files_to_upload = []

    output_dir = pathlib.Path(output_path)
    rootdir = pathlib.Path(input_path)
    
    for f in rootdir.rglob('*'):
        if f.is_file():
            new_file = _copy_file(f, output_dir)
            if new_file:
                files_to_upload.append(str(new_file))

    if files_to_upload:
        thread = threading.Thread(target = _upload, args = (files_to_upload, email, password, jpeg_storage_path, processing_callback))
        thread.start()


def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description='Download files from Panono website')
    parser.add_argument('-e', '--email', dest="email", required=True, help='E-Mail used for loging in on panono.com')
    parser.add_argument('-p', '--password', dest="password", required=True, help='Password used for loging in on panono.com')
    parser.add_argument('destination', help='Storage directory')

    args = parser.parse_args()
    download_new_panoramas(args.destination, args.email, args.password)


if __name__ == '__main__':
    main()
