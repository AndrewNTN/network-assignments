from socket import *

server_port = 8080
max_backlog_connections = 1

content_types = {
    'html': 'text/html',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'txt': 'text/plain',
    'jpg': 'image/jpeg',
}


def create_http_response(status_code, content_type, content):
    response = f'HTTP/1.1 {status_code}\r\n'

    # add headers
    response += f'Content-Type: {content_type}\r\n'
    response += f'Content-Length: {len(content)}\r\n'
    response += '\r\n'

    # encode to bytes if string
    if isinstance(content, str):
        return response.encode() + content.encode()

    return response.encode() + content


def send_http_response(request):
    # parse HTTP request from client
    request_lines = request.split('\r\n')
    request_line = request_lines[0]
    method, path, _ = request_line.split()
    filename = path[1:]

    # default to HelloWorld.html if no file name
    if filename == '':
        filename = 'HelloWorld.html'

    try:
        # find the requested file in the server
        with open(filename, 'rb') as f:
            content = f.read()

        extension = filename.split('.')[-1].lower()

        content_type = content_types.get(extension,
                                         'application/octet-stream')  # default to octet-stream for ext unknown to the server
        return create_http_response('200 OK', content_type, content)
    except FileNotFoundError:
        not_found_msg = ('<h1>404 Not Found</h1>'
                         '<p>The file requested was not found on the server.</p>')
        return create_http_response('404 Not Found', 'text/html', not_found_msg)


def main():
    server_socket = socket(AF_INET, SOCK_STREAM)  # TCP socket
    server_socket.bind(('', server_port))
    server_socket.listen(max_backlog_connections)
    print(f'Server listening to port {server_port}')

    # main server loop
    while True:
        # wait for a client connection
        connection_socket, addr = server_socket.accept()

        # get request
        request = connection_socket.recv(1024).decode()

        # handle request
        if request:
            response = send_http_response(request)
            connection_socket.sendall(response)

        connection_socket.close()


if __name__ == '__main__':
    main()
