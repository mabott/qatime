#!/usr/bin/env python

""" Grabbed Tiny Syslog Server from a github project
Tiny Syslog Server in Python.
This is a tiny syslog server that is able to receive UDP based syslog
entries on a specified port and save them to a file.
That's it... it does nothing else...
There are a few configuration parameters."""

import logging
import time
import threading
import socketserver
import redis

LOG_FILE 	= 'qumulo_audit.log'
HOST		= '192.168.11.156'
UDP_PORT	= 1514

listening = False

logging.basicConfig(level=logging.INFO, format='%(message)s', datefmt='', filename=LOG_FILE, filemode='a')

R = redis.Redis()


class SyslogUDPHandler(socketserver.BaseRequestHandler):

	def handle(self):
		data = bytes.decode(self.request[0].strip())
		# data = self.request[0].strip()
		# socket = self.request[1]
		# print(( "%s : " % self.client_address[0], str(data)))
		extract_keyvalue(str(data))
		# logging.info(str(data))


def extract_keyvalue(data):
	list = data.split(',')
	timestamp = list[0]
	# file_id = list[7]
	file_path = list[8].strip('"') # if we don't strip quotes redis escapes
	print(list)
	print(file_path)
	print(timestamp)
	R.set(file_path, timestamp)


if __name__ == "__main__":
	listening = True
	try:
		# Redis

		# UDP server
		udpServer = socketserver.UDPServer((HOST, UDP_PORT), SyslogUDPHandler)
		udpThread = threading.Thread(target=udpServer.serve_forever)
		udpThread.daemon = True
		udpThread.start()

		while True:
			time.sleep(1)

	except (IOError, SystemExit):
		raise
	except KeyboardInterrupt:
		listening = False
		udpServer.shutdown()
		udpServer.server_close()
		print ("Crtl+C Pressed. Shutting down.")