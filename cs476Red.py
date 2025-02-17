import numpy as np
import random
import math

# Helper function to generate Pareto-distributed durations (ON/OFF states)
def pareto(x_min, alpha):
    u = random.random()
    return x_min * (1 - u) ** (-1.0 / alpha)

# Host Class
class Host:
    def __init__(self, id, x, y, alpha_on, alpha_off, network):
        # Init
        self.id = id
        self.x = x
        self.y = y
        self.alpha_on = alpha_on
        self.alpha_off = alpha_off

        # Queues
        self.tcp_queues = {}        # Dictionary of TCP queues
        self.udp_queue = []         # Shared UDP queue

        # Constants
        self.link = None            # The link between this host and its assigned router. This gets assigned during create_network() in the Network class.
        self.isHost = True
        self.state = 'OFF'          # State: ON or OFF
        self.cwnd = 1               # Congestion Window for TCP
        self.rto = 1                # Retransmission Timeout
        self.timeout = False
        self.time_in_state = 0
        self.pareto_on = pareto(1, self.alpha_on)
        self.pareto_off = pareto(1, self.alpha_off)

        self.received_packets = []

    def generate_packet(self):
        # Host generates a packet based on its state (ON/OFF)
        if self.state == 'ON':
            destination = random.choice(network.hosts)
            packet_type = random.choice(['TCP', 'UDP'])
            self.enqueue_packet(packet_type, destination)
            if debug:
                print(f"Host {self.id}: \tQueued {packet_type} packet to be sent to Host {destination.id}")
    
    def enqueue_packet(self, packet_type, destination):
        # Insert a packet into the appropriate queue
        if packet_type == 'TCP':
            if destination not in self.tcp_queues:
                self.tcp_queues[destination] = []
            self.tcp_queues[destination].append({'source': self, 'destination': destination, 'type': 'TCP', 'seq_num': len(self.tcp_queues[destination]), 'ack': False})
        elif packet_type == 'UDP':
            self.udp_queue.append({'source': self, 'destination': destination, 'type': 'UDP'})
        else:
            raise ValueError("enqueue_packet: Invalid packet type \"" + str(packet_type) + "\"")

    def update_state(self):
        # Transition between ON and OFF states using Pareto distribution
        if self.state == 'OFF':
            self.state = 'ON'
            self.time_in_state = 0
            self.pareto_on = pareto(1, self.alpha_on)
        else:
            self.state = 'OFF'
            self.time_in_state = 0
            self.pareto_off = pareto(1, self.alpha_off)
    
    def get_next_state_duration(self):
        # Get the next duration for ON/OFF state
        if self.state == 'ON':
            return self.pareto_on
        else:
            return self.pareto_off
        
    def send_packet(self):
        # Send a packet to the nearest router
        if self.state == 'ON':
            # Randomly decide which queue (TCP or UDP) to send a packet from
            send_tcp = random.uniform(0, 1)

            if send_tcp and len(list(self.tcp_queues.keys())) > 0:
                # Send packets from a random TCP queue
                key = random.choice(list(self.tcp_queues.keys()))       # Line of code adapted from https://www.slingacademy.com/article/python-how-to-get-a-random-item-from-a-dictionary/
                if self.tcp_queues[key]:
                    packet = self.tcp_queues[key].pop(0)
                    self.link.queue.append(packet)
                    if debug: print(f"Host {self.id}: \tSent TCP packet to Router {self.link.destination.id} (Destination: Host {packet["destination"].id})")
                if not self.tcp_queues[key]:
                    # Delete the queue if it is now empty
                    self.tcp_queues.pop(key)
            else:
                # Send packets from the UDP queue
                if self.udp_queue:
                    packet = self.udp_queue.pop(0)
                    self.link.queue.append(packet)
                    print(f"Host {self.id}: \tSent UDP packet to Router {self.link.destination.id} (Destination: Host {packet["destination"].id})")
            global sentP
            sentP = sentP+1

    def receive_packet(self, packet):
        self.received_packets.append(packet)
        #global recP
        #recP = recP+1

# Router Class
class Router:
    def __init__(self, id, x, y, buffer_size, network):
        # Init
        self.id = id
        self.x = x
        self.y = y
        self.buffer_size = buffer_size
        self.links = []

        # Queues
        self.tcp_queues = {}        # Dictionary of TCP queues
        self.udp_queue = []         # Shared UDP queue

        # Constants
        self.isHost = False
    
    def send_packet(self):
        # Send a packet to the router that has a link to the destination host. Or, send the packet to the host if there's a path
        # Randomly decide which queue (TCP or UDP) to send a packet from
        send_tcp = random.uniform(0, 1)

        if send_tcp and len(list(self.tcp_queues.keys())) > 0:
            # Send packets from a random TCP queue
            key = random.choice(list(self.tcp_queues.keys()))       # Line of code adapted from https://www.slingacademy.com/article/python-how-to-get-a-random-item-from-a-dictionary/
            if self.tcp_queues[key]:
                packet = self.tcp_queues[key].pop(0)
                source = packet['source']
                destination = packet['destination']

                # Find a router that has a link to the destination host, and send the packet to that router
                next_router = network.get_link(None, destination).source
                link = network.get_link(self, next_router)

                # If the destination host is also conected to this router, just send it there instead
                if self.id == next_router.id and self.isHost == next_router.isHost:
                    link = network.get_link(self, destination)
                
                link.queue.append(packet)

                identity = "Router"
                if link.destination.isHost:
                    identity = "Host"
                print(f"Router {self.id}: \tSent TCP packet to {identity} {link.destination.id} (Destination: Host {destination.id})")
            if not self.tcp_queues[key]:
                # Delete the queue if it is now empty
                self.tcp_queues.pop(key)
        else:
            # Send packets from the UDP queue
            if self.udp_queue:
                packet = self.udp_queue.pop(0)
                source = packet['source']
                destination = packet['destination']

                # Find a router that has a link to the distination host, and send the packet to that router
                next_router = network.get_link(None, destination).source
                link = network.get_link(self, next_router)

                # If the destination host is also conected to this router, just send it there instead
                if self.id == next_router.id and self.isHost == next_router.isHost:
                    link = network.get_link(self, destination)

                link.queue.append(packet)

                if debug:
                    identity = "Router"
                    if link.destination.isHost:
                        identity = "Host"
                    print(f"Router {self.id}: \tSent UDP packet to Router {link.destination.id} (Destination: Host {destination.id})")

    # def send_packet(self, packet):
    #     # Send packet to a link
    #     source = packet['source']
    #     destination = packet['destination']
    #     if destination in self.routing_table:
    #         host = self.routing_table[destination]
    #         print("Host: " + str(host))
    #         if len(self.queues[host]) < self.buffer_size:
    #             self.queues[host].append(packet)
    #             print(f"Router {self.id}: Forwarded packet from {source.id} to Router {host.id}")
    #         else:
    #             # Drop packet if the queue is full
    #             print(f"Router {self.id}: Dropped packet from {packet['source'].id} to {destination.id}")

    def receive_packet(self, packet):
        # Add this packet to the queue
        global dropP
        if packet['type'] == 'TCP':
            host = packet['destination']
            if host not in self.tcp_queues:
                self.tcp_queues[host] = []
                if len(self.tcp_queues[host]) < self.buffer_size: self.tcp_queues[host].append(packet)
                else: 
                    if debug: print(f"Router {self.id}: Dropped packet from {packet['source'].id} to {self.id}")
                    dropP = dropP+1

        elif packet['type'] == 'UDP':
            if len(self.udp_queue) < self.buffer_size: self.udp_queue.append(packet)
            else: 
                if debug: print(f"Router {self.id}: Dropped packet from {packet['source'].id} to {self.id}")
                dropP = dropP+1

# Link Class
# Note: Links are one-directional. They can only go from source to destination.
class Link:
    def __init__(self, source, destination, delay):
        # Init
        self.source = source
        self.destination = destination
        self.delay = delay

        # Queues
        self.queue = []

        # Variables
        self.delay_countdown = delay

    def propagate(self):
        # Propagate packet after delay
        if self.delay_countdown <= 0:
            self.delay_countdown = self.delay   # Reset delay countdown
            if self.queue:
                packet = self.queue.pop(0)
                if self.destination:
                    identity1 = "Router"
                    identity2 = "Router"
                    if self.source.isHost:
                        identity1 = "Host"
                    if self.destination.isHost:
                        identity2 = "Host"
                    if debug: print(f"Link: \t\tSent {packet['type']} packet from {identity1} {self.source.id} to {identity2} {self.destination.id} (Destination: Host {packet["destination"].id})")
                    self.destination.receive_packet(packet)
        else:
            self.delay_countdown -= 1

# RED Algorithm for packet dropping
class RED:
    def __init__(self, minth, maxth, maxp, wq):
        self.minth = minth
        self.maxth = maxth
        self.maxp = maxp
        self.wq = wq
        self.avg_queue_size = 0
    
    def drop_packet(self, queue_size):
        # Apply RED algorithm for packet dropping
        self.avg_queue_size = (1 - self.wq) * self.avg_queue_size + self.wq * queue_size
        if self.avg_queue_size < self.minth:
            return False
        elif self.avg_queue_size > self.maxth:
            return True
        else:
            # Geometric distribution
            p = (self.avg_queue_size - self.minth) / (self.maxth - self.minth) * self.maxp
            return random.random() < p

# Network Class
class Network:
    def __init__(self, num_hosts, num_routers, aOn, aOff, buffSize, propScale, maxp, minth, maxth, wq):
        self.hosts = []
        self.routers = []
        self.links = []
        self.maxp = maxp
        self.minth = minth
        self.maxth = maxth
        self.wq = wq
        self.red = RED(minth, maxth, maxp, wq)
        self.create_network(num_hosts, num_routers)
    
    def create_network(self, num_hosts, num_routers):
        # Initialize hosts and routers
        for i in range(num_hosts):
            x, y = random.uniform(0, propScale), random.uniform(0, propScale)  # Random positions for simplicity
            host = Host(i, x, y, aOn, aOff, self)
            self.hosts.append(host)

        for i in range(num_routers):
            x, y = random.uniform(0, propScale), random.uniform(0, propScale)
            router = Router(i, x, y, buffSize, self)
            self.routers.append(router)

        # Create links between hosts and their nearest router (simple model)
        for host in self.hosts:
            nearest_router = min(self.routers, key=lambda router: (router.x - host.x) ** 2 + (router.y - host.y) ** 2)  # Uses pythagorean theorem to find the closest router
            delay = random.randint(1, 5)        # Random delay between 1 and 5 ticks
            # Create link from host -> nearest router
            link1 = Link(host, nearest_router, delay)
            self.links.append(link1)
            host.link = link1
            # Create link from nearest router -> host
            link2 = Link(nearest_router, host, delay)
            self.links.append(link2)
            nearest_router.links.append(link2)

        # Create a link between every router for simplicity (normally this wouldn't be the case)
        for router1 in self.routers:
            for router2 in self.routers:
                if router1.id == router2.id:
                    continue
                delay = random.randint(1, 5)    # Random delay between 1 and 5 ticks
                # Create link from router1 -> router2 
                link1 = Link(router1, router2, delay)
                self.links.append(link1)
                router1.links.append(link1)
                # No need to create a link from router2 -> router1, because it will happen later

    def run_simulation(self, ticks):
        for tick in range(ticks):
            self.simulate_tick(tick)
    
    def simulate_tick(self, _):
        # Process packets in the network
        for host in self.hosts:
            host.generate_packet()
            host.update_state()
            host.send_packet()

        for router in self.routers:
            router.send_packet()

        # Forward packets in the network
        for link in self.links:
            link.propagate()
        
        # NOTE: This needs to be redone
        # Apply RED for packet dropping
        # for router in self.routers:
        #     for next_router in router.queues:
        #         if self.red.drop_packet(len(router.queues[next_router])):
        #             packet = router.queues[next_router].pop(0)  # Drop packet
        #             print(f"Router {router.id}: Dropped packet from {packet['source'].id} to {packet['destination'].id}")
    
    def qCheck(self):
        fullQ = 0
        totalQ = 0
        for router in self.routers:
            totalQ = totalQ+1 #UDP queue
            if len(router.udp_queue) >= buffSize: fullQ = fullQ+1
            for queue in router.tcp_queues.values(): #TCP queues
                totalQ = totalQ+1
                if len(queue) >= buffSize: fullQ = fullQ+1
                
        for host in self.hosts:
            totalQ = totalQ+1 #UDP queue
            if len(host.udp_queue) >= buffSize: fullQ = fullQ+1
            for queue in host.tcp_queues.values(): #TCP queues
                totalQ = totalQ+1
                if len(queue) >= buffSize: fullQ = fullQ+1
        propQ = fullQ / totalQ
        return propQ
            
    def print_network_data(self):
        qSum = 0
        for router in self.routers:
            qSum = qSum + len(router.udp_queue)
            for queue in router.tcp_queues.values(): qSum = qSum + len(queue)
        qAvg = qSum / len(self.routers)
        qProp = self.qCheck()
        print(f"Total packets sent: {sentP}, total packets dropped: {dropP}.\nAverage Queue length: {qAvg}.\nProportion of full Queues: {qProp}")

    def print_network_status(self):
        # Print current status of network (for debugging)
        print("--------------")
        print("|   Hosts:   |")
        print("--------------")
        for host in self.hosts:
            print(f"Host {host.id} at ({host.x}, {host.y})")
        print("--------------")
        print("|  Routers:  |")
        print("--------------")
        for router in self.routers:
            print(f"Router {router.id} at ({router.x}, {router.y})")
        print("--------------")
        print("|   Links:   |")
        print("--------------")
        for link in self.links:
            identity1 = "Router"
            identity2 = "Router"
            if link.source.isHost:
                identity1 = "Host"
            if link.destination.isHost:
                identity2 = "Host"
            print(f"Link between {identity1} {link.source.id} and {identity2} {link.destination.id}")

    # Checks if the link with the specified source & destination exists, and returns it if so. This is my favorite function of all time.
    def get_link(self, source, destination):
        if source == None:  # Returns the first link that has the specified destination.
            for link in self.links:
                if link.destination.id == destination.id and link.destination.isHost == destination.isHost:
                    return link
        else:
            for link in self.links:
                if link.source.id == source.id and link.source.isHost == source.isHost and link.destination.id == destination.id and link.destination.isHost == destination.isHost:
                    return link
        return None  # No link with specified source & destination was found

# Main Execution

# Debug variable - set to True for debug messages
#debug = True
debug = False


# Data tracking variables
sentP = 0
dropP = 0
#recP = 0
#dropP = sentP-recP
Qlen = 0
Qprop = 0

# Initialize network parameters
num_hosts = 3
num_routers = 2
buffSize = 10
aOn = 1.5
aOff = 1.5
propScale = 10
# Initialize RED parameters
maxp = 0  # Max packet drop probability
minth = 1  # Min threshold for RED
maxth = 3  # Max threshold for RED
wq = 0.1  # Weight for RED average queue size

# Create the network
network = Network(num_hosts, num_routers, aOn, aOff, buffSize, propScale, maxp, minth, maxth, wq)

# Run simulation
network.run_simulation(3000)  # Run for 1000 ticks

network.print_network_data()
if debug:
    network.print_network_status()

    # Peek at Host 0's queues (uncomment for debug)
    # print("Contents of Host 0's Queues:")
    # for i in network.hosts[0].udp_queue:
    #     print(f"{i['type']}")

    # for queue in network.hosts[0].tcp_queues.values():
    #     for i in queue:
    #         print(f"{i['type']}")