import struct

class Drtp:

    def __init__(self):
        # Start sequence and acknowledgement numbers at 1
        self.seq_numm = 1
        self.ack_num = 1

    def create_packet(self, data, SYN =False, ACK = False, FIN = False, reset_flag = False):
        # Generate bit flags based on input parameters (SYN, ACK, FIN, reset_flag)
        flags = (SYN << 3) | (ACK << 2) | (FIN << 1) |reset_flag
        #Create header by packing sequence and acknowledgement numbers along with flags. DRTP_Header_Format,'!HHH'
        header = struct.pack('!HHH', self.seq_numm, self.ack_num, flags)
        #Move to the next sequence number
        self.seq_numm += 1

        #Return the constructed packet (header + data)
        return header + data
    
    def parse_packet(self, packet):
        #Divide the packet into header and data parts
        header = packet[:6]
        data = packet[6:]
        #Unpack header details: sequence number, acknowledgement number, and flags
        seq_numm, ack_num, flags = struct.unpack('!HHH', header)
        # Identify induvidual flags from packed flags
        SYN = bool(flags & 0b1000)
        ACK = bool(flags & 0b0100)
        FIN = bool(flags & 0b0010)
        reset_flag = bool(flags & 0b0001)
        
        ## Return all unpacked and identified values
        return seq_numm, ack_num, SYN, ACK, FIN, data
    
    def send_ACK(self, socket, address, FIN=False, reset_flag=False):
        #Construct an ACK packet with optional fin and resett flags
        ack_packet = self.create_packet(b'', ACK=True, FIN=FIN, reset_flag=reset_flag)
        #Transmit the ACK packet to the specified adress
        socket.sendto(ack_packet, address)

    



