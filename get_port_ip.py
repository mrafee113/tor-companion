import json

import requests


def get_port_ip(**kargs):
    url = 'http://ipinfo.io/json'
    alt_url = 'http://ip-api.com/json/'
    session = requests.session()

    if 'port' in kargs:
        session.proxies = dict()
	session.proxies['http'], session.proxies['https'] = (f'socks5h://localhost:{kargs["port"]}',) * 2

    response = session.get(url)
    if response.status_code != 200:
        response = session.get(alt_url)
        if response.status_code != 200:
            raise ConnectionRefusedError("couldn't get ip from servers")

    data = json.loads(response.text)

    # take out needed headers
    metadata = {}
    metadata_headers = 'ip-org-city-country-region'.split('-')
    for k, v in data.items():
        if k in metadata_headers:
            metadata[k] = v

    return metadata

    # older method of getting ip using PySocks
    # import socks
    # import socket
    # from urllib import request as urlrequest

    # if args.port:
    #     socks.set_default_proxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 9050)
    #     socket.socket = socks.socksocket

    # req = urlrequest.Request(url)

    # response = urlrequest.urlopen(req)
