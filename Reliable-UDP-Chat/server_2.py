'''
This module defines the behaviour of server in your Chat Application
'''
import sys
import getopt
import socket
import util
from queue import Queue
from threading import Thread


class Server:
    '''
    This is the main Server Class with custom reliable transport.
    '''

    def __init__(self, dest, port, window):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(None)
        self.sock.bind((self.server_addr, self.server_port))

        self.clients = {}  # username : addr
        self.buffers = {}  # addr : {"chunks": [], "expected": seq}
        self.clients_seq = {}  # addr : next seq num
        self.msg_queue = Queue()


    def start(self):
        '''
        Launch receiver and main loop threads.
        Receiver thread listens for packets being sent and places them in the queue.
        Main loop handles messages in the queue.
        '''

        # start recv and message loops
        Thread(target=self.recv_loop, daemon=True).start()
        Thread(target=self.message_loop, daemon=True).start()

        # keep main thread alive until keyboard interrupt
        try:
            while True:
                pass
        except KeyboardInterrupt:
            sys.exit(0)

    def recv_loop(self):
        while True:
            message, addr, next_seq = util.receive_msg(self.sock, self.buffers)
            if message and addr:
                self.clients_seq[addr] = next_seq
                self.msg_queue.put((message, addr))

    def message_loop(self):
        while True:
            message, addr = self.msg_queue.get()
            self.handle_message(message, addr)

    def handle_message(self, message, addr):
        # extract command and handle accordingly
        msg_parts = message.split()
        cmd = msg_parts[0]

        if cmd == "disconnect":
            self.delete_client(msg_parts)
        elif cmd == "join":
            self.add_client(msg_parts, addr)
        elif cmd == "send_message":
            self.send_chat_msg(msg_parts, addr)
        elif cmd == "request_users_list":
            self.send_users_list(addr)
        else:
            self.unknown_cmd(addr)

    def unknown_cmd(self, addr):
        # get username from address
        username = None
        for name, stored_addr in self.clients.items():
            if stored_addr == addr:
                username = name

        if username:
            util.reliable_send_msg(self.sock, "err_unknown_message", 2, addr,
                                   self.clients_seq[addr])
            # disconnect client
            del self.clients[username]
            print(f"disconnected: {username} sent unknown command")

    def delete_client(self, msg_parts):
        username = msg_parts[2]

        # ensure user exists
        if username in self.clients.keys():
            del self.clients[username]
            print(f"disconnected: {username}")

    def add_client(self, msg_parts, addr):
        username = msg_parts[2]

        # check for max number of clients
        if len(self.clients) >= util.MAX_NUM_CLIENTS:
            util.reliable_send_msg(self.sock, "err_server_full", 2, addr,
                                   self.clients_seq[addr])
            print(f"disconnected: server full")

        # check if username already exists
        if username in self.clients.keys():
            util.reliable_send_msg(self.sock, "err_username_unavailable", 2, addr,
                                   self.clients_seq[addr])
            print(f"disconnected: username not available")

        self.clients[username] = addr
        print(f"join: {username}")

    def send_users_list(self, addr):
        # ensure user exists
        username = None
        for name, stored_addr in self.clients.items():
            if stored_addr == addr:
                username = name

        if username:
            name_list = sorted(self.clients.keys())
            response_str = f"{len(name_list)} {' '.join(name_list)}"
            print("sending users list:", response_str)
            util.reliable_send_msg(self.sock, "response_users_list", 3, addr,
                                   self.clients_seq[addr], response_str)
            print(f"request_users_list: {username}")

    def send_chat_msg(self, msg_parts, addr):
        # ensure sender exists
        sender_name = None
        for name, stored_addr in self.clients.items():
            if stored_addr == addr:
                sender_name = name

        if sender_name:
            print(f"msg: {sender_name}")

            num_recv = int(msg_parts[2])
            recipients = msg_parts[3:3 + num_recv]
            msg = " ".join(msg_parts[3 + num_recv:])

            # deliver msg to each recipient
            for recipient in recipients:
                # ensure recipient exists and get address
                recv_addr = self.clients.get(recipient)
                msg_formatted = f"1 {sender_name} {msg}"
                if recv_addr:
                    util.reliable_send_msg(self.sock, "forward_message", 4, recv_addr,
                                           self.clients_seq[addr], msg_formatted)
                else:
                    print(f"msg: {sender_name} to non-existent user {recipient}")


# Do not change below part of code

if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our module completion
        '''
        print("Server")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW | --window=WINDOW The window size, default is 3")
        print("-h | --help Print this help")


    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "p:a:w", ["port=", "address=", "window="])
    except getopt.GetoptError:
        helper()
        exit()

    PORT = 15000
    DEST = "localhost"
    WINDOW = 3

    for o, a in OPTS:
        if o in ("-p", "--port="):
            PORT = int(a)
        elif o in ("-a", "--address="):
            DEST = a
        elif o in ("-w", "--window="):
            WINDOW = a

    SERVER = Server(DEST, PORT, WINDOW)
    try:
        SERVER.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
