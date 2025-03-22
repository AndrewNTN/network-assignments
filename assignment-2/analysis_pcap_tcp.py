import dpkt
import sys
import socket
from collections import defaultdict

file_name = ""


def parse_pcap(pcap_file_name, sender_ip, receiver_ip):
    # open pcap file
    pcap_file = open(pcap_file_name, "rb")
    pcap = dpkt.pcap.Reader(pcap_file)

    tcp_flows = {}  # TCP 4-tuple will be the key

    for ts, buf in pcap:
        try:
            eth = dpkt.ethernet.Ethernet(buf)

            # ignore non IP packet type
            if not isinstance(eth.data, dpkt.ip.IP):
                continue

            ip = eth.data

            # ignore non TCP type connection
            if not isinstance(ip.data, dpkt.tcp.TCP):
                continue

            tcp = ip.data

            # create TCP 4-tuple
            src_ip = socket.inet_ntoa(ip.src)
            src_port = tcp.sport
            dest_ip = socket.inet_ntoa(ip.dst)
            dest_port = tcp.dport

            # only consider packets between sender and receiver
            if not ((src_ip == sender_ip and dest_ip == receiver_ip) or
                    (src_ip == receiver_ip and dest_ip == sender_ip)):
                continue

            # create from sender's perspective
            if src_ip == sender_ip:
                tcp_tuple = (src_ip, src_port, dest_ip, dest_port)
            else:
                tcp_tuple = (dest_ip, dest_port, src_ip, src_port)

            # parse SYN packet from sender and create new flow
            if src_ip == sender_ip and (tcp.flags & dpkt.tcp.TH_SYN) and not (tcp.flags & dpkt.tcp.TH_ACK):
                tcp_flows[tcp_tuple] = {
                    "start_time": ts,
                    "end_time": None,
                    "handshake_complete": False,
                    "bytes_sent": 0,
                    "window_scale": 1,
                    "first_two_transactions": [],
                    "triple_ack_retransmits": 0,
                    "timeout_retransmits": 0,
                    "rtt_estimate": None,
                    "next_rtt_estimate": None,
                    "curr_rtt_sample": None,
                    "unacked_seq_nums": defaultdict(float),  # seq nums, sequence num : time sent
                    "cwnd_size_list": [],
                    "last_rtt_update": None,
                    "rtt_window_packets": set()
                }

            # get window scale
            for opt_type, opt_data in dpkt.tcp.parse_opts(tcp.opts):
                if opt_type == dpkt.tcp.TCP_OPT_WSCALE:
                    tcp_flows[tcp_tuple]["window_scale"] = int.from_bytes(opt_data, "big")

            # measure the RTT from SYN to SYN-ACK to use as the initial RTT
            if tcp_tuple in tcp_flows and src_ip == receiver_ip and (tcp.flags & dpkt.tcp.TH_SYN) and (
                    tcp.flags & dpkt.tcp.TH_ACK):
                tcp_flows[tcp_tuple]["rtt_estimate"] = ts - tcp_flows[tcp_tuple]["start_time"]
                tcp_flows[tcp_tuple]["curr_rtt_sample"] = tcp_flows[tcp_tuple]["rtt_estimate"]
                tcp_flows[tcp_tuple]["last_rtt_update"] = ts

            # check for the ACK from sender to mark the tcp handshake as complete
            if tcp_tuple in tcp_flows and not tcp_flows[tcp_tuple]["handshake_complete"]:
                if src_ip == sender_ip and (tcp.flags & dpkt.tcp.TH_ACK) and not (
                        tcp.flags & dpkt.tcp.TH_SYN):  # ACK only from sender, no SYN flag
                    tcp_flows[tcp_tuple]["handshake_complete"] = True

            # RTT and congestion window
            if tcp_tuple in tcp_flows and tcp_flows[tcp_tuple]["handshake_complete"]:
                # check if curr RTT is exceeded
                if (tcp_flows[tcp_tuple]["rtt_estimate"] is not None and
                        ts - tcp_flows[tcp_tuple]["last_rtt_update"] > tcp_flows[tcp_tuple]["rtt_estimate"]):
                    # record the congestion window size
                    cwnd_size = len(tcp_flows[tcp_tuple]["rtt_window_packets"])
                    tcp_flows[tcp_tuple]["cwnd_size_list"].append(cwnd_size)

                    # update next RTT estimate
                    if tcp_flows[tcp_tuple]["next_rtt_estimate"] is not None:
                        tcp_flows[tcp_tuple]["rtt_estimate"] = tcp_flows[tcp_tuple]["next_rtt_estimate"]

                    # reset for next cwnd
                    tcp_flows[tcp_tuple]["last_rtt_update"] = ts
                    tcp_flows[tcp_tuple]["rtt_window_packets"].clear()

                if src_ip == sender_ip and len(tcp.data) > 0:
                    # track seq num and send time
                    tcp_flows[tcp_tuple]["unacked_seq_nums"][tcp.seq] = ts

                    # add to current RTT window for cwnd calculation
                    tcp_flows[tcp_tuple]["rtt_window_packets"].add(tcp.seq)

                # process ACK packets from receiver
                elif src_ip == receiver_ip and (tcp.flags & dpkt.tcp.TH_ACK) and not (tcp.flags & dpkt.tcp.TH_SYN):
                    if tcp.ack in tcp_flows[tcp_tuple]["unacked_seq_nums"]:
                        # calculate new RTT sample from this ACK
                        send_time = tcp_flows[tcp_tuple]["unacked_seq_nums"][tcp.ack]
                        rtt_sample = ts - send_time
                        tcp_flows[tcp_tuple]["curr_rtt_sample"] = rtt_sample

                        # update the next RTT estimate using EWMA formula
                        if tcp_flows[tcp_tuple]["next_rtt_estimate"] is None:
                            tcp_flows[tcp_tuple]["next_rtt_estimate"] = rtt_sample
                        else:
                            alpha = 0.125  # recommended alpha value from slides for RTT estimation
                            tcp_flows[tcp_tuple]["next_rtt_estimate"] = ((1 - alpha) *
                                                                         tcp_flows[tcp_tuple][
                                                                             "next_rtt_estimate"] + alpha * rtt_sample)

                        # remove ACKed sequence number
                        del tcp_flows[tcp_tuple]["unacked_seq_nums"][tcp.ack]

            if tcp_tuple in tcp_flows and tcp_flows[tcp_tuple]["handshake_complete"]:
                # store first 2 transactions after handshake is completed
                if len(tcp_flows[tcp_tuple]["first_two_transactions"]) < 2:
                    if src_ip == sender_ip and len(tcp.data) > 0:
                        # calculate receive window size
                        rwnd_size = tcp.win * (2 ** tcp_flows[tcp_tuple][
                            "window_scale"])  # TCP window size = TCP window size in bytes * (2^scale factor)

                        # store first 2 transaction info
                        tcp_flows[tcp_tuple]["first_two_transactions"].append({
                            "seq": tcp.seq,
                            "ack": tcp.ack,
                            "rwnd": rwnd_size
                        })

            # store number of bytes sent for throughput calculation
            if tcp_tuple in tcp_flows:
                if src_ip == sender_ip:
                    tcp_flows[tcp_tuple]["bytes_sent"] += len(tcp)

                # set flow end time to most recent packet
                tcp_flows[tcp_tuple]["end_time"] = ts

        except Exception as e:
            print(f"Error while parsing packet: {e}")
            continue

    pcap_file.close()
    return tcp_flows


def main():
    sender_ip = "130.245.145.12"
    receiver_ip = "128.208.2.198"

    tcp_flows = parse_pcap(file_name, sender_ip, receiver_ip)

    print(f"Number of TCP Flows initialized from sender: {len(tcp_flows)}\n"
          f"-------------------------------------------------")
    for flow in tcp_flows:
        print(
            f"[Flow]\n"
            f"[Sender IP]: {flow[0]} [Sender Port]: {flow[1]}\n[Receiver IP]: {flow[2]} [Receiver Port]: {flow[3]}")
        for i, transaction in enumerate(tcp_flows[flow]["first_two_transactions"], 1):
            print(f"    [Transaction {i}]:\n"
                  f"        Sequence Number: {transaction['seq']}\n"
                  f"        Acknowledgement Number: {transaction['ack']}\n"
                  f"        Receive Window Size: {transaction['rwnd']}")

        if tcp_flows[flow]["end_time"] is not None:
            # calculate throughput
            flow_info = tcp_flows[flow]
            if flow_info["start_time"] and flow_info["end_time"]:
                duration = flow_info["end_time"] - flow_info["start_time"]
                if duration > 0:
                    throughput = flow_info["bytes_sent"] / duration
                else:
                    throughput = 0
            else:
                throughput = 0
            print(f"    [Throughput]: {throughput} bytes/sec")
        else:
            print(f"Flow was incomplete.\n")

        print(f"    [First 3 congestion window sizes]: {tcp_flows[flow]['cwnd_size_list'][0:3]}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_name = sys.argv[1]
    else:
        print("Usage: python analysis_pcap_tcp.py <pcap_filename>")
    main()
