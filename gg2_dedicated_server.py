import struct
import socket
import time
import threading
import random
import upnpy
import map_data_extractor


# --------------------------------------------------------------------------
# --------------------------------Variables---------------------------------
# --------------------------------------------------------------------------
# Lobby Registration Server Domain and port
REG_LOBBY_DOMAIN = "ganggarrison.com"
REG_LOBBY_PORT = 29944

# Server Hosting Port and UPNP toggle
SERVER_PORT = 8150
USE_UPNP = True

# Class Constants
CLASS_SCOUT = 0
CLASS_SOLDIER = 1
CLASS_SNIPER = 2
CLASS_DEMOMAN = 3
CLASS_MEDIC = 4
CLASS_ENGINEER = 5
CLASS_HEAVY = 6
CLASS_SPY = 7
CLASS_PYRO = 8
CLASS_QUOTE = 9

# Networking Constants
HELLO = 0
PLAYER_JOIN = 1
PLAYER_LEAVE = 2
PLAYER_CHANGETEAM = 3
PLAYER_CHANGECLASS = 4
PLAYER_SPAWN = 5

INPUTSTATE = 6
CHANGE_MAP = 7
FULL_UPDATE = 8
QUICK_UPDATE = 9
CAPS_UPDATE = 28

PLAYER_DEATH = 10
SERVER_FULL = 11

JOIN_UPDATE = 44

MESSAGE_STRING = 53

RESERVE_SLOT = 60


# --------------------------------------------------------------------------
# --------------------------------Functions---------------------------------
# --------------------------------------------------------------------------
# Updates lobby server of server existance
def registration(boolean):
    while(boolean):
        # Assembles Packet
        occupied_slots = struct.pack(">H", len(player_list)-1)
        num_bots = struct.pack(">H", 0)
        current_map_key_length = struct.pack(">B", 3)
        current_map_key = bytes("map", "utf-8")
        current_map_length = struct.pack(">H", 9)
        current_map = bytes("ctf_eiger", "utf-8")
        packet = REG_PACKET_ONE
            + occupied_slots
            + num_bots
            + REG_PACKET_TWO
            + current_map_key_length
            + current_map_key
            + current_map_length
            + current_map
            + REG_PACKET_THREE

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            # sock.sendto(packet, (UDP_IP, UDP_PORT)) #UDP WAY
            sock.connect((REG_LOBBY_DOMAIN, REG_LOBBY_PORT)) # COOLER TCP WAY
            sock.send(packet)
        print("---Registration Packet Sent---")
        time.sleep(30)


def upnp_port_mapping():
    while(True):
        # Gets host local ip
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as temp_socket:
            temp_sock.connect(("8.8.8.8", 80))
            HOST_IP = temp_sock.getsockname()[0]

        # UPNP port forwarding
        upnp = upnpy.UPnP()
        # Gets devices
        devices = upnp.discover()
        # Gets router I think
        device = upnp.get_igd()
        # Gets device services
        device.get_services()
        # Sets service
        service = device["WANIPConn1"]
        # Gets actions for said service
        service.get_actions()

        # Maps port
        service.AddPortMapping.get_input_arguments()
        service.AddPortMapping(
            NewRemoteHost="",
            NewExternalPort=SERVER_PORT,
            NewProtocol="TCP",
            NewInternalPort=SERVER_PORT,
            NewInternalClient=HOST_IP,
            NewEnabled=1,
            NewPortMappingDescription="GGPDS Port",
            NewLeaseDuration=150,
        )
        print("---UPNP Port Mapped---")
        time.sleep(135)


# --------------------------------------------------------------------------
# ----------------------------------Classes---------------------------------
# --------------------------------------------------------------------------
# Player Class
class Player:
    def __init__(self, connection, _id, name, team, _class):
        self.character_object = None
        self.connection = connection
        self._id = _id
        self.name = name
        self.team = team
        self._class = _class
        self.stats = [0]*11
        self.queue_jump = 0
        self.respawn_timer = 1


class Character:
    def __init__(self, player_object):
        self.player_object = player_object
        self.x = 0
        self.y = 0
        self.hspeed = 0
        self.vspeed = 0

        self.key_state = 0
        self.pressed_keys = 0
        self.released_keys = 0
        self.last_key_state = 0

        self.aim_direction = 0
        self.aim_distance = 0

        self.hp = 50


class gg2_map:
    def __init__(self, gg2_map_data):
        self.redspawns = []
        self.bluespawns = []
        self.intels = [None, None]
        for entity in gg2_map_data[0]:
            if(entity.type == "redintel"):
                self.intels[0] = entity
            elif(entity.type == "blueintel"):
                self.intels[1] = entity
            elif(entity.type == "redspawn"):
                self.redspawns.append(entity)
            elif(entity.type == "bluespawn"):
                self.bluespawns.append(entity)


class GameServer:
    def __init__(self):
        self.server_to_send = bytes("", "utf-8")
        self.new_connections = [];

    def add_connection(self, conn, addr):
        self.new_connections.append(conn)
        print(
            "Connections:"
            f"{len(self.new_connections) + len(player_list) - 1)}\n"
        )

    def serialize_state(self, update_type, client_player):
        to_send = struct.pack(">B", update_type)

        if(update_type == FULL_UPDATE):
            to_send += struct.pack("<H", 30) # >H is the intended one

        to_send += struct.pack(">B", len(player_list))

        # Writes player stats n stuff
        if(update_type != CAPS_UPDATE):
            for joining_player in player_list:
                to_send += struct.pack(">B", joining_player.stats[0])
                to_send += struct.pack(">B", joining_player.stats[1])
                to_send += struct.pack(">B", joining_player.stats[2])
                to_send += struct.pack(">B", joining_player.stats[3])
                to_send += struct.pack(">B", joining_player.stats[4])
                to_send += struct.pack(">B", joining_player.stats[5])
                to_send += struct.pack(">H", joining_player.stats[6])
                to_send += struct.pack(">B", joining_player.stats[7])
                to_send += struct.pack(">B", joining_player.stats[8])
                to_send += struct.pack(">B", joining_player.stats[9])
                to_send += struct.pack(">B", joining_player.stats[10])
                to_send += struct.pack(">B", 0)
                to_send += struct.pack(">H", 0)
                to_send += bytes("", "utf-8")
                # Dominations except I don't do them
                for victim in player_list:
                    if(joining_player != victim):
                        to_send += struct.pack(">B", 0)

                # Subojects except they don't exist yet fully
                if(client_player.character_object != None):
                    to_send += struct.pack(">B", 1)

                    # NEW
                    to_send += struct.pack(">B", client_player.character_object.key_state)
                    to_send += struct.pack("<H", client_player.character_object.aim_direction)
                    to_send += struct.pack(">B", client_player.character_object.aim_distance)
                    if(update_type == QUICK_UPDATE or update_type == FULL_UPDATE):
                         to_send += struct.pack("<H", client_player.character_object.x*5)
                         to_send += struct.pack("<H", client_player.character_object.y*5)
                         to_send += struct.pack(">b", client_player.character_object.hspeed*8.5)
                         to_send += struct.pack(">b", client_player.character_object.vspeed*8.5)
                         to_send += struct.pack(">B", ceil(client_player.character_object.hp))
                         # Temp Values
                         to_send += struct.pack(">B", 1)

                else:
                    to_send += struct.pack(">B", 0)

        if(update_type == FULL_UPDATE):
            # Red Intel
            to_send += struct.pack("<H", 1)
            # Multiply 5 because deserilized divide by 5
            to_send += struct.pack("<H", loaded_map.intels[0].x*5)
            to_send += struct.pack("<H", loaded_map.intels[0].y*5)
            to_send += struct.pack("<h", -1)
            # Blue Intel
            to_send += struct.pack("<H", 1)
            to_send += struct.pack("<H", loaded_map.intels[1].x*5)
            to_send += struct.pack("<H", loaded_map.intels[1].y*5)
            to_send += struct.pack("<h", -1)
            # Caps limit and caps and respawn time
            to_send += struct.pack(">B", 3)
            to_send += struct.pack(">B", 0)
            to_send += struct.pack(">B", 0)
            to_send += struct.pack(">B", 5)
            # CTF HUD
            to_send += struct.pack(">B", 15)
            to_send += struct.pack("<I", 25000)
            # Classlimits
            to_send += struct.pack(">B", 255)
            to_send += struct.pack(">B", 255)
            to_send += struct.pack(">B", 255)
            to_send += struct.pack(">B", 255)
            to_send += struct.pack(">B", 255)
            to_send += struct.pack(">B", 255)
            to_send += struct.pack(">B", 255)
            to_send += struct.pack(">B", 255)
            to_send += struct.pack(">B", 255)
            to_send += struct.pack(">B", 255)
        return to_send

    def join_player(self, conn):
        while True:
            try:
                data = conn.recv(1024)
            except ConnectionResetError:
                player_list.remove(client_player)
                print("New Connection Socket Disconnect")
                break
            if not data:
                print("New Connection Socket Disconnect")
                break
            print("Received New Connection Data")
            print(data)
            with open("connData.txt", "wb") as f:
                f.write(data)
            if(data[0] == HELLO):
                print("Received Hello")
                to_send = struct.pack(">B", 43)
                if(data[1:17] == PROTOCOL_ID):
                    print("Compatible Protocol Received")
                    # Assembles Response
                    to_send = struct.pack(">B", HELLO)
                    to_send += struct.pack(">B", 21)
                    to_send += bytes("Python Server Testing", "utf-8")
                    to_send += struct.pack(">B", 9)
                    to_send += bytes("ctf_eiger", "utf-8")
                    to_send += struct.pack(">B", 0)
                    to_send += bytes("", "utf-8")
                    to_send += struct.pack(">B", 0)
                    to_send += struct.pack(">H", 0)
                    to_send += bytes("", "utf-8")
                else:
                    print("Incompatible Protocol Received")
                    conn.sendall(to_send)
                    break

            elif(data[0] == RESERVE_SLOT):
                print("Received Reserve Slot")
                # Generates player ID for new player
                client_player_id = random.randint(1000, 9999)
                while(client_player_id in player_list):
                    client_player_id = random.randint(1000, 9999)
                # playerID, playerName, playerTeam, playerClass
                client_player = Player(
                    conn,
                    int(client_player_id),
                    str(data[2:data[1] + 2].decode()),
                    2,
                    0,
                )
                # Assembles Response
                to_send = struct.pack(">B", SERVER_FULL)
                if(4 < 5):
                    print("Slot Reserved")
                    to_send = struct.pack(">B", RESERVE_SLOT)
                else:
                    print("Server Full")
                    conn.sendall(to_send)
                    break

            elif(data[0] == PLAYER_JOIN):
                print("Received Player Join")
                # Writes JOIN_UPDATE with num of players and map area
                to_send = struct.pack(">B", JOIN_UPDATE)
                to_send += struct.pack(">B", len(player_list))
                to_send += struct.pack(">B", 1)

                # Writes the current map n stuff
                to_send += struct.pack(">B", CHANGE_MAP)
                to_send += struct.pack(">B", 9)
                to_send += bytes("ctf_eiger", "utf-8")
                to_send += struct.pack(">B", 0)
                to_send += bytes("", "utf-8")

                # Player joining n stuff
                for player_index, joining_player in enumerate(player_list):
                    to_send += struct.pack(">B", PLAYER_JOIN)
                    to_send += struct.pack(">B", len(joining_player.name))
                    to_send += bytes(joining_player.name, "utf-8")
                    # Set player class
                    to_send += struct.pack(">B", PLAYER_CHANGECLASS)
                    to_send += struct.pack(">B", player_index)
                    to_send += struct.pack(">B", joining_player._class)
                    # Sets player team
                    to_send += struct.pack(">B", PLAYER_CHANGETEAM)
                    to_send += struct.pack(">B", player_index)
                    to_send += struct.pack(">B", joining_player.team)
                # Writes FULL_UPDATE stuff
                to_send += self.serialize_state(FULL_UPDATE, client_player)

                player_list.append(client_player)
                # Server Player Join
                self.server_to_send += struct.pack(">B", PLAYER_JOIN)
                self.server_to_send += struct.pack(">B", len(client_player.name))
                self.server_to_send += bytes(client_player.name, "utf-8")

                # Server Message
                to_send += struct.pack(">B", MESSAGE_STRING)
                to_send += struct.pack(">B", 12)
                to_send += bytes("You Made It!", "utf-8")
                print("Sent New Connection Data Back")
                conn.sendall(to_send)
                print("Connection setup complete")
                registration(False)
                break
            print("Sent New Connection Data Back")
            conn.sendall(to_send)
        self.new_connections.remove(conn)

    def process_client_commands(self, player_to_service):
        conn = player_to_service.connection
        conn.settimeout(0.5)
        try:
            data = None
            data = conn.recv(1024)
            if not data:
                print("Player Socket Disconnect")
                return 0
            print("Received Player Data")
            print(data[0])
            print(data)
            with open("connData2.txt", "wb") as f:
                f.write(data)
            reading_position = 0;
            while reading_position <= (len(data)-1):
                if(data[reading_position] == PLAYER_LEAVE):
                    print("YO")
                    # Updates data reading position
                    reading_position = reading_position + 1

                elif(data[reading_position] == PLAYER_CHANGETEAM):
                    print("Received Change Team")
                    # Player Death
                    if(player_to_service.team != data[reading_position+1] and player_to_service.character_object != None):
                        self.server_to_send = struct.pack(">B", 10)
                        self.server_to_send += struct.pack(">B", 1)
                        self.server_to_send += struct.pack(">B", 1)
                        self.server_to_send += struct.pack(">B", 255)
                        self.server_to_send += struct.pack(">B", 25)

                    player_to_service.respawn_timer = 1
                    player_to_service.character_object = None
                    # Player Set Team
                    player_to_service.team = data[reading_position+1]
                    self.server_to_send += struct.pack(">B", PLAYER_CHANGETEAM)
                    self.server_to_send += struct.pack(">B", player_list.index(player_to_service))
                    self.server_to_send += struct.pack(">B", player_to_service.team)
                    # Updates data reading position
                    reading_position = reading_position + 2

                elif(data[reading_position] == PLAYER_CHANGECLASS):
                    print("Received Change Class")
                    player_to_service.respawn_timer = 1
                    player_to_service.character_object = None
                    # Player Set Class
                    player_to_service._class = data[reading_position+1]
                    self.server_to_send += struct.pack(">B", PLAYER_CHANGECLASS)
                    self.server_to_send += struct.pack(">B", player_list.index(player_to_service))
                    self.server_to_send += struct.pack(">B", player_to_service._class)
                    # Updates data reading position
                    reading_position = reading_position + 2

                elif(data[reading_position] == INPUTSTATE):
                    if(player_to_service.character_object != None):
                        player_to_service.character_object.key_state = data[reading_position+1]
                        player_to_service.character_object.aim_direction = struct.unpack("<H", data[reading_position+2:reading_position+4])[0] # *360/65536
                        player_to_service.character_object.aim_distance = data[reading_position+4]

                        player_to_service.character_object.pressed_keys |= player_to_service.character_object.key_state & ~player_to_service.character_object.last_key_state
                        player_to_service.character_object.released_keys |= ~player_to_service.character_object.key_state & player_to_service.character_object.last_key_state
                        player_to_service.character_object.last_key_state = player_to_service.character_object.key_state

                        print(player_to_service.character_object.pressed_keys)
                        print(player_to_service.character_object.released_keys)
                        print(player_to_service.character_object.last_key_state)
                    # Updates data reading position
                    reading_position = reading_position + 5

                else:
                    # self.server_to_send = 0
                    print("Not yet added thing")
                    # Lifeline
                    reading_position = reading_position + 1

                # print(str(reading_position) + "|" + str(len(data)-1))

            time.sleep(0.1)

        except ConnectionResetError:
            player_list.remove(player_to_service)
            print("Player Socket Disconnect")
        except TimeoutError:
            pass

    def process_client_alarms(self, player_to_service):
        # Respawn Alarm
        player_to_service.respawn_timer = player_to_service.respawn_timer - 1
        if(player_to_service.respawn_timer <= 0 and player_to_service.character_object == None and (player_to_service.team == 0 or player_to_service.team == 1) and (0 <= player_to_service._class and player_to_service._class <= 9)):
            # Player Spawning
            player_to_service.character_object = Character(player_to_service)
            self.server_to_send += struct.pack(">B", PLAYER_SPAWN)
            self.server_to_send += struct.pack(">B", player_list.index(player_to_service))
            if(player_to_service.team == 0):
                random_spawn = random.randint(0, len(loaded_map.redspawns)-1)
                self.server_to_send += struct.pack(">B", random_spawn)
                # Spawning red player locally
                player_to_service.character_object.x = loaded_map.redspawns[random_spawn].x
                player_to_service.character_object.y = loaded_map.redspawns[random_spawn].y
            elif(player_to_service.team == 1):
                random_spawn = random.randint(0, len(loaded_map.bluespawns)-1)
                self.server_to_send += struct.pack(">B", random_spawn)
                # Spawning blue player locally
                player_to_service.character_object.x = loaded_map.bluespawns[random_spawn].x
                player_to_service.character_object.y = loaded_map.bluespawns[random_spawn].y
            self.server_to_send += struct.pack(">B", 0)
            print("Spawned Player")

    def run_game_server_networking(self):
        self.server_to_send = bytes("", "utf-8")
        while True:
            # Processes client commands
            if(1 < len(player_list)):
                for player_to_service in player_list:
                    if(player_to_service._id != 1000):
                        self.process_client_commands(player_to_service)

            # Alarm Updating Here
            if(1 < len(player_list)):
                for player_to_service in player_list:
                    if(player_to_service._id != 1000):
                        self.process_client_alarms(player_to_service)

            # Position/physics object updating here

            # Joins 1 new player each loop
            if(0 < len(self.new_connections)):
                self.join_player(self.new_connections[0])

            # Sends update to all players
            if(0 < len(self.server_to_send)):
                for player_to_service in player_list:
                    if(player_to_service._id != 1000):
                        conn = player_to_service.connection
                        conn.sendall(self.server_to_send)

            # Clears data to send
            self.server_to_send = bytes("", "utf-8")
            time.sleep(0.01)

    def run_game_server(self):
        while True:
            if(1 < len(player_list)):
                for player_to_service in player_list:
                    if(player_to_service._id != 1000):
                        if(player_to_service.character_object == None and player_to_service.respawn_timer <= 0 and (player_to_service.team == 0 or player_to_service.team == 1) and (0 <= player_to_service._class and player_to_service._class <= 9)):
                            player_to_service.character_object = Character(player_to_service)
                            print("Player Character Created")

            time.sleep(0.01)


# --------------------------------------------------------------------------
# --------------END OF DEFINING START OF CODE EXECUTION---------------------
# --------------------------------------------------------------------------
# Creates list for players
player_list = [Player(None, 1000, "Host", 2, 0)]


# Stuff below is setting up packet for registration
# Registration Packet 1
REG_PACKET_ONE = struct.pack(
    ">16B",
    181,
    218,
    226,
    232,
    66,
    79,
    158,
    208,
    15,
    203,
    140,
    33,
    199,
    202,
    19,
    82,
) # Registration ID
REG_PACKET_ONE += struct.pack(
    ">16B",
    17,
    211,
    119,
    67,
    190,
    25,
    205,
    141,
    171,
    76,
    89,
    102,
    234,
    11,
    69,
    132,
) # Server ID
REG_PACKET_ONE += struct.pack(
    ">16B",
    28,
    207,
    22,
    177,
    67,
    109,
    133,
    111,
    80,
    77,
    204,
    26,
    243,
    6,
    170,
    167,
)  # Lobby ID
REG_PACKET_ONE += struct.pack(">B", 0)           # Connection Type (UDP or TCP)
REG_PACKET_ONE += struct.pack(">H", SERVER_PORT) # Hosting Port
REG_PACKET_ONE += struct.pack(">H", 5)           # Player Limit

# Registration Packet 2
REG_PACKET_TWO = struct.pack(">H", 0)  # Server Password
REG_PACKET_TWO += struct.pack(">H", 7) # Amount of Value Groups
# Server Name
# Server Name Key Length
REG_PACKET_TWO += struct.pack(">B", 4)
# Server Name Key
REG_PACKET_TWO += bytes("name", "utf-8")
# Server Name Length
REG_PACKET_TWO += struct.pack(">H", 21)
# Server Name
REG_PACKET_TWO += bytes("Python Server Testing", "utf-8")
# Game Name
# Game Name Key Length
REG_PACKET_TWO += struct.pack(">B", 4)
# Game Name Key
REG_PACKET_TWO += bytes("game", "utf-8")
# Game Name Length
REG_PACKET_TWO += struct.pack(">H", 15)
# Game Name
REG_PACKET_TWO += bytes("Gang Garrison 2", "utf-8")
# Game Short
# Game Short Key Length
REG_PACKET_TWO += struct.pack(">B", 10)
# Game Short Key
REG_PACKET_TWO += bytes("game_short", "utf-8")
# Game Short Length
REG_PACKET_TWO += struct.pack(">H", 3)
# Game Short
REG_PACKET_TWO += bytes("gg2", "utf-8")
# Game Version
# Game Version Key Length
REG_PACKET_TWO += struct.pack(">B", 8)
# Game Version Key
REG_PACKET_TWO += bytes("game_ver", "utf-8")
# Game Version Length
REG_PACKET_TWO += struct.pack(">H", 6)
# Game Version
REG_PACKET_TWO += bytes("v2.9.2", "utf-8")
# Game URL
# Game URL Key Length
REG_PACKET_TWO += struct.pack(">B", 8)
# Game URL Key
REG_PACKET_TWO += bytes("game_url", "utf-8")
# Game URL Length
REG_PACKET_TWO += struct.pack(">H", 27)
# Game URL
REG_PACKET_TWO += bytes("http://www.ganggarrison.com", "utf-8")

# Registration Packet Const 3
REG_PACKET_THREE = struct.pack(">B", 11)             # Protocol ID Key Length
REG_PACKET_THREE += bytes("protocol_id", "utf-8")    # Protocol ID Key
REG_PACKET_THREE += struct.pack(">H", 16)            # Protocol ID Length
PROTOCOL_ID = struct.pack(
    ">16B",
    179,
    28,
    34,
    9,
    66,
    86,
    154,
    25,
    208,
    239,
    199,
    28,
    83,
    115,
    189,
    117
) # Protocol ID
REG_PACKET_THREE += PROTOCOL_ID

def main():
    # Maps UPNP port if UPNP is enabled
    if(USE_UPNP == True):
        upnp_thread = threading.Thread(target = upnp_port_mapping, args = ())
        upnp_thread.start()
        time.sleep(5)


    # Starts registration loop thread
    reg_thread = threading.Thread(target = registration, args = (True))
    reg_thread.start()

    # Gets map entities and wallmask
    global loaded_map
    loaded_map = gg2_map(map_data_extractor.extract_map_data("ctf_eiger.png"))

    time.sleep(0.1)
    game_server = GameServer()
    server_networking_thread = threading.Thread(
        target = GameServer.run_game_server_networking,
        args = (game_server)
    )
    server_networking_thread.start()

    time.sleep(0.1)
    # Listens for connections and starts a thread to handle them
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", SERVER_PORT))
        s.listen()
        print(f"Listening on port {SERVER_PORT}")
        while True:
            conn, addr = s.accept()
            print("Accepted connection from", addr)
            game_server.add_connection(conn, addr)

def upnp_exit():
    upnp = upnpy.UPnP()
    # Gets devices
    devices = upnp.discover()
    # Gets router I think
    device = upnp.get_igd()
    # Gets device services
    device.get_services()
    # Sets service
    service = device["WANIPConn1"]
    # Gets actions for said service
    service.get_actions()

    service.DeletePortMapping.get_input_arguments()
    # Finally, add the new port mapping to the IGD
    # This specific action returns an empty dict: {}
    service.DeletePortMapping(
        NewRemoteHost = "",
        NewExternalPort = SERVER_PORT,
        NewProtocol = "TCP"
    )

if __name__ == "__main__":
    if SERVER_PORT < 0:
        exit()

    try:
        main()
    except Exception as e:
        print(f"EXCEPTION: {e}")
    finally:
        if USE_UPNP:
            upnp_exit()

        exit()
