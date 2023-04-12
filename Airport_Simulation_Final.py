
import math
import random
import pygame
import simpy


# Define the Cargo class (which will also be used for passengers)
class Cargo:
    def __init__(self, env, group, destination, size=1):
        # Current simulation environment
        self.env = env
        # Type of cargo: passenger or cargo
        self.group = group
        # Where the cargo needs to be delivered: airport object
        self.destination = destination
        # How many cargo slots does the item take (4 out of 80 capacity for one object)
        # Default value is 1 for passengers
        self.size = size


# Define the Plane class
class Plane:
    def __init__(self, env, gui, name, speed, passenger_capacity, cargo_capacity):
        # Current simulation environment
        self.env = env
        # Current pygame environment
        self.gui = gui
        # Name of the plane
        self.name = name
        # Speed of the plane
        self.speed = speed
        # Max number of passengers that can board the plane
        self.passenger_capacity = passenger_capacity
        # Max number of cargo that can board the plane
        self.cargo_capacity = cargo_capacity
        # Number of passengers on the plane
        self.passengers = []
        # Number of cargo on the plane
        self.cargo = []
        # Current space of cargo that are in the plane
        self.cargo_space = 0
        # Is a list of airport objects that the plane travels through.
        # Define in setup
        self.route = []
        # Airport that the plane is heading towards [referencing the index of route]
        # Define in setup
        self.destination = 0
        # Holds the Runway Resource
        self.runway = None
        # Holds the plane object for the gui
        self.plane = {}
        # Holds the plane name object for the gui
        self.plane_name = {}

    def land(self, a):
        # Wait for permission to land
        yield self.env.timeout(1)

        # Land the plane
        print(f'{self.env.now:.2f}: {self.name} has arrived at {a.name}')
        yield self.env.timeout(1)

    def takeoff(self, a):
        # Wait for permission to take off
        yield self.env.timeout(1)

        # Take off
        print(f'{self.env.now:.2f}: {self.name} has departed from {a.name} to {self.route[self.destination].name}')
        yield self.env.timeout(1)

    def travel(self):
        self.plane = {
            'type': "circle",
            'color': self.gui.color['BLACK'],
            'coords': self.route[self.destination-1].location.copy(),
            'size': 10
        }
        self.plane_name = {
            'type': "font",
            'name': self.name,
            'color': self.gui.color['BLACK'],
            'coords': self.route[self.destination-1].location.copy()
        }

        self.gui.dynamic_objects.append(self.plane)
        self.gui.dynamic_objects.append(self.plane_name)


        #Calculate the time it takes to travel
        dx = self.route[self.destination].location[0] - self.route[self.destination-1].location[0]
        dy = self.route[self.destination].location[1] \
             - self.route[self.destination-1].location[1]

        distance = math.sqrt(dx**2 + dy**2)
        travel_time = distance / self.speed

        # Move the plane to the destination airport
        print(f'distance to travel is {distance:.2f}')
        print(f'time to travel is {travel_time:.2f}')
        print(f'speed of travel is {self.speed:.2f}')

        vx = self.speed * math.cos(math.atan2(dy, dx))
        vy = self.speed * math.sin(math.atan2(dy, dx))

        for i in range(math.floor(travel_time)):
            print(f"x {self.plane['coords'][0]}, y {self.plane['coords'][1]}")
            self.plane['coords'][0] += vx
            self.plane_name['coords'][0] += vx
            self.plane['coords'][1] += vy
            self.plane_name['coords'][1] += vy
            yield self.env.timeout(1)
        self.gui.dynamic_objects.remove(self.plane)
        self.gui.dynamic_objects.remove(self.plane_name)

    def run(self):
        while True:
            pygame.event.get()
            self.gui.pygame_update()

            # ------------------------------------------------------Plane leaves airport
            # request and wait for resource
            self.route[self.destination-1].current_planes.append(self)
            self.runway = self.route[self.destination-1].runway.request()
            yield self.runway
            yield self.env.timeout(1)
            yield self.env.process(self.takeoff(self.route[self.destination-1]))

            # Release the runway resource
            yield self.route[self.destination-1].runway.release(self.runway)
            self.runway = None

            # ------------------------------------------------------Plane is flying
            yield self.env.process(self.travel())

            # ------------------------------------------------------Plane reaches airport
            yield self.env.process(self.land(self.route[self.destination]))

            # Plane route and the current location
            print(self.name, end=' route < ')
            for i in range(len(self.route)):
                if i == self.destination:
                    print("'"+str(self.route[i].name)+"'", end=' ')
                else:
                    print(self.route[i].name, end=' ')
            print(">")

            # If we reach the end of our route then we must turn back, and in turn we reverse the list
            if self.destination+1 > len(self.route)-1:
                self.route.reverse()
                self.destination = 1
            else:
                self.destination += 1





# Define the Airport class
class Airport:
    def __init__(self, env, gui, name, location, refuel_time, cargo_service_time, cargo_capacity,
                 passenger_service_time, passenger_capacity):
        # Current simulation environment
        self.env = env
        # Current pygame environment
        self.gui = gui
        # Name of the airport
        self.name = name
        # Absolute location on the pygame map
        self.location = location
        # planes that are currently in the airport
        # [plane, plane2, plane3]
        self.current_planes = []
        # Time it takes to refuel a plane
        # 15 - 20 min
        self.refuel_time = refuel_time
        # Time it takes for a cargo to enter or exit the plane
        # 22 min
        self.cargo_service_time = cargo_service_time
        # Maximum number of cargo that can be in the airport
        self.cargo_capacity = cargo_capacity
        # Time it takes for a passenger to enter or exit the plane
        # 20 min
        self.passenger_service_time = passenger_service_time
        # Maximum number of people that can be in the airport
        self.passenger_capacity = passenger_capacity
        # Current cargo that is in the airport
        self.cargo = []
        # Current space of cargo that are in the airport
        self.cargo_space = 0
        # Current number of people that are in the airport
        self.passengers = []
        # Prevents the plane from leaving until it acquires this resource
        self.runway = simpy.Resource(env, capacity=1)
        self.runway_value = self.runway.request()
        # To prevent infinite requests for the runway, we will only request if this value is false
        self.runway_queue = True
        # A list of all the other airports
        self.all_airports = []

    #plane does not have a fuel value, it is assumed the plane will never have 0% and plane refuel time
    def refuel(self, p):
        # Refuel the plane
        yield self.env.timeout(self.refuel_time)
        print(f'{self.env.now:.2f}: {p.name} is fully refueled')

    def service_passengers(self, p):
        # Service the passengers on the plane
        # Remove passengers from plane
        yield self.env.timeout(self.passenger_service_time)
        departed_passengers = 0
        for passenger in p.passengers:
            if passenger.destination == p.route[p.destination-1]:
                p.passengers.remove(passenger)
                del passenger
                departed_passengers += 1
        print(f'{env.now:.2f}: {p.name} delivered {departed_passengers} passengers')

        # Load passengers onto plane
        embarked_passengers = 0
        for passenger in self.passengers:
            if passenger.destination in p.route:
                if len(p.passengers) < p.passenger_capacity:
                    p.passengers.append(passenger)
                    self.passengers.remove(passenger)
                    embarked_passengers += 1
                else:
                    print(f'{env.now:.2f}: Passengers with destination "{passenger.destination.name}" cannot board the full {p.name}')
        print(f'{env.now:.2f}: {p.name} boarded {embarked_passengers} passengers')

        print(f'{self.env.now:.2f}: {p.name} has {len(p.passengers)}/{p.passenger_capacity} passengers')

    def service_cargo(self, p):
        # Service the cargo on the plane
        # Remove cargo from plane
        yield self.env.timeout(self.cargo_service_time)
        departed_cargo = 0
        for cargo in p.cargo:
            if cargo.destination == p.route[p.destination-1]:
                p.cargo.remove(cargo)
                p.cargo_space -= cargo.size
                del cargo
                departed_cargo += 1
        print(f'{env.now:.2f}: {p.name} delivered {departed_cargo} cargo')

        # Load cargo onto plane
        embarked_cargo = 0
        for cargo in self.cargo:
            if cargo.destination in p.route:
                if cargo.size + p.cargo_space <= p.cargo_capacity:
                    p.cargo.append(cargo)
                    self.cargo.remove(cargo)
                    p.cargo_space += cargo.size
                    self.cargo_space -= cargo.size
                    embarked_cargo += 1
                else:
                    print(f'{env.now:.2f}: Cargo with destination "{cargo.destination.name}" is too large to fit on {p.name}')
        print(f'{env.now:.2f}: {p.name} loaded {embarked_cargo} cargo')

        print(f'{self.env.now:.2f}: {p.name} has {p.cargo_space}/{p.cargo_capacity} cargo')

    def wait_for_service(self, p):
        # Wait for all services to complete
        services = [
            self.env.process(self.refuel(p)),
            self.env.process(self.service_passengers(p)),
            self.env.process(self.service_cargo(p))]
        yield self.env.timeout(1)
        yield simpy.AllOf(self.env, services)

    def run(self):
        while True:
            self.gui.pygame_update()
            yield self.env.timeout(1)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

            # Chance event to Generate Cargo at the airport
            if random.random() <= 0.1:
                for i in range(random.randint(1, 3)):
                    d = random.choice(self.all_airports)
                    if random.choice(['passenger', 'cargo']) == 'passenger':
                        if len(self.passengers) >= self.passenger_capacity:
                            print(f'{self.env.now:.2f}: {self.name} can not receive anymore passengers.')
                        else:
                            c = Cargo(self.env, 'passenger', d)
                            self.passengers.append(c)
                            print(f'{self.env.now:.2f}: Passenger spawned at {self.name}, with the destination {d.name}')
                    else:
                        s = random.randint(1, 5)
                        if self.cargo_space + s > self.cargo_capacity:
                            print(f'{self.env.now:.2f}: {self.name} can not receive anymore cargo.')
                        else:
                            c = Cargo(self.env, 'cargo', d, s)
                            self.cargo.append(c)
                            self.cargo_space += s
                            print(f'{self.env.now:.2f}: Cargo has spawned at {self.name}, with the destination {d.name}. '
                                  f'Capacity: {self.cargo_space}/{self.cargo_capacity}')

            # Occupy or withold the runway resource.
            if not self.runway_queue: # if runway_queue is false, then queue up, else dont
                self.runway_value = self.runway.request()
                self.runway_queue = True

            if len(self.current_planes) > 0:
                # There is a plane at the airport that needs to be serviced
                p = self.current_planes[0]

                yield self.env.process(self.wait_for_service(p))

                print(f'{self.env.now:.2f}: {p.name} is ready for departure')

                self.runway_queue = False
                yield self.runway.release(self.runway_value)

                self.current_planes = self.current_planes[1:]
            else:
                # There are no planes at the airport, so wait for one to arrive
                yield self.env.timeout(1)


class GUI:
    def __init__(self, env):
        self.env = env
        self.screen = None
        self.font = None
        self.const_objects = []
        self.dynamic_objects = []
        self.airports = []
        self.planes = []

        self.color = {
            'BLACK': (0, 0, 0),
            'WHITE': (255, 255, 255),
            'BROWN': (139, 69, 19),
            'DARK_BROWN': (92, 64, 51),
            'RED': (255, 0, 0),
            'GREEN': (0, 255, 0),
            'BLUE': (0, 0, 255),
            'YELLOW': (255, 255, 0),
            'CYAN': (0, 255, 255),
            'MAGENTA': (255, 0, 255),
            'SILVER': (192, 192, 192),
            'GRAY': (128, 128, 128),
            'MAROON': (128, 0, 0),
            'OLIVE': (128, 128, 0),
            'PURPLE': (128, 0, 128),
            'TEAL': (0, 128, 128),
            'NAVY': (0, 0, 128)
        }

    def pygame_start(self, Airports, Planes):
        self.airports = Airports
        self.planes = Planes
        # Initialize pygame
        pygame.init()

        # Set up window
        self.screen = pygame.display.set_mode((700, 600))
        pygame.display.set_caption('Airport Simulation')

        # Define font
        self.font = pygame.font.SysFont('Arial', 16)

        # Draw airports
        for i, airport in enumerate(self.airports):
            # Generate a random color for this airport

            # Draw circle for airport
            self.const_objects.append({
                'type': "circle",
                'color': self.color['WHITE'],
                'coords': airport.location.copy(),
                'size': 20
            })

            pygame.draw.circle(self.screen, self.color['WHITE'], airport.location, 20)

            # Render airport name text
            self.const_objects.append({
                'type': "font",
                'name': airport.name,
                'color': self.color['WHITE'],
                'coords': airport.location.copy(),
                'size': 20
            })

            self.const_objects.append({
                'type': "rectangle",
                'color': self.color['BROWN'],
                'coords': [500, 0, 200, 500]
            })
            self.const_objects.append({
                'type': "rectangle",
                'color': self.color['DARK_BROWN'],
                'coords': [0, 500, 700, 100]
            })

        # Render airport stats text
        self.const_objects.append({
            'type': "airport_legend",
            'color': self.color['WHITE'],
            'coords': [600, 50]
        })

        # Render plane stats text
        self.const_objects.append({
            'type': "plane_legend",
            'color': self.color['WHITE'],
            'coords': [100, 520]
        })

        pygame.display.update()

    def pygame_update(self):
        self.screen.fill(self.color['OLIVE'])

        for object in self.const_objects:
            if object['type'] == 'circle':
                pygame.draw.circle(self.screen, object['color'], object['coords'], object['size'])
            if object['type'] == 'font':
                name_surface = self.font.render(object['name'], True, object['color'])
                name_rect = name_surface.get_rect()
                name_rect.center = object['coords'][0], object['coords'][1] + 30
                self.screen.blit(name_surface, name_rect)
            if object['type'] == 'rectangle':
                pygame.draw.rect(self.screen, object['color'], pygame.Rect(object['coords'][0], object['coords'][1], object['coords'][2], object['coords'][3]))
            if object['type'] == 'airport_legend':
                temp = 20
                for a in self.airports:
                    text_surface = self.font.render(a.name+":", True, object['color'])
                    text_rect = text_surface.get_rect()
                    text_rect.center = 600, temp
                    self.screen.blit(text_surface, text_rect)
                    temp+=20
                    text_surface = self.font.render(str(len(a.current_planes))+" planes", True, object['color'])
                    text_rect = text_surface.get_rect()
                    text_rect.center = 600, temp
                    self.screen.blit(text_surface, text_rect)
                    temp+=20
                    text_surface = self.font.render(("cargo: "+str(a.cargo_space)+"/"+str(a.cargo_capacity)), True, object['color'])
                    text_rect = text_surface.get_rect()
                    text_rect.center = 600, temp
                    self.screen.blit(text_surface, text_rect)
                    temp+=20
                    text_surface = self.font.render(("passengers: "+str(len(a.passengers))+"/"+str(a.passenger_capacity)), True, object['color'])
                    text_rect = text_surface.get_rect()
                    text_rect.center = 600, temp
                    self.screen.blit(text_surface, text_rect)
                    temp+=50
            if object['type'] == 'plane_legend':
                temp = 0
                for p in self.planes:
                    route = "< "
                    for i in p.route:
                        if p.route[p.destination-1] == i:
                            route += "'"+str(i.name)+"' "
                        else:
                            route += i.name + " "
                    route += ">"

                    text_surface = self.font.render(p.name+":", True, object['color'])
                    text_rect = text_surface.get_rect()
                    text_rect.center = object['coords'][0]+temp, object['coords'][1]
                    self.screen.blit(text_surface, text_rect)
                    text_surface = self.font.render(route, True, object['color'])
                    text_rect = text_surface.get_rect()
                    text_rect.center = object['coords'][0]+temp, object['coords'][1]+20
                    self.screen.blit(text_surface, text_rect)
                    text_surface = self.font.render(("cargo: "+str(p.cargo_space)+"/"+str(p.cargo_capacity)), True, object['color'])
                    text_rect = text_surface.get_rect()
                    text_rect.center = object['coords'][0]+temp, object['coords'][1]+40
                    self.screen.blit(text_surface, text_rect)
                    text_surface = self.font.render(("passengers: "+str(len(p.passengers))+"/"+str(p.passenger_capacity)), True, object['color'])
                    text_rect = text_surface.get_rect()
                    text_rect.center = object['coords'][0]+temp, object['coords'][1]+60
                    self.screen.blit(text_surface, text_rect)
                    temp+=200

        for object in self.dynamic_objects:
            if object['type'] == 'circle':
                pygame.draw.circle(self.screen, object['color'], object['coords'], object['size'])
            if object['type'] == 'font':
                name_surface = self.font.render(object['name'], True, object['color'])
                name_rect = name_surface.get_rect()
                name_rect.center = object['coords'][0], object['coords'][1] + 30
                self.screen.blit(name_surface, name_rect)

        pygame.display.update()


env = simpy.rt.RealtimeEnvironment(factor=0.5)
sim_window = GUI(env)


planes = [
    Plane(env, sim_window, "Plane1", 20, 80, 20),
    Plane(env, sim_window, "Plane2", 30, 70, 30),
    Plane(env, sim_window, "Plane3", 40, 60, 40)
]
airports = [
    Airport(env, sim_window, "JFK", [100, 200], 15, 22, 50, 20, 200),
    Airport(env, sim_window, "LAX", [200, 400], 15, 22, 50, 20, 200),
    Airport(env, sim_window, "ORD", [400, 200], 15, 22, 50, 20, 200),
    Airport(env, sim_window, "DFW", [300, 300], 15, 22, 50, 20, 200),
]

# Create airport processes
airport_processes = []
for airport in airports:
    airport_processes.append(env.process(airport.run()))

    # give each airport a reference to the other airports
    for i in range(len(airports)):
        if airport != airports[i]:
            airport.all_airports.append(airports[i])

# Create plane processes
plane_processes = []
for plane in planes:
    # Assign the plane to a random airport
    plane.route = random.sample(airports, 3)
    for i in plane.route:
        print(f'plane-destinations: {i.name}')
    plane.destination = 1
    plane_processes.append(env.process(plane.run()))

# Start Pygame
sim_window.pygame_start(airports, planes)
# Run the simulation
env.run(until=300)
