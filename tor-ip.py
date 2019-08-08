# !/usr/bin/python3
from prettytable import PrettyTable
from stem import Signal
from stem.control import Controller
from urllib.request import urlopen
import requests
import argparse
import socket
import json
import re
import os

# args: ip, new, port, country
parser = argparse.ArgumentParser()
parser.add_argument('--ip', default=False, action='store_true')
parser.add_argument('--new', '-n', default=False, action='store_true')
parser.add_argument("--port", default=False)
parser.add_argument("--country", default=False)
args = parser.parse_args()
if args.port and args.country:
    raise Exception('between port and country, one should only be provided.')

ports = {port.split('=')[0].replace('tor_', ''): port.split('=')[1][:4] for port in
         os.popen("set | grep tor_").read().split('\n')}
ports['default'] = '0000'

ip = {}


def get_current_ip(port):
    session = requests.session()
    session.proxies = {}
    session.proxies['http'] = 'socks5h://localhost:%s' % port
    session.proxies['https'] = 'socks5h://localhost:%s' % port

    try:
        r = session.get('http://httpbin.org/ip')
    except Exception as e:
        print(str(e))
    else:
        a = json.loads(r.text)
        return a['origin'].split(',')[0]


def renew_tor_ip():
    for port in ports.values():
        if args.port and not port in args.port:
            continue
        with Controller.from_port(port=int(port) + 1) as controller:
            controller.authenticate(password="Aliqapou4979@")
            controller.signal(Signal.NEWNYM)


def getip(flags):
    if 'isp' in flags:
        ip['stem'] = json.loads(os.popen("python3 get_port_ip.py"))
    if 'tor' in flags:
        ip['tor'] = json.loads(os.system("torsocks python3 get_port_ip.py"))
        with open('ip.txt', 'r') as f:
            ip['tor'] = json.load(f)
        ip['stem'] = get_current_ip()


def getip(port=None):
    if port:
        for country, eachPort in ports.items():
            ip['tor-%s' % country] = json.loads(os.popen("python3 get_port_ip.py --port %s" % eachPort))
    else:
        for country, eachPort in ports.items():
            if port in eachPort:
                ip['tor-%s' % country] = json.loads(os.popen("python3 get_port_ip.py --port %s" % port))


getip()

x = PrettyTable()
x.field_names = ["*", "ip", "city", "country", "region"]
x.align["ip"] = "l"
x.align["city"] = "l"
x.align["country"] = "l"
x.align["region"] = "l"


def add_rows_to_table(table):
    for n, port in ports.items():
        if args.port:
            if port in args.port:
                table.add_row([n + ':' + ports['us'], ip[n]['ip'], ip[n]['city'], ip[n]['country'], ip[n]['region']])
        else:
            table.add_row([n + ':' + ports['us'], ip[n]['ip'], ip[n]['city'], ip[n]['country'], ip[n]['region']])


if args.ip and args.new:
    add_rows_to_table(x)
    print(x)
    x.clear_rows()
    renew_tor_ip()
    add_rows_to_table(x)
    print(x)

elif args.ip:
    add_rows_to_table(x)
    print(x)
elif args.new:
    renew_tor_ip()
#
#     print('--stem ', ip['stem'])
#     print('--tor: ', ip['tor']['ip'], ' > city: ', ip['tor']['city'], ' > country: ', ip['tor']['country'],
#           ' > region: ', ip['tor']['region'])
#     print('--isp: ', ip['isp']['ip'], ' > city: ', ip['isp']['city'], ' > country: ', ip['isp']['country'],
#           ' > region: ', ip['isp']['region'])
# elif args.new:
#     print('--isp: ', ip['isp']['ip'], ' > city: ', ip['isp']['city'], ' > country: ', ip['isp']['country'],
#           ' > region: ', ip['isp']['region'])
#
#     print('before:')
#     print('--stem ', ip['stem'])
#     print('--tor: ', ip['tor']['ip'], ' > city: ', ip['tor']['city'], ' > country: ', ip['tor']['country'],
#           ' > region: ', ip['tor']['region'])
#     renew_tor_ip()
#     getip(('tor',))
#     print('after:')
#     print('--stem ', ip['stem'])
#     print('--tor: ', ip['tor']['ip'], ' > city: ', ip['tor']['city'], ' > country: ', ip['tor']['country'],
#           ' > region: ', ip['tor']['region'])
