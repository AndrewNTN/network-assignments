from socket import *
import os

server_port = 8080
max_backlog_connections = 1
cache_dir = 'cache'
# create cache directory if it doesn't exist
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)


def parse_url(url):
    if url.startswith('/'):
        url = url[1:]

    if url.startswith('http://'):
        url = url[7:]
    elif url.startswith('https://'):
        url = url[8:]

    parts = url.split('/', 1)
    host = parts[0]
    path = '/' + parts[1] if len(parts) > 1 else '/'

    return host, path


def main():
    proxy_socket = socket(AF_INET, SOCK_STREAM)
    proxy_socket.bind(('', server_port))
    proxy_socket.listen(max_backlog_connections)

    print(f'Proxy server listening to port {server_port}')

    # main server loop
    while True:
        # wait for client connection
        print('LISTENING: Waiting for a new connection...')
        connection_socket, addr = proxy_socket.accept()

        # get request
        request = connection_socket.recv(1024).decode()

        if request:
            method, url, _ = request.split('\n')[0].split(' ')
            if method != 'GET':  # only handle GET requests
                connection_socket.close()
                return

            # extract host and create file path for caching
            host, path = parse_url(url)
            file_path = os.path.join(cache_dir, host + url.replace('/', '_'))

            new_request_line = f'GET {path} HTTP/1.1\r\n'
            modified_request = new_request_line
            request_lines = request.split('\n')
            for i in range(1, len(request_lines)):
                line = request_lines[i]
                if line.lower().startswith('host:'):
                    modified_request += f'Host: {host}\r\n'
                else:
                    modified_request += line + '\n'

            # send cached data if it exists
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    cached_data = f.read()
                    connection_socket.sendall(cached_data)
            else:
                try:
                    # connect to the requested web server
                    server_socket = socket(AF_INET, SOCK_STREAM)
                    server_socket.connect((host, 80))
                    print(f'BUSY: Connected to {host}')

                    # send client request to the requested server
                    server_socket.sendall(modified_request.encode())

                    response = b''  # store response as binary
                    while True:
                        data = server_socket.recv(2048)
                        if not data:
                            break
                        response += data
                        connection_socket.sendall(data)

                    # cache full response
                    with open(file_path, 'wb') as f:
                        f.write(response)

                    server_socket.close()
                except error:
                    not_found_msg = ('<h1>404 Not Found</h1>'
                                     '<p>Could not connect to the requested server.</p>')
                    response = 'HTTP/1.1 404 Not Found\r\n'

                    # add headers
                    response += f'Content-Type: text/html\r\n'
                    response += f'Content-Length: {len(not_found_msg)}\r\n'
                    response += '\r\n'
                    connection_socket.sendall(response.encode() + not_found_msg.encode())

        connection_socket.close()


if __name__ == "__main__":
    main()
