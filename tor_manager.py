import argparse
import logging

from TManager import TManager

logger = logging.Logger("TManager_arg_parser")
io_handler = logging.StreamHandler()
logger.addHandler(io_handler)

parser = argparse.ArgumentParser()
parser.add_argument("--port", default=False)
parser.add_argument("--country", default=False)

parser.add_argument("--start-client", default=False, help='start tor client based on the specified details.')
parser.add_argument("--stop-client", default=False, help='stop tor client based on the specified details.')

parser.add_argument("--show-configs", default=False, action="store_true")
parser.add_argument("--show-running-clients", default=False, action="store_true")
parser.add_argument("--stop-running-clients", default=False, action="store_true")
parser.add_argument("--start-all-clients", default=False, action="store_true")

parser.add_argument("--renew-ip", default=False, action="store_true",
                    help='if not specified, it will renew all clients.')
parser.add_argument("--show-ip", default=False, action="store_true")

parser.add_argument("--create-new-torrc-config", default=False, action="store_true")
parser.add_argument("--delete-torrc-config", default=False, action="store_true")

parser.add_argument("--sudo", default=False, action="store_true")
parser.add_argument("--tunnel-tor-proxy", default=False, action="store_true")

args = parser.parse_args()

if args.port and args.country:
    logger.error('between port and country, one should only be provided.')
    exit(1)
if (args.start_client or args.stop_client) and not (args.port or args.country):
    logger.error('for starting or stopping a client you have to specify port or country of client.')
    exit(1)
if (args.create_new_torrc_config or args.delete_torrc_config) and not args.port:
    logging.error('for creating or deleting torrc configs you have to specify at least port number.')
    exit(1)
if args.show_ip and not (args.port or args.country):
    logger.error('for showing a client ip you have to specify port or country of client.')
    exit(1)

if __name__ == "__main__":
    tm = TManager()

    temp = dict()
    if args.port:
        temp['port'] = args.port if int(args.port) % 2 == 0 else str(int(args.port) + 1)
    if args.country:
        temp['country'] = args.country

    if args.start_client:
        tm.start_connection(**temp)
    elif args.stop_client:
        tm.kill_tor_connection(**temp)
    elif args.start_all_clients:
        tm.load_clients_cache()
        tm.read_configs()
        tm.start_all_connections()
    elif args.stop_running_clients:
        tm.kill_all_connections()

    if args.renew_ip:
        if args.port or args.country:
            tm.renew_connection(**temp)
        else:
            tm.renew_all_connections()

    if args.show_ip:
        info = tm.get_ip_info(**temp)
        ip = info['ip'] if info is not None else 'nan'
        print(f'127.0.0.1:{temp.__str__().strip("{}")} {ip}')

    if args.create_new_torrc_config:
        tm.create_torrc_config(**temp)

    if args.delete_torrc_config:
        tm.delete_torrc_config(**temp)

    if args.show_running_clients:
        tm.output_running_clients()

    if args.show_configs:
        tm.output_configs()

    tm.write_running_clients_configs()
