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

        self.clients = {}  # conn_socket : Username

    def start(self):
        '''
        Main loop.
        continue receiving messages from Clients and processing it.
        '''

        while True:
            try:
                # wait for a client connection
                conn_socket, addr = self.sock.accept()

                # get message
                message = conn_socket.recv(4096).decode()

                # handle message
                if message:
                    self.handle_message(message, conn_socket)

            except Exception as e:
                print(f"Error: {e}")

    def handle_message(self, message, conn_socket):
        msg_type, seqno, data, checksum = util.parse_packet(message)

        if data == "disconnect":
            print(f"disconnected: {self.clients[conn_socket]}")
            del self.clients[conn_socket]

    def add_client(self, client_name, conn_socket):
        if len(self.clients) >= util.MAX_NUM_CLIENTS:
            # send client disconnected: full
            pass

        if client_name in self.clients.values():
            # send client disconnected: username not available
            pass

        self.clients[client_name] = conn_socket


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
