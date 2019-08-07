# !/usr/bin/python3
import logging
import os
import pickle

from prettytable import PrettyTable

from TorConfig import TorConfig


class TManager:
    def __init__(self):
        self.tor_manager_path = os.path.dirname(__file__)

        self.CLIENTS_CACHE_DIR = os.path.join(os.path.dirname(__file__), "clients_cache_dir")
        if not os.path.isdir(self.CLIENTS_CACHE_DIR):
            os.mkdir(self.CLIENTS_CACHE_DIR)

        self.CONFIGS_DIR = "/etc/tor"

        self.clients = list()
        self.load_clients_cache()
        self.read_configs()

    def __str__(self):
        return_str = str()
        for client in self.clients:
            return_str += str(client)
            return_str += '\n'

        return return_str

    def __getitem__(self, item):
        if isinstance(item, int):
            if item > 1000:
                for client in self.clients:
                    if int(client.socks_port) == item or int(client.control_port) == item:
                        return client
            else:
                return self.clients[item]

        elif isinstance(item, str):  # country
            for client in self.clients:
                if item in client.exit_nodes:
                    return client

    def __repr__(self):
        return self.__str__()

    def __iter__(self):
        return self

    def __next__(self):
        for client in self.clients:
            yield client
        raise StopIteration

    def __add__(self, other):
        if isinstance(other, TManager):
            self.clients.extend(other.clients)
        else:
            raise TypeError(f"cannot add type TManager with type {type(other)}")

    def __bool__(self):
        if len(self.clients) != 0:
            return True
        else:
            return False

    def __contains__(self, item):
        if isinstance(item, int):
            for client in self.clients:
                if item == int(client.socks_port) or item == int(client.control_port):
                    return True
            else:
                return False
        elif isinstance(item, str):  # country
            for client in self.clients:
                if item in client.exit_nodes:
                    return True
            else:
                return False

    def __len__(self):
        return len(self.clients)

    def read_configs(self):
        """
        Reads custom and default torrc configurations from tor path and loads them all in clients using CONFIGS_DIR
        """
        for client in self.clients:
            if client.config_file_path is None:
                del client

        if 'torrc' not in [each for each in os.listdir(self.CONFIGS_DIR) if each == 'torrc']:
            logging.critical("no default torrc file found in tor configs path")

        for torrc in os.listdir(self.CONFIGS_DIR):
            # skip loaded clients
            if torrc in [os.path.basename(client.config_file_path) for client in self.clients if
                         client.config_file_path is not None]:
                continue

            # Default torrc file
            if 'torrc' == torrc:
                self.clients.append(TorConfig(os.path.join(self.CONFIGS_DIR, torrc)))
                self.clients[-1].connection = -1
                self.clients[-1].pid = -1

            # exclude non-torrc files
            if 'torrc.' not in torrc:
                continue

            # torrc custom files
            self.clients.append(TorConfig(os.path.join(self.CONFIGS_DIR, torrc)))

    def load_clients_cache(self):
        """
        Unpickles tor clients from CLIENTS_CACHE_DIR and loads them into clients.
        """
        for client in os.listdir(self.CLIENTS_CACHE_DIR):
            if 'client.' in client:
                with open(os.path.join(self.CLIENTS_CACHE_DIR, client), 'rb') as fp:
                    client_obj = pickle.load(fp)

                # remove config file after loading it
                os.remove(os.path.join(self.CLIENTS_CACHE_DIR, client))

                for cli in self.clients:
                    if client_obj == cli.socks_port:
                        cli.custom_init({
                            attr: getattr(client_obj, attr)
                            for attr in dir(client_obj) if attr[0] != '_' and attr[-1] != '_'
                        })
                else:
                    self.clients.append(client_obj)

    def write_running_client_config(self, client):
        """
        Unpickle the given client
        Args:
            client: TorConfig
        """
        with open(os.path.join(self.CLIENTS_CACHE_DIR, f'client.{client.socks_port}')) as fp:
            pickle.dump(client, fp)

    def write_running_clients_configs(self):
        """
        Writes the running clients from clients to the client pickled files
        """
        for client in self.clients:
            with open(os.path.join(self.CLIENTS_CACHE_DIR, f'client.{client.socks_port}'), 'wb') as fp:
                pickle.dump(client, fp)

    def renew_connection(self, **kwargs):
        """
        Restarts connection using stem.control.Controller
        """
        for client in self.clients:
            if client.pid is not None:
                if 'port' in kwargs:
                    if client.socks_port == kwargs['port']:
                        client.renew_ip()
                if 'country' in kwargs:
                    if kwargs['country'] in client.exit_nodes:
                        client.renew_ip()
            else:
                self.start_connection(port=client.socks_port)

    def renew_all_connections(self):
        for client in self.clients:
            if client.pid is not None:
                client.renew_ip()

    def kill_tor_connection(self, **kwargs):
        """
        Iterates through clients and finds the client wanted, then kills it.

        Args:
            **kwargs:
                Keyword Args:
                    pid: finds the client with the same pid
                    port: finds the client with the same socks port

        """
        for client in self.clients:
            if client.connection is not None:
                if 'pid' in kwargs:
                    if client.pid == kwargs['pid']:
                        client.kill_connection()
                        self.write_running_client_config(client)
                        del client
                        break

                elif 'port' in kwargs:
                    if client.socks_port == kwargs['port']:
                        client.kill_connection()
                        self.write_running_client_config(client)
                        del client
                        break
                else:
                    raise OSError("you have to specify pid or port")

    def get_ip_info(self, **kwargs):
        """
        Args:
            **kwargs:
                port: int
                country: str

        Returns:
            ip_info of client
        """
        for client in self.clients:
            if 'port' in kwargs:
                if client.socks_port == kwargs['port']:
                    return client.ip_info
            if 'country' in kwargs:
                if kwargs['country'] in client.exit_nodes:
                    return client.ip_info

    def start_connection(self, **kwargs):
        """
        Starts connection
        Args:
            **kwargs:
                port: int
                country: str

        """
        for client in self.clients:
            if 'port' in kwargs:
                if client.socks_port == kwargs['port']:
                    client.create_connection_from_config()
            if 'country' in kwargs:
                if kwargs['country'] in client.exit_nodes:
                    client.create_connection_from_config()

    def start_all_connections(self):
        """
        Start connections for all configs which are not started from tor config path
        """
        for client in self.clients:
            if client.config_file_path == '/etc/tor/torrc':
                # client.renew_ip()
                pass
            else:
                if client.connection is not None:
                    continue
                elif client.pid is not None:
                    # client.renew_ip()
                    pass
                else:
                    client.create_connection_from_config()

    def kill_all_connections(self):
        """
        kills all running processes
        """
        for client in self.clients:
            self.kill_tor_connection(port=f'{client.socks_port}')

    def output_configs(self):
        """
        print the contents of configs
        """
        table = PrettyTable()
        table.field_names = ["file name", "socks port", "control port", "exit nodes", "data directory",
                             "connection pid", "ip"]
        table.align['file name'] = 'l'
        table.align['socks port'] = 'l'
        table.align['control port'] = 'l'
        table.align['data directory'] = 'l'
        table.align['exit nodes'] = 'l'
        table.align['connection pid'] = 'l'
        table.align['ip'] = 'l'

        for client in self.clients:

            pid = client.pid
            if pid is None:
                pid = "N/A"

            ip = client.ip_info
            if ip is None:
                ip = "N/A"
            else:
                ip = ip['ip']

            table.add_row(
                (
                    os.path.basename(client.config_file_path),
                    client.socks_port,
                    client.control_port,
                    str(client.exit_nodes).strip("[]"),
                    client.data_directory,
                    pid,
                    ip
                )
            )

        print("tor configs table")
        print(table)

    def output_running_clients(self):
        """
        print the contents of running processes with prettyTable
        """
        table = PrettyTable()
        table.field_names = ["pid", "port", "ip", "country", "region", "city"]
        table.align['pid'] = 'r'
        table.align['port'] = 'r'
        table.align['ip'] = 'r'
        table.align['country'] = 'l'
        table.align['region'] = 'l'
        table.align['city'] = 'l'

        for client in self.clients:
            if client.ip_info is not None:
                table.add_row(
                    (client.pid,
                     client.socks_port,
                     client.ip_info['ip'],
                     client.ip_info["country"],
                     client.ip_info['region'],
                     client.ip_info['city'])
                )

        print("tor running clients table")
        print(table)

    def create_torrc_config(self, **kwargs):
        """
        Create a new torrc config file in CONFIGS_DIR
        Keyword Args:
            port: int
            data-directory: str
            countries: list
        """
        max_num = 0
        for torrc in os.listdir(self.CONFIGS_DIR):
            # exclude non-torrc files
            if 'torrc.' not in torrc:
                continue

            # torrc custom files
            max_num = max(max_num, int(torrc[torrc.find('.') + 1:]))

        file_data = str()
        if 'port' in kwargs:
            file_data += f'SocksPort {kwargs["port"]}\n'
            file_data += f'ControlPort {kwargs["port"] + 1}\n'
        else:
            return False

        if 'data-directory' in kwargs:
            file_data += f'DataDirectory {os.path.abspath(kwargs["data-directory"])}\n'
        else:
            path = os.path.join('/var/lib', f'tor{int(max_num + 1)}')
            os.mkdir(path)
            file_data += f'DataDirectory {path}'

        if 'countries' in kwargs:
            exit_nodes = str()
            for country in kwargs['countries']:
                if country not in exit_nodes.split()[0]:
                    exit_nodes += ', '

                exit_nodes += "{%s}" % country

            file_data += f'ExitNodes {exit_nodes}\n'

        with open(os.path.join(self.CONFIGS_DIR, f'torrc.{max_num + 1}'), 'w') as fp:
            fp.write(file_data)

    def delete_torrc_config(self, **kwargs):
        """
        Deletes a torrc config file from CONFIGS_DIR
        Keyword Args:
            port: int
            data-directory: str
            countries: list
        """
        for client in self.clients:
            if 'port' in kwargs:
                if kwargs['port'] == client.socks_port:
                    os.remove(client.config_file_path)
                    del client
                    break
            if 'country' in kwargs:
                if kwargs['country'] in client.exit_nodes:
                    os.remove(client.config_file_path)
                    os.remove(os.path.join(self.CLIENTS_CACHE_DIR, f'client.{client.socks_port}'))
                    del client
                    break
