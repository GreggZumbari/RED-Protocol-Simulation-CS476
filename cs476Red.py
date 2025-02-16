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
        self.network = network

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

        self.received_packets = 0

    def generate_packet(self):
        # Host generates a packet based on its state (ON/OFF)
        if self.state == 'ON':
            destination = random.choice(self.network.hosts)
            packet_type = random.choice(['TCP', 'UDP'])
            self.enqueue_packet(packet_type, destination)
            if debug:
                print(f"Host {self.id}: Queued {packet_type} packet to be sent to Host {destination.id}")
    
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
            # Decide which queue (TCP or UDP) to send a packet from
            send_tcp = random.uniform(0, 1)

            if send_tcp:
                # Send packets from a random TCP queue
                key = random.choice(list(self.tcp_queues.keys()))       # Line of code adapted from https://www.slingacademy.com/article/python-how-to-get-a-random-item-from-a-dictionary/
                if self.tcp_queues[key]:
                    packet = self.tcp_queues[key].pop(0)
                    self.link.queue.append(packet)
                    print(f"Host {self.id}: Sent TCP packet to Router {self.link.destination.id}")
                if not self.tcp_queues[key]:
                    # Delete the queue if it is now empty
                    self.tcp_queues.pop(key)
            else:
                # Send packets from UDP queues
                if self.udp_queue:
                    packet = self.udp_queue.pop(0)
                    self.link.queue.append(packet)
                    print(f"Host {self.id}: Sent UDP packet to Router {self.link.destination.id}")

    def receive_packet(self):
        self.received_packets += 1

# Router Class
class Router:
    def __init__(self, id, x, y, buffer_size, network):
        # Init
        self.id = id
        self.x = x
        self.y = y
        self.buffer_size = buffer_size
        self.network = network

        # Queues
        self.tcp_queues = {}        # Dictionary of TCP queues
        self.udp_queue = []         # Shared UDP queue

        # Constants
        self.isHost = False
    
    def send_packet(self, packet):
        # Send packet to a link
        source = packet['source']
        destination = packet['destination']
        if destination in self.routing_table:
            host = self.routing_table[destination]
            print("Host: " + str(host))
            if len(self.queues[host]) < self.buffer_size:
                self.queues[host].append(packet)
                print(f"Router {self.id}: Forwarded packet from {source.id} to Router {host.id}")
            else:
                # Drop packet if the queue is full
                print(f"Router {self.id}: Dropped packet from {packet['source'].id} to {destination.id}")

    def receive_packet(self, packet):
        # Add this packet to the queue
        if packet['type'] == 'TCP':
            host = packet['destination']
            self.tcp_queues[host].append(packet)
        elif packet['type'] == 'UDP':
            self.udp_queue.append(packet)

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
                    print(f"Sending {packet} from {self.source} to {self.destination} through a link")
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
    def __init__(self, num_hosts, num_routers, maxp, minth, maxth, wq):
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
            x, y = random.uniform(0, 10), random.uniform(0, 10)  # Random positions for simplicity
            host = Host(i, x, y, 1.5, 1.5, self)
            self.hosts.append(host)

        for i in range(num_routers):
            x, y = random.uniform(0, 10), random.uniform(0, 10)
            router = Router(i, x, y, 10, self)
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

        # Create a link between every router for simplicity (normally this wouldn't be the case)
        for router1 in self.routers:
            for router2 in self.routers:
                if router1.id == router2.id:
                    continue
                delay = random.randint(1, 5)    # Random delay between 1 and 5 ticks
                # Create link from router1 -> router2 
                link1 = Link(router1, router2, delay)
                self.links.append(link1)
                # No need to create a link from router2 -> router1, because it will happen later

    def run_simulation(self, ticks):
        for tick in range(ticks):
            self.simulate_tick(tick)
    
    def simulate_tick(self, _):
        # Process packets in the network
        for host in self.hosts:
            host.generate_packet()
            host.update_state()

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

# Main Execution

# Debug variable - set to True for debug messages
debug = True

# Initialize network parameters
num_hosts = 3
num_routers = 2
maxp = 0  # Max packet drop probability
minth = 1  # Min threshold for RED
maxth = 3  # Max threshold for RED
wq = 0.1  # Weight for RED average queue size

# Create the network
network = Network(num_hosts, num_routers, maxp, minth, maxth, wq)

# Run simulation
network.run_simulation(1000)  # Run for 1000 ticks
if debug:
    network.print_network_status()
    print("")

    # Peek at Router 0's queues (uncomment for debug)
    # for i in network.hosts[0].udp_queue:
    #     print(f"{i['type']}")

    # for queue in network.hosts[0].tcp_queues.values():
    #     for i in queue:
    #         print(f"{i['type']}")