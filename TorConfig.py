import getpass
import json
import logging
import os
import threading
import time

from stem import process, Signal
from stem.control import Controller
from stem.util import conf

from get_port_ip import get_port_ip


class TorConfig:
    """
    Attributes:
        config_dict:dict:
            output of stem.util.conf.get_config().load()

        config_file_path:str:
            path of torrc config file

        control_port:int:
            torrc control port

        socks_port:int:
            torrc socks port

        exit_nodes:list:
            torrc exit nodes

        hashed_control_password:str:
            torrc HashedControlPassword

        data_directory:str:
            torrc data directory

        ip_info:dict:
            keys: 'ip', 'country', 'region', 'city'

        connection:subprocess.Popen:
            tor connection object

        password:str:
            original unhashed torrc password (which will be prompted to acquire)

        pid:
            pid of connection
    """

    def __init__(self, config_file_path=None):
        """
        Args:
            config_file_path: str:
                if provided, config_dict will be loaded.
        """
        self.config_file_path = config_file_path  # str

        self.config_dict = None  # dict casted from conf.Config object
        self.control_port = None  # int
        self.socks_port = None  # int
        self.exit_nodes = None  # list
        self.hashed_control_password = None  # str
        self.data_directory = None  # str

        self.ip_info = None  # dict
        self.pid = None  # int
        self.connection = None  # subprocess object

        self.password = None  # str

        if self.config_file_path:
            self.load_conf_dict()

        if os.path.basename(self.config_file_path) == 'torrc':
            self.get_tor_ip_dict()

        # set up logging
        self._logger_ = logging.getLogger(__name__)
        self._logger_.setLevel(logging.INFO)

        file_handler = logging.FileHandler(filename="TorConfig.log")
        file_handler.setLevel(logging.INFO)
        self._logger_.addHandler(file_handler)

    def __str__(self):
        return f"{os.path.basename(self.config_file_path)} {self.socks_port} {self.exit_nodes}" + \
               f" {self.ip_info['ip']}" if self.pid is not None else ""

    def __getitem__(self, item):
        try:
            obj = getattr(self, item)
            return obj
        except Exception:
            raise KeyError(f"object has no attribute {item}")

    @property
    def config_file_path(self):
        return self._config_file_path_

    @config_file_path.setter
    def config_file_path(self, file_path):
        if file_path is None:
            self._config_file_path_ = file_path

        elif os.path.isfile(file_path):
            self._config_file_path_ = file_path

        else:
            raise NotADirectoryError("config path is not a directory")

    @property
    def control_port(self):
        return self._control_port_

    @control_port.setter
    def control_port(self, port):
        if port is None:
            self._control_port_ = port

        elif isinstance(port, list):
            self._control_port_ = int(port[0])

        elif isinstance(port, str):
            if port.isdecimal():
                self._control_port_ = int(port)

        elif isinstance(port, int):
            self._control_port_ = port

        else:
            raise ValueError(f"control_port cannot be of type {type(port)}")

    @property
    def socks_port(self):
        return self._socks_port_

    @socks_port.setter
    def socks_port(self, port):
        if port is None:
            self._socks_port_ = port

        elif isinstance(port, list):
            self._socks_port_ = int(port[0])

        elif isinstance(port, str):
            if port.isdecimal():
                self._socks_port_ = int(port)

        elif isinstance(port, int):
            self._socks_port_ = port

        else:
            raise ValueError(f"socks_port cannot be of type {type(port)}")

    @property
    def data_directory(self):
        return self._data_directory_

    @data_directory.setter
    def data_directory(self, dds):
        if dds is None:
            self._data_directory_ = dds

        elif isinstance(dds, str):
            if os.path.isdir(dds):
                self._data_directory_ = dds

        elif isinstance(dds, list):
            for dd in dds:
                if isinstance(dd, str):
                    self._data_directory_ = dd

                    if not os.path.isdir(dd):
                        os.mkdir(dd)

        else:
            raise ValueError(f"data_directory cannot be of type {type(dds)}")

    @property
    def exit_nodes(self):
        return self._exit_nodes_

    @exit_nodes.setter
    def exit_nodes(self, ens):
        if ens is None:
            self._exit_nodes_ = ens

        elif isinstance(ens, list):
            with open("tor-countries.json", 'r') as fp:
                tor_ens = json.load(fp)

            for en in ens:
                if en.strip('{}') not in tor_ens.keys():
                    raise ValueError(f"tor config exit node '{en}' not in tor predefined countries")
            else:
                self._exit_nodes_ = list(map(lambda x: x.strip("{}"), ens))

        else:
            raise ValueError(f"exit_nodes cannot be of type {type(ens)}")

    @property
    def hashed_control_password(self):
        return self._hashed_control_password_

    @hashed_control_password.setter
    def hashed_control_password(self, psw):
        if psw is None:
            self._hashed_control_password_ = psw

        elif isinstance(psw, list):
            if isinstance(psw[0], str):
                if psw[0][:2] == '16':
                    if len(psw[0][3:]) == 58:
                        self._hashed_control_password_ = psw[0]

        elif isinstance(psw, str):
            if psw[:2] == '16':
                if len(psw[3:]) == 58:
                    self._hashed_control_password_ = psw

        else:
            raise ValueError(f"hashed_control_password cannot be of type {type(psw)}")

    def __getstate__(self):
        attrs = [attr for attr in dir(self) if attr[0] != '_' and attr[-1] != '_']

        args = {key: getattr(self, key) for key in attrs}

        del args["connection"]
        return args

    def __setstate__(self, state):
        # set up logging
        self._logger_ = logging.getLogger(__name__)
        self._logger_.setLevel(logging.INFO)

        file_handler = logging.FileHandler(filename="TorConfig.log")
        file_handler.setLevel(logging.INFO)
        self._logger_.addHandler(file_handler)

        self.exit_nodes = None
        self.hashed_control_password = None

        self.ip_info = None
        self.pid = None
        self.connection = None

        self.password = None

        for key, value in state.items():
            setattr(self, key, value)

        if os.path.basename(self.config_file_path) == 'torrc':
            self.get_tor_ip_dict()

    def custom_init(self, kwargs: dict):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def kill_connection(self):
        """
        If connection was not None, it'll kill the subprocess.Popen object.
        Else if pid was not None, it'll use kill signal to kill the tor process.
        """
        if self.connection is not None:
            self.connection.kill()
            self.connection = None
            self.pid = None
            self.ip_info = None
            self._logger_.info(f"successfully killed config[{self.config_file_path}] connection")
        else:
            if self.pid is not None and self.pid != -1:
                os.popen(f"kill -KILL {self.pid}")
                self.pid = None
                self.ip_info = None
                self._logger_.info(f"successfully killed config[{self.config_file_path}] connection")

    def create_connection_from_config(self):
        """
        Sets a timer for 60 seconds and if connection wasn't created successfully by then, it'll raise an Exception.
        Calls get_tor_ip_dict to get the new ip_info
        """
        if self.connection is not None:
            start_time = time.time()
            self._logger_.info("creating connection from config")

            def check_time(st):
                while True:
                    time.sleep(2)
                    self._logger_.info(
                        f"{int(time.time() - st)} seconds has elapsed, still trying to create the connection.")
                    if self.connection is None:
                        if time.time() - st > 60:
                            raise Exception("something went wrong. probably openconnect is conneted...")
                    else:
                        self._logger_.info(f"successfully created connection[pid={self.connection.pid}] "
                                           f"after {int(time.time() - st)} seconds")
                        return

            threading.Thread(target=check_time, args=(start_time,)).start()
            self.connection = process.launch_tor_with_config(config=self.config_dict)
            self.pid = self.connection.pid
            self.get_tor_ip_dict()

    def load_conf_dict(self):
        """
        Loads configuration from config_file_path to config_dict
        """
        config_object = conf.get_config('config_handler')
        config_object.load(self.config_file_path)

        self.config_dict = dict(config_object)

        for key in config_object.keys():
            if 'ControlPort' in key:
                self.control_port = config_object[key]
            if 'SocksPort' in key:
                self.socks_port = config_object[key]
            if 'ExitNodes' in key:
                self.exit_nodes = config_object[key]
            if 'DataDirectory' in key:
                self.data_directory = config_object[key]
            if 'HashedControlPassword' in key:
                self.hashed_control_password = config_object[key]
            elif not self.hashed_control_password:
                main_torrc_config_object = conf.get_config('main_handler')
                main_torrc_config_object.load("/etc/tor/torrc")
                self.hashed_control_password = main_torrc_config_object["HashedControlPassword"]

            # TODO: complete this list

        config_object.clear()

    def renew_ip(self):
        """
        Calls torrc connection restart signal NEWNYM using stem
        """
        if not self.password:
            self.password = getpass.unix_getpass(prompt=f"tor config file {self.config_file_path}\npassword:")

        try:
            with Controller.from_port(port=self.control_port) as controller:
                controller.authenticate(password=self.password)
                controller.signal(Signal.NEWNYM)

            if self.connection is not None and self.connection != -1:
                self.pid = self.connection.pid
            self.get_tor_ip_dict()
            self._logger_.info(f"successfully renew-ed config[{self.config_file_path}] connection[pid={self.pid}]\n"
                               f"new ip:{self.ip_info['country'].lower()}:{self.ip_info['ip']}:{self.socks_port}")
        except Exception as e:
            self._logger_.error(f"renew-ing connection for config[{self.config_file_path}] faced an Exception:\n"
                                f"\t{str(e)}")

    def get_tor_ip_dict(self):
        """
        Calls file get_port_ip.py using --port and --file arguments and loads its output to ip_info
        """
        self.ip_info = get_port_ip(port=self.socks_port)


if __name__ == "__main__":
    obj = TorConfig("/etc/tor/torrc.5")
    obj.create_connection_from_config()
    print(obj.ip_info)
    obj.renew_ip()
    print(obj.ip_info)
    obj.kill_connection()
