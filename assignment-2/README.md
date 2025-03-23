## Instructions to run project
### Prerequisites
- Python 3.6 or higher
- dpkt

This program uses the dpkt library. If not already installed, install it with
```shell
pip install dpkt
```

Run the program and pass in a .pcap file as an argument
```shell
python analysis_pcap_tcp.py <pcap_filename>
```

If you run into a "command not found" error, try running 
```shell
python3 analysis_pcap_tcp.py <pcap_filename>
```

IP addresses are hard-coded in main().

## High-Level Summary
### TCP Flow
- New flows are created by parsing packets and identifying 3-way TCP handshakes.
- Flows are uniquely identified by using a TCP 4-tuple (source ip, source port, destination ip, destination port).
- After a flow is identified, the first two packets with data are recorded.
- Throughput is calculated by storing the number of total bytes sent in a flow then dividing by the lifespan of the flow.

### Congestion Control
- The congestion window is estimated by tracking unacknowledged packets within each estimated RTT period, with the RTT estimate being updated at the conclusion of each window using the EWMA formula.
  - RTT = (1-α) (RTT) + α (new_sample)
- The initial RTT estimation is the RTT from the 3-way TCP handshake (from SYN to SYN-ACK).
- RTT samples are taken every time a new ACK is received by keeping track of sequence numbers and their send time.
  - Sequence numbers are kept track by the ACK expected to be received from the server for that sequence number.
- Retransmissions are detected when the sender resends an unacknowledged sequence number. 
- If the time elapsed from sending the original sequence number exceeds 2 * RTT', then it is treated as a timeout retransmission. If not, it is treated as a triple ACK retransmission.