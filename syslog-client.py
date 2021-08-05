#!/usr/bin/env python

import argparse
import logging
import logging.handlers

from typing import Mapping

LOG_LEVELS: Mapping[str, int] = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}


def main() -> None:
    parser = argparse.ArgumentParser(__file__, description="A syslog message generator")
    parser.add_argument(
        "--address",
        "-a",
        default="localhost",
        help="The syslog message recipient address",
    )
    parser.add_argument(
        "--port", "-p", type=int, default=5514, help="The syslog message recipient port"
    )
    parser.add_argument(
        "--level",
        "-l",
        default="DEBUG",
        help="The syslog message log level",
        choices=LOG_LEVELS.keys(),
    )
    parser.add_argument("--message", "-m", required=True, help="The syslog message")

    args = parser.parse_args()
    level = LOG_LEVELS.get(args.level, logging.NOTSET)

    syslogger = logging.getLogger("SyslogLogger")
    syslogger.setLevel(level)
    handler = logging.handlers.SysLogHandler(
        address=(args.address, args.port), facility=19
    )
    syslogger.addHandler(handler)
    syslogger.log(level=level, msg=args.message)


if __name__ == "__main__":
    main()
