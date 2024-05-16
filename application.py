import argparse
import socket
import time
from collections import deque
from datetime import datetime
from DrtpClass import Drtp # type: ignore

def start_drtp_server(server_adress, server_port, discard_seq_num):
    # Initialize a UDP socket
    ser_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Assign the socket to the provided IP address and port number
    ser_sock.bind((server_adress, server_port))
    print(f'Server is started at {server_adress} : {server_port}\n')

    # Set up a DRTP object (Drtp is a class, an object from this class is being instantiated here)
    drtp = Drtp() 
    # Initialize a variable to keep track of the amount of data received
    data_received = 0
    # Initialize a variable to keep track of the number of packets received
    packet_recieved = 0
    # Record the start time for calculating throughput later on
    start_time = time.time()
    # Initialize a flag to check if the connection has been established
    connection_established = False

    # Main listening loop of the server
    while True:
        # Listen for packets from the client
        packet, address = ser_sock.recvfrom(1000)
        # Use the DRTP instance to parse the received packet
        seq_num, ack_num, SYN, ACK, FIN, data = drtp.parse_packet(packet)

        # If the SYN flag is set and the connection is not yet established, respond to the SYN packet
        if SYN and not connection_established:
            print('SYN packet is received')
            # Construct and send a SYN-ACK packet
            syn_ack_packet = drtp.create_packet(b'', SYN=True, ACK=True)
            ser_sock.sendto(syn_ack_packet, address)
            print('SYN-ACK packet is sent')
        
        # If the ACK flag is received and the connection is not yet established, establish the connection
        elif ACK and not connection_established:
            print('ACK packet is received')
            print('Connection established')
            # Set the connection flag to True, indicating that the connection is now established
            connection_established = True
            start_time = time.time()
        
        # If the connection is established
        elif connection_established:
            # If the sequence number matches the discard sequence number, discard the packet
            if seq_num == discard_seq_num:
                print('Discarding packet with seq = {}'.format(seq_num))
                # Simulate a delay longer than the client's timeout period
                time.sleep(0.6)  
                # Reset the discard sequence number, thus ensuring that the next packet is not discarded."
                discard_seq_num = float('inf')  
                continue

            # If the packet is a FIN packet
            else:
                if FIN:
                    print('....\n')
                    print('FIN packet is received')
                    # Send a FIN-ACK packet
                    drtp.send_ACK(ser_sock, address, FIN=True)
                    drtp.ack_num += 1  # increment the acknowledgement number
                    print('FIN ACK packet is sent\n')
                    break
                else:
                    print('{} -- packet {} is received'.format(datetime.now().time(), seq_num))
                    drtp.send_ACK(ser_sock, address)
                    drtp.ack_num += 1
                    print('{} -- sending ack for the received {}'.format(datetime.now().time(), seq_num))

            # Write the received data to a file
            with open('received_file', 'ab') as f:
                if data:
                    f.write(data)
                    data_received += len(data)

    ser_sock.close()

    end_time = time.time()
    # Calculate the elapsed time by subtracting the start time from the end time
    elapsed_time = end_time - start_time
    # Calculate the throughput (in Mbps) by dividing the amount of data received by the elapsed time and converting to Mbps
    throughput = "{:.2f}".format(data_received / elapsed_time / 125000)  # Convert to Mbps
    print('The throughput is {} Mbps'.format(throughput))
    print('Connection Closes\n')

#Creates and sends a series of packets to transmit the file to the specified server
def transfer_file(socket, host, port, filename, win_size):
    # 'base_seq_num' is the sequence number of the oldest unacknowledged packet
    base_seq_num = 0
    # 'next_seq_num' is the smallest unused sequence number, starts from 1
    next_seq_num = 1
    # List to store the packets
    packets = []
    # Sliding window with size equal to window size. Deque is a type of data structure, here used to create a sliding window.
    sliding_win = deque(maxlen=win_size)  
    drtp = Drtp() # Create a DRTP object

    # Open the file in binary mode for reading
    with open(filename, 'rb') as f:
        while True:
            # Send packets within the window size limit
            while next_seq_num < base_seq_num + win_size + 1:
                data = f.read(994)
                if not data:
                    break

                # Use the DRTP instance to create a packet with the read data
                packet = drtp.create_packet(data)
                # Store the packet in the list of packets
                packets.append(packet)
                socket.sendto(packet, (host, port))
                # Append the sequence number to the sliding window
                sliding_win.append(next_seq_num)
                list_sliding = list(sliding_win)
                print('{} -- packet with seq = {} is sent, sliding window = {{{}}}'.format(datetime.now().time(), next_seq_num, ', '.join(map(str, list_sliding))))
                next_seq_num += 1

                # Start waiting for ACKs after the sliding window is full or 5 packets have been sent
                if len(sliding_win) == win_size or next_seq_num > 5:
                    try:
                        # Wait for an acknowledgement packet
                        ack_packet, address = socket.recvfrom(1000)
                        # Parse the acknowledgement packet
                        seq_num, ack_num, SYN, ACK, FIN, data = drtp.parse_packet(ack_packet)

                        if ACK:
                            print('{} -- ACK for packet = {} is received'.format(datetime.now().time(), ack_num))
                            # Remove the acknowledged packet from the sliding window
                            sliding_win.popleft()

                    except TimeoutError:
                        # If a timeout occurs, retransmit all unacknowledged packets
                        print('Timeout occurred, retransmitting packets')
                        for i in range(len(sliding_win)):
                            socket.sendto(packets[i], (host, port))

            if not data:
                break
    print("\nData Finished\n")

def start_drtp_client(client_address, client_port, filename, win_size):
    # Set up a socket for client and specify a timeout duration 
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.5)  # Timeout set to 500ms

    drtp = Drtp()

    # Connection Establishment Phase
    print("\nConnection Establishment Phase:\n")

    drtp.seq_num = 1
    # Create and send a SYN packet
    syn_packet = drtp.create_packet(b'', SYN=True)
    sock.sendto(syn_packet, (client_address, client_port))
    print('SYN packet is sent')

    # Wait for a SYN-ACK packet
    while True:
        packet, adress = sock.recvfrom(1000)
        seq_num, ack_num, SYN, ACK, FIN, data = drtp.parse_packet(packet)

        if SYN and ACK:
            print('SYN-ACK packet is received')
            # Send an ACK packet
            drtp.seq_num += 1  # Increment sequence number for the next packet
            ack_packet = drtp.create_packet(b'', ACK=True)
            sock.sendto(ack_packet, (client_address, client_port))
            print('ACK packet is sent\n')
            print("Connection established\n")
            print('\nData Transfer:\n')
            break

    # Start sending the file using Go-Back-N protocol
    transfer_file(sock, client_address, client_port, filename, win_size)
    

    # Connection Teardown Phase
    print("\nConnection Teardown:\n")

    # Send a FIN packet
    fin_packet = drtp.create_packet(b'', FIN=True)
    sock.sendto(fin_packet, (client_address, client_port))
    print('FIN packet is sent')

    # Wait for a FIN-ACK packet
    while True:
        packet, address = sock.recvfrom(1000)
        seq_num, ack_num, SYN, ACK, FIN, data = drtp.parse_packet(packet)

        if FIN and ACK:
            print('FIN ACK packet is received')
            break

    print("\nConnection Closes\n")
    sock.close()

if __name__ == '__main__':
    # Argument parser for command-line options
    parser = argparse.ArgumentParser(description='DRTP File Transfer Application')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-s', '--server', action='store_true', help='Run as server')
    group.add_argument('-c', '--client', action='store_true', help='Run as client')
    parser.add_argument('-p', '--port', type=int, required=True, help='Port number to use')
    parser.add_argument('-i', '--ip', required=True, help='IP address of the server')
    parser.add_argument('-f', '--file', help='Name of the file to send')
    parser.add_argument('-w', '--window', type=int, default=3, help='Size of the sliding window')
    parser.add_argument('-d', '--discard', type=int, default=float('inf'), help='Sequence number of packet to discard')

    # Parse command-line arguments
    args = parser.parse_args()

    # Check command line arguments to determine mode of operation
    if args.server:
        start_drtp_server(args.ip, args.port, args.discard)
    elif args.client:
        if args.file is None:
            print('Please specify a file to send')
        else:
            start_drtp_client(args.ip, args.port, args.file, args.window) 
