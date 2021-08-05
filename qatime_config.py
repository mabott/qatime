import configparser
from dataclasses import dataclass


@dataclass(frozen=True)
class SyslogConfig:
    log_file: str
    host: str
    udp_port: int


@dataclass(frozen=True)
class AtimeConfig:
    nfs_mount: str
    batch_size: int


@dataclass(frozen=True)
class RestConfig:
    address: str
    port: int
    username: str
    password: str


@dataclass(frozen=True)
class TestConfig:
    base_path: str
    folder_name: str


@dataclass(frozen=True)
class Config:
    syslog: SyslogConfig
    atime: AtimeConfig
    rest: RestConfig
    test: TestConfig


def load_config(filename: str = "qatime_config.ini") -> Config:
    config = configparser.ConfigParser()
    config.read(filename)

    syslog = SyslogConfig(
        log_file=config["syslog"]["LOG_FILE"],
        host=config["syslog"]["HOST"],
        udp_port=int(config["syslog"]["UDP_PORT"]),
    )
    atime = AtimeConfig(
        nfs_mount=config["atime"]["NFS_MOUNT"],
        batch_size=int(config["atime"]["BATCH_SIZE"]),
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
        atime=atime,
        rest=rest,
        test=test,
    )
