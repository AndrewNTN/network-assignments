'''
This file contains basic utility functions that you can use and can also make your helper functions here
'''
import binascii
import socket

MAX_NUM_CLIENTS = 10
TIME_OUT = 0.5  # 500ms
CHUNK_SIZE = 1400  # 1400 Bytes


def validate_checksum(message):
    '''
    Validates Checksum of a message and returns true/false
    '''
    try:
        msg, checksum = message.rsplit('|', 1)
        msg += '|'
        return generate_checksum(msg.encode()) == checksum
    except BaseException:
        return False


def generate_checksum(message):
    '''
    Returns Checksum of the given message
    '''
    return str(binascii.crc32(message) & 0xffffffff)


def make_packet(msg_type="data", seqno=0, msg=""):
    '''
    This will add the header to your message.
    The formats is `<message_type> <sequence_number> <body> <checksum>`
    msg_type can be data, ack, end, start
    seqno is a packet sequence number (integer)
    msg is the actual message string
    '''
    body = "%s|%d|%s|" % (msg_type, seqno, msg)
    checksum = generate_checksum(body.encode())
    packet = "%s%s" % (body, checksum)
    return packet


def parse_packet(message):
    '''
    This function will parse the packet in the same way it was made in the above function.
    '''
    pieces = message.split('|')
    msg_type, seqno = pieces[0:2]
    checksum = pieces[-1]
    data = '|'.join(pieces[2:-1])
    return msg_type, seqno, data, checksum


def make_message(msg_type, msg_format, message=None):
    '''
    This function can be used to format your message according
    to any one of the formats described in the documentation.
    msg_type defines type like join, disconnect etc.
    msg_format is either 1,2,3 or 4
    msg is remaining.
    '''
    if msg_format == 2:
        msg_len = 0
        return "%s %d" % (msg_type, msg_len)
    if msg_format in [1, 3, 4]:
        msg_len = len(message)
        return "%s %d %s" % (msg_type, msg_len, message)
    return ""


def send_msg(sock, msg_type, msg_format, addr, message=None):
    msg = make_message(msg_type, msg_format, message=message)
    packet = make_packet(msg=msg)
    sock.sendto(packet.encode(), addr)


def reliable_send_msg(sock, msg_type, msg_format, send_addr, seqno, message=None):
    # reliably send a message to send_addr
    msg = make_message(msg_type, msg_format, message=message)

    # split into message into chunks
    chunks = [msg[i:i + CHUNK_SIZE] for i in range(0, len(msg), CHUNK_SIZE)]

    # send start
    start_packet = make_packet("start", seqno)
    send_and_wait_ack(sock, start_packet, send_addr, seqno)
    seqno += 1

    # send data
    for chunk in chunks:
        chunk_packet = make_packet("data", seqno, chunk)
        send_and_wait_ack(sock, chunk_packet, send_addr, seqno)
        seqno += 1

    # send end
    end_packet = make_packet("end", seqno)
    send_and_wait_ack(sock, end_packet, send_addr, seqno)


def send_and_wait_ack(sock, packet, send_addr, seqno):
    while True:
        sock.sendto(packet.encode(), send_addr)
        sock.settimeout(TIME_OUT)
        # wait for ack
        try:
            res, _ = sock.recvfrom(4096)
            res_type, res_seq, res_data, _ = parse_packet(res.decode())
            print(f"ACK_SEQNUM: {res_seq}, SEQNO+1: {seqno + 1}")
            if res_type == "ack" and res_seq.isdigit() and int(res_seq) == seqno + 1:
                break  # successfully sent
        except socket.timeout:
            # try again if timed out
            continue
        finally:
            sock.settimeout(None)


def receive_msg(sock, buffers):
    try:
        # receive packet
        packet, addr = sock.recvfrom(4096)
        packet = packet.decode()
    except socket.timeout:
        return None, None, None

    # verify checksum and skip if invalid
    if not validate_checksum(packet):
        return None, None, None

    # parse packet
    msg_type, seq_str, data, checksum = parse_packet(packet)
    seq = int(seq_str)

    if msg_type == "start" or msg_type == "data" or msg_type == "end":
        buffer = buffers.setdefault(addr, {"chunks": [], "expected": seq})

        # send acks
        if msg_type == "start":
            print(f"START: {seq}")
            buffer["expected"] += 1
            ack = make_packet("ack", buffer["expected"])
            sock.sendto(ack.encode(), addr)

        elif msg_type == "data":
            print(f"DATA: {seq}")
            buffer["chunks"].append(data)
            buffer["expected"] += 1
            ack = make_packet("ack", buffer["expected"])
            sock.sendto(ack.encode(), addr)

        else:  # end
            print(f"END: {seq}")
            buffer["expected"] += 1
            ack = make_packet("ack", buffer["expected"])
            sock.sendto(ack.encode(), addr)

            # put together message
            message = "".join(buffer["chunks"])
            buffers.pop(addr, None)
            return message, addr, buffer["expected"]

    return None, None, None
