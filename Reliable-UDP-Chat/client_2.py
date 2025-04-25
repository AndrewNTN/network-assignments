'''
This module defines the behaviour of a client in your Chat Application
'''
import sys
import getopt
import socket
import random
from threading import Thread
import os
import util

'''
Write your code inside this class. 
In the start() function, you will read user-input and act accordingly.
receive_handler() function is running another thread and you have to listen 
for incoming messages in this function.
'''


class Client:
    '''
    This is the main Client Class with custom reliable transport.
    '''

    def __init__(self, username, dest, port, window_size):
        self.server_addr = dest
        self.server_port = port
        self.send_addr = (self.server_addr, self.server_port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(None)
        self.sock.bind(('', random.randint(10000, 40000)))
        self.name = username
        self.buffers = {}  # addr : {"chunks": [], "expected": seq}
        self.next_seq = None
        self.started = False

    def start(self):
        '''
        Main Loop is here
        Start by sending the server a JOIN message.
        Use make_message() and make_util() functions from util.py to make your first join packet
        Waits for userinput and then process it

        A separate thread is started to receive messages from the server, then
        '''

        # send join message to server
        init_seq = random.randint(1, 100000)
        util.reliable_send_msg(self.sock, "join", 1, self.send_addr, init_seq, message=self.name)
        self.next_seq = init_seq + 1
        self.started = True
        while True:
            # get user input
            msg = input()
            if msg:
                self.handle_message(msg)

    def handle_message(self, msg):
        # extract command and handle accordingly
        msg_parts = msg.split()
        cmd = msg_parts[0]

        if cmd == "msg":
            self.chat(msg_parts)
        elif cmd == "list":
            self.list()
        elif cmd == "help":
            self.help()
        elif cmd == "quit":
            self.quit()
            sys.exit(0)
        else:
            print("incorrect userinput format")

    def receive_handler(self):
        '''
        Waits for a message from server and process it accordingly
        '''
        while True:
            if not self.started:
                continue

            message, _, next_seq = util.receive_msg(self.sock, self.buffers)
            # send message received from packets to handler
            if message:
                self.next_seq = next_seq
                self.handle_server_msg(message)

    def handle_server_msg(self, message):
        # extract command and handle accordingly
        msg_parts = message.split()
        res = msg_parts[0]

        if res == "response_users_list":
            self.users_list_res(msg_parts)
        elif res == "forward_message":
            self.fwd_message(msg_parts)
        elif res == "err_username_unavailable":
            print("disconnected: username not available")
            sys.exit(0)
        elif res == "err_server_full":
            print("disconnected: server full")
            sys.exit(0)
        elif res == "err_unknown_message":
            print("disconnected: server received an unknown command")
            sys.exit(0)

    def chat(self, msg_parts):
        # ensure correct formatting
        if len(msg_parts) < 3:  # need msg cmd, a user, and msg at least
            print("incorrect userinput format")
            return

        num_recv = msg_parts[1]
        if num_recv.isdigit():
            num_recv = int(num_recv)
        else:
            print("incorrect userinput format")
            return

        if (num_recv < 1  # ensure at least 1 recipient
                or len(msg_parts) < num_recv + 3):  # ensure recipients are named
            print("incorrect userinput format")
            return

        recipients = msg_parts[2: 2 + num_recv]
        message = " ".join(msg_parts[2 + num_recv:])

        # send msg to server
        msg_formatted = f"{num_recv} {' '.join(recipients)} {message}"
        util.reliable_send_msg(self.sock, "send_message", 4, self.send_addr,
                               self.next_seq, message=msg_formatted)

    def list(self):
        # provie user with list of connected users
        util.reliable_send_msg(self.sock, "request_users_list", 2,
                               self.send_addr, self.next_seq)

    def help(self):
        # provide user with list of commands
        print("List of Commands:\n"
              "msg <number_of_users> <username1> <username2> … <message>\n"
              "list\n"
              "help\n"
              "quit\n")

    def quit(self):
        # send quit message
        util.reliable_send_msg(self.sock, "disconnect", 1,
                               self.send_addr, self.next_seq, message=self.name)
        print("quitting")

    def users_list_res(self, msg_parts):
        # display users list response from server
        num_users = int(msg_parts[2])
        user_list = msg_parts[3:3 + num_users]

        print(f"list: {' '.join(user_list)}")

    def fwd_message(self, msg_parts):
        # display fwd msg to user
        sender_name = msg_parts[3]
        msg = " ".join(msg_parts[4:])

        print(f"msg: {sender_name}: {msg}")


# Do not change below part of code
if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our Client module completion
        '''
        print("Client")
        print("-u username | --user=username The username of Client")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW_SIZE | --window=WINDOW_SIZE The window_size, defaults to 3")
        print("-h | --help Print this help")


    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "u:p:a:w", ["user=", "port=", "address=", "window="])
    except getopt.error:
        helper()
        exit(1)

    PORT = 15000
    DEST = "localhost"
    USER_NAME = None
    WINDOW_SIZE = 3
    for o, a in OPTS:
        if o in ("-u", "--user="):
            USER_NAME = a
        elif o in ("-p", "--port="):
            PORT = int(a)
        elif o in ("-a", "--address="):
            DEST = a
        elif o in ("-w", "--window="):
            WINDOW_SIZE = a

    if USER_NAME is None:
        print("Missing Username.")
        helper()
        exit(1)

    S = Client(USER_NAME, DEST, PORT, WINDOW_SIZE)
    try:
        # Start receiving Messages
        T = Thread(target=S.receive_handler)
        T.daemon = True
        T.start()
        # Start Client
        S.start()
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
