'''
This module defines the behaviour of server in your Chat Application
'''
import sys
import getopt
import socket
import util


class Server:
    '''
    This is the main Server Class. You will  write Server code inside this class.
    '''

    def __init__(self, dest, port, window):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(None)
        self.sock.bind((self.server_addr, self.server_port))

        self.clients = {}  # username : addr

    def start(self):
        '''
        Main loop.
        continue receiving messages from Clients and processing it.
        '''

        while True:
            # wait for a client message
            message, addr = self.sock.recvfrom(4096)

            # handle message
            if message:
                message = message.decode()
                self.handle_message(message, addr)

    def handle_message(self, message, addr):
        msg_type, seqno, data, checksum = util.parse_packet(message)
        msg_parts = data.split()
        cmd = msg_parts[0]

        if cmd == "disconnect":
            self.delete_client(msg_parts, addr)
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
            self.send_msg("err_unknown_message", 2, addr)

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
            self.send_msg("err_server_full", 2, addr)
            print(f"disconnected: server full")

        # check if username already exists
        if username in self.clients.keys():
            self.send_msg("err_username_unavailable", 2, addr)
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
            self.send_msg("response_users_list", 3, addr, response_str)
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
                if recv_addr:
                    self.send_msg("forward_message", 4, recv_addr, msg)
                else:
                    print(f"msg: {sender_name} to non-existent user {recipient}")

    def send_msg(self, msg_type, msg_format, addr, message=None):
        msg = util.make_message(msg_type, msg_format, message=message)
        packet = util.make_packet(msg=msg)
        self.sock.sendto(packet.encode(), addr)


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
