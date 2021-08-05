import configparser
from dataclasses import dataclass
from qumulo.rest_client import RestClient


@dataclass(frozen=True)
class SyslogConfig:
    log_file: str
    host: str
    port: int


@dataclass(frozen=True)
class RestConfig:
    address: str
    port: int
    username: str
    password: str

    def make_client(self) -> RestClient:
        client = RestClient(address=self.address, port=self.port)
        client.login(username=self.username, password=self.password)
        return client


@dataclass(frozen=True)
class TestConfig:
    base_path: str
    folder_name: str


@dataclass(frozen=True)
class Config:
    syslog: SyslogConfig
    rest: RestConfig
    test: TestConfig


def load_config(filename: str = "qatime_config.ini") -> Config:
    config = configparser.ConfigParser()
    config.read(filename)

    syslog = SyslogConfig(
        log_file=config["syslog"]["LOG_FILE"],
        host=config["syslog"]["HOST"],
        port=int(config["syslog"]["UDP_PORT"]),
    )
    rest = RestConfig(
        address=config["qumulo"]["QADDRESS"],
        port=int(config["qumulo"]["QPORT"]),
        username=config["qumulo"]["QLOGIN"],
        password=config["qumulo"]["QPASS"],
    )
    test = TestConfig(
        base_path=config["test"]["BASE_PATH"],
        folder_name=config["test"]["TEST_FOLDER"],
    )

    return Config(
        syslog=syslog,
        rest=rest,
        test=test,
    )
