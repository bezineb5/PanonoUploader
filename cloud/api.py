import argparse
import glob
import json
import logging
import random
from typing import Dict

import requests

log = logging.getLogger(__name__)

ROOT_URL = "https://api3-dev.panono.com"

HEADERS = {
    'Cache-Control': "no-cache",
    'Origin': "https://cloud.panono.com",
    'Content-Type': "application/json;charset=UTF-8",
}


def login(session: requests.Session, username: str, password: str):
    log.info("Logging in: %s", username)

    url = ROOT_URL + "/login"

    parameters = {
        "email": username,
        "password": password,
        "remember_me": False,
    }

    response = session.post(url, data=json.dumps(parameters), headers=HEADERS)
    response.raise_for_status()
    output = response.json()
    log.info(output)

    return output


def _generate_random_id() -> str:
    charset = "0123456789"
    return "".join(random.sample(charset, 10))


def _create_image(session: requests.Session) -> str:
    log.info("Creating image")

    url = ROOT_URL + "/panorama/create"
    payload = {
        "type": "panorama",
        "data": {
            "image_id":"image_" + _generate_random_id(),
        },
    }

    response = session.post(url, data=json.dumps(payload), headers=HEADERS)
    response.raise_for_status()
    output = response.json()
    log.info(output)

    return output.get('id')


def _create_upf(session: requests.Session, id: str) -> (str, str):
    log.info("Creating UPF: %s", id)

    url = "{root}/panorama/{id}/upf".format(root=ROOT_URL, id=id)

    response = session.post(url, headers=HEADERS)
    response.raise_for_status()
    output = response.json()
    log.info(output)

    return output.get('upload_url'), output.get('callback_url')


def _upload_image(upload_url: str, filename: str):
    log.info("Uploading image: %s", filename)

    headers = {
        "Content-type": "application/x-unstitched-panorama-format",
        "Origin": "https://cloud.panono.com",
    }

    with open(filename, 'rb') as large_file:
        response = requests.put(upload_url, data=large_file, headers=headers)
        response.raise_for_status()
        log.info(response.text)


def _callback_after_upload(session: requests.Session, callback_url: str):
    log.info("Callback call")

    url = ROOT_URL + callback_url
    response = session.post(url, headers=HEADERS)
    response.raise_for_status()
    output = response.json()
    log.info(output)


def upload_upf(session: requests.Session, filename: str):
    image_id = _create_image(session)
    upload_url, callback_url = _create_upf(session, image_id)
    _upload_image(upload_url, filename)
    _callback_after_upload(session, callback_url)


def list_tasks(session: requests.Session) -> Dict:
    log.info("Listing tasks")

    url = "{root}/tasks".format(root=ROOT_URL)

    response = session.get(url, headers=HEADERS)
    response.raise_for_status()
    output = response.json()
    log.info(output)

    return output

def list_panoramas(session: requests.Session, username: str, page_size: int=50) -> Dict:
    url = "{root}/u/{username}/panoramas".format(root=ROOT_URL, username=username)

    query_parameters = {
        "pageSize": page_size,
    }

    response = session.get(url, headers=HEADERS, params=query_parameters)
    response.raise_for_status()
    output = response.json()
    log.info(output)

    return output


def list_all_panoramas(session: requests.Session, username: str):
    log.info("Listing all panoramas")

    page = list_panoramas(session, username)

    while page:
        items = page.get("items")
        next_page = page.get("next")
        page = None

        if items:
            for item in items:
                yield item
        
        if next_page:
            page = call_self_url(session, next_page)


def call_self_url(session: requests.Session, self_url: str) -> Dict:
    if not session or not self_url:
        return None

    response = session.get(self_url, headers=HEADERS)
    response.raise_for_status()
    return response.json()


def _parse_arguments():
    parser = argparse.ArgumentParser(description='Upload UPF to the Panono.com website for processing.')
    parser.add_argument('-e', '--email', dest="email", required=True, help='E-Mail used for loging in on panono.com')
    parser.add_argument('-p', '--password', dest="password", required=True, help='Password used for loging in on panono.com')
    parser.add_argument('filenames', metavar='filename', nargs='+',
                    help='UPF files to upload')

    return parser.parse_args()


def main():
    args = _parse_arguments()

    with requests.Session() as session:
        login(session, args.email, args.password)
        for pathname in args.filenames:
            for filename in glob.iglob(pathname):
                upload_upf(session, filename)


if __name__ == '__main__':
    main()
