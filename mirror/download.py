import requests
from contextlib import nullcontext


def download_file(url, filename_or_obj):
    if isinstance(filename_or_obj, str):
        fileobj = open(filename_or_obj, 'wb')
    else:
        fileobj = nullcontext(filename_or_obj)

    with fileobj as f:
        with requests.get(url, stream=True) as request:
            request.raise_for_status()
            for chunk in request.iter_content(chunk_size=8192):
                f.write(chunk)
