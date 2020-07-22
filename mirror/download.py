import requests
from contextlib import nullcontext
import os
import werkzeug
import urllib


def get_download_name_from_request(request):
    if 'Content-Disposition' in request.headers:
        disposition = werkzeug.http.parse_options_header(request.headers['Content-Disposition'])[1]
        if 'filename' in disposition:
            return urllib.parse.unquote(disposition['filename'])

    return urllib.parse.unquote(os.path.basename(request.request.path_url))


def get_download_name(url):
    with requests.get(url, stream=True) as request:
        return get_download_name_from_request(request)


def download_file(url, filename_or_obj):
    filename = None
    with requests.get(url, stream=True) as request:
        if not isinstance(filename_or_obj, str):
            fileobj = nullcontext(filename_or_obj)
        elif os.path.isdir(filename_or_obj):
            filename = os.path.join(filename_or_obj, get_download_name_from_request(request))
            fileobj = open(filename, 'wb')
        else:
            filename = filename_or_obj
            fileobj = open(filename_or_obj, 'wb')

        with fileobj as f:
            with requests.get(url, stream=True) as request:
                request.raise_for_status()
                for chunk in request.iter_content(chunk_size=8192):
                    f.write(chunk)

    return filename
