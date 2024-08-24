import struct
import socket
import time
import threading
import random
import upnpy
import math
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

# Map File
map_file_path = "ctf_eiger.png"

# Server player name
host_name = "Host"

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
def registration(should_loop):
    while should_loop:
        # Assembles Packet
        occupied_slots = struct.pack(">H", len(player_list) - 1)
        num_bots = struct.pack(">H", 0)
        current_map_key_length = struct.pack(">B", 3)
        current_map_key = bytes("map", "utf-8")
        current_map_length = struct.pack(">H", 9)
        current_map = bytes("ctf_eiger", "utf-8")
        packet = (REG_PACKET_ONE
            + occupied_slots
            + num_bots
            + REG_PACKET_TWO
            + current_map_key_length
            + current_map_key
            + current_map_length
            + current_map
            + REG_PACKET_THREE)

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            # sock.sendto(packet, (UDP_IP, UDP_PORT)) #UDP WAY
            sock.connect((REG_LOBBY_DOMAIN, REG_LOBBY_PORT)) # COOLER TCP WAY
            sock.send(packet)
        print("---Registration Packet Sent---")
        time.sleep(30)


def upnp_port_mapping():
    while True:
        # Gets host local ip
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as temp_socket:
            temp_socket.connect(("8.8.8.8", 80))
            HOST_IP = temp_socket.getsockname()[0]

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


def hex_as_int(input_value):
    return int(hex(input_value), 16)

def num_to_bool(input_num):
    if input_num > 0.5:
        return True
    else:
        return False

def sign(input_num):
    if input_num < 0:
        return -1
    elif 0 < input_num:
        return 1
    else:
        return 0

def point_direction(x1, y1, x2, y2):
    return math.degrees(math.atan2(-(y2-y1), x2-x1)) % 360

def degtorad(degrees):
    return degrees * math.pi / 180


# --------------------------------------------------------------------------
# ----------------------------------Classes---------------------------------
# --------------------------------------------------------------------------
class characterMask:
    def __init__(self, xPos1, yPos1, width, height):
        self.x1 = xPos1
        self.y1 = yPos1
        self.width = width
        self.height = height


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
        self.applied_gravity = 0

        self.key_state = 0x0
        self.pressed_keys = 0x0
        self.released_keys = 0x0
        self.last_key_state = 0x0
        self.move_status = 0x0

        self.net_aim_direction = 0
        self.aim_direction = 0
        self.aim_distance = 0

        self.humiliated = False
        self.taunting = False
        self.omnomnomnom = False

        self.hp = 50

    def place_free(self, xPos, yPos): # [characterMask(-6, -10, 12, 33)]
        collisions = []
        rect2_x = xPos + class_masks[0].x1
        rect2_y = yPos + class_masks[0].y1
        rect2_width = class_masks[0].width
        rect2_height = class_masks[0].height
        
        for rect1 in loaded_map.wm_collision_rects:
            if (rect1.x < rect2_x + rect2_width and
                    rect1.x + rect1.width > rect2_x and
                    rect1.y < rect2_y + rect2_height and
                    rect1.y + rect1.height > rect2_y):
                collisions.append(rect1)
        if(len(collisions) > 0):
            return False
        else:
            return True

    def move_outside_solid(self, direction, max_dist):
        if direction == 0:
            self.x += max_dist
        elif direction == 90:
            self.y -= max_dist
        elif direction == 180:
            self.x -= max_dist
        elif direction == 270:
            self.y += max_dist

    def good_move_contact_solid(self, arg0, arg1):
        if arg0 <= 0:
            return 0;

        MAX_I = 8
        i = 8
        max_distance = arg1
        hvec = math.cos(degtorad(arg0)) * max_distance
        vvec = -math.sin(degtorad(arg0)) * max_distance
        sfac = max(abs(hvec), abs(vvec))
        total_moved = 0
        last_collision_happened = False

        while total_moved < max_distance and i > 0:
            move_x = hvec/sfac * i/MAX_I * min(1, max_distance - total_moved)
            move_y = vvec/sfac * i/MAX_I * min(1, max_distance - total_moved)

            new_x = self.x + move_x*i/MAX_I
            new_y = self.y + move_y*i/MAX_I
            if self.place_free(new_x, new_y):
                total_moved += math.dist([self.x, self.y], [new_x, new_y])
                self.x = new_x
                self.y = new_y
                if i < MAX_I:
                    break
            else:
                last_collision_happened = True
                i -= 1

        return total_moved

    def character_hit_obstacle(self):
        old_x = self.x
        old_y = self.y
        old_hspeed = self.hspeed
        old_vspeed = self.vspeed
        bbox_height = class_masks[0].height
        bbox_width = class_masks[0].width

        if not self.place_free(self.x, self.y):
            self.move_outside_solid(90, bbox_height/2)
            distu = old_y - self.y
            uy = self.y
            self.y = old_y
            
            self.move_outside_solid(270, bbox_height/2)
            distd = self.y - old_y
            dy = self.y
            self.y = old_y
            
            self.move_outside_solid(0, bbox_width/2)
            distr = self.x - old_x
            rx = self.x
            self.x = old_x
            
            self.move_outside_solid(180, bbox_width/2)
            distl = old_x - self.x
            lx = self.x
            self.x = old_x

            if distu < distd and distu < distr and distu < distl:
                self.y = uy
            elif distd < distr and distd < distl:
                self.y = dy
            elif distr < distl:
                self.x = rx
            else:
                self.x = lx
            
            if not self.place_free(self.x, self.y):
                self.x = old_x
                self.y = old_y

        hleft = self.hspeed
        vleft = self.vspeed
        loop_counter = 0
        stuck = 0
        while (abs(hleft) > 0.1 or abs(vleft) > 0.1) and stuck == 0:
            loop_counter += 1
            if loop_counter > 10:
                stuck = 1

            collision_rectified = False
            prev_x = self.x
            prev_y = self.y
            
            self.good_move_contact_solid(point_direction(self.x, self.y, self.x + hleft, self.y + vleft), math.dist([self.x, self.y], [self.x + hleft, self.y + vleft]))

            hleft -= self.x - prev_x
            vleft -= self.y - prev_y

            if vleft != 0 and not self.place_free(self.x, self.y + sign(vleft)):
                if vleft > 0:
                    self.move_status = 0
                vleft = 0
                self.vspeed = 0
                collision_rectified = True

            if hleft != 0 and not self.place_free(self.x + sign(hleft), self.y):
                if self.place_free(self.x + sign(hleft), self.y - 6):
                    self.y -= 6
                    collision_rectified = True
                    self.move_status = 0
                elif self.place_free(self.x + sign(hleft), self.y + 6) and abs(self.hspeed) >= abs(self.vspeed):
                    self.y += 6
                    collision_rectified = True
                    self.move_status = 0
                else:
                    hleft = 0
                    self.hspeed = 0
                    collision_rectified = True
            if not collision_rectified and (abs(hleft) >= 1 or abs(vleft) >= 1):
                self.vspeed = 0
                vleft = 0

            self.hspeed /= 1
            self.vspeed /= 1


    def begin_step(self):
        stuck_in_wall = not self.place_free(self.x, self.y)
        obstacle_below = not self.place_free(self.x, self.y+1);
        on_ground = False
        on_non_surfing_ground = False

        if self.vspeed >= 0:
            if obstacle_below:
                on_ground = True
                on_non_surfing_ground = True
            elif not (int(hex(self.key_state), 16) & 0x02):
                # I ain't adding dropdowns soon
                pass

        if on_non_surfing_ground:
            self.move_status = 0
        if on_ground:
            double_jump_used = 0;

        # Afterburn here

        # Input Handling
        if False:
            if num_to_bool(hex_as_int(self.pressed_keys) & 0x80):
                want_to_jump = True
            elif num_to_bool(hex_as_int(self.released_keys) & 0x80):
                want_to_jump = False

        if not self.taunting and not self.omnomnomnom:
            if not self.humiliated and num_to_bool((hex_as_int(self.key_state) | hex_as_int(self.pressed_keys)) & 0x10):
                # Weapon fire here
                pass
            if not self.humiliated and self.pressed_keys & 0x01:
                # Taunting Stuff
                if False:
                    pass

            if ((num_to_bool(hex_as_int(self.pressed_keys) & 0x80)) or (False and want_to_jump)) and self.vspeed > -8.3:
                if on_ground and not stuck_in_wall:
                    if True:
                        want_to_jump = False
                        self.vspeed = -8.3
                        on_ground = False
                        print("done jump")
            elif False and not double_jump_used:
                want_to_jump = False
                self.vspeed = -8.3
                on_ground = false;
                move_status = 0;

        # Move Status stuff

        # Horizonal Movement
        controlling = False
        for x in range(2):
            if not self.taunting and not self.omnomnomnom:
                if num_to_bool((hex_as_int(self.key_state) | hex_as_int(self.pressed_keys)) & 0x40) and self.hspeed >= -(1.4 * 0.85 / (1.15-1)):
                    self.hspeed -= 1.4*0.85 * 0.5;
                    controlling = True;
                if num_to_bool((hex_as_int(self.key_state) | hex_as_int(self.pressed_keys)) & 0x20) and self.hspeed <= 1.4 * 0.85 / (1.15-1):
                    self.hspeed += 1.4*0.85 * 0.5;
                    controlling = not controlling;

        # Stuff in between to implement

        if abs(self.hspeed) > (1.4 * 0.85 / (1.15-1)) * 2 or (num_to_bool((hex_as_int(self.key_state) | hex_as_int(self.pressed_keys)) & 0x60) and abs(self.hspeed) < (1.4 * 0.85 / (1.15-1))):
            self.hspeed /= (1.15 * 0.5 + (1-1*0.5))
        else:
            self.hspeed /= (1.15 * 0.5 + (1-1*0.5))

        self.pressed_keys = 0
        self.released_keys = 0

        # Stop "ice skating"
        if abs(self.hspeed) < 0.195 and not controlling:
            self.hspeed = 0


        if not on_ground and not stuck_in_wall:
            if False:
                self.applied_gravity += 0.54
            else:
                self.applied_gravity += 0.6

    def normal_step(self):
        self.hspeed = min(abs(self.hspeed), 15) * sign(self.hspeed)
        self.vspeed = min(abs(self.vspeed), 15) * sign(self.vspeed)

        #print("X: " + str(self.hspeed))
        #print("Y: " + str(self.vspeed))

        # Spin jumping here

        # Move status here

        # Gravity
        self.vspeed += self.applied_gravity*0.5
        if self.vspeed > 10:
            self.vspeed = 10

        y_previous = self.y
        x_previous = self.x

        doHit = not self.place_free(self.x + self.hspeed, self.y + self.vspeed)
        #print("X: " + str(self.x + self.hspeed))
        #print("Y: " + str(self.y + self.vspeed))
        if doHit:
            self.character_hit_obstacle()
        else:
            self.x += self.hspeed
            self.y += self.vspeed

        # Fallback?
        if self.place_free(self.x, self.y + 1):
            self.vspeed += self.applied_gravity*0.5
        if self.vspeed > 10:
            self.vspeed = 10
        self.applied_gravity = 0

        # Dropdown platforms? Never heard of them

        #self.x -= self.hspeed
        #self.y -= self.vspeed

        self.x += self.hspeed
        self.y += self.vspeed

        #if self.hspeed != 0:
        #    print("HSPEED: " + str(self.hspeed))
        #if self.vspeed != 0:
        #    print("VSPEED: " + str(self.vspeed))


class GG2Map:
    def __init__(self, gg2_map_data):
        # Wallmask rectangles for collision checking
        self.wm_collision_rects = gg2_map_data[1]

        # GG2 map's collision entities
        self.redspawns = []
        self.bluespawns = []
        self.intels = [None, None]
        for entity in gg2_map_data[0]:
            if entity.type == "redintel":
                self.intels[0] = entity
            elif entity.type == "blueintel":
                self.intels[1] = entity
            elif entity.type == "redspawn":
                self.redspawns.append(entity)
            elif entity.type == "bluespawn":
                self.bluespawns.append(entity)


class GameServer:
    def __init__(self):
        self.server_to_send = bytes("", "utf-8")
        self.new_connections = [];

    def add_connection(self, conn, addr):
        self.new_connections.append(conn)
        print(
            "Connections:"
            f"{len(self.new_connections) + len(player_list) - 1}\n"
        )

    def serialize_state(self, update_type):
        to_send = struct.pack(">B", update_type)

        if update_type == FULL_UPDATE:
            # tdm invulnerability ticks
            to_send += struct.pack("<H", 30)

        to_send += struct.pack(">B", len(player_list))

        # Adds each player's data for update
        if update_type != CAPS_UPDATE:
            for joining_player in player_list:
                if update_type == FULL_UPDATE:
                    to_send += struct.pack(">B", joining_player.stats[0])  # Kills
                    to_send += struct.pack(">B", joining_player.stats[1])  # Deaths
                    to_send += struct.pack(">B", joining_player.stats[2])  # Caps
                    to_send += struct.pack(">B", joining_player.stats[3])  # Assists
                    to_send += struct.pack(">B", joining_player.stats[4])  # Destruction
                    to_send += struct.pack(">B", joining_player.stats[5])  # Stabs
                    to_send += struct.pack("<H", joining_player.stats[6])  # Healing
                    to_send += struct.pack(">B", joining_player.stats[7])  # Defenses
                    to_send += struct.pack(">B", joining_player.stats[8])  # Invulns
                    to_send += struct.pack(">B", joining_player.stats[9])  # Bonus
                    to_send += struct.pack(">B", joining_player.stats[10]) # Points
                    to_send += struct.pack(">B", 0)  # Queue Jump (Temp Value)
                    to_send += struct.pack("<H", 0)  # Rewards length (Temp Value)
                    to_send += bytes("", "utf-8")    # Rewards String (Temp Value)
                    
                    # Dominations (Temp value)
                    for victim in player_list:
                        if joining_player != victim:
                            to_send += struct.pack(">B", 0)

                # Subojects (Character, Weapon, Sentry)
                if joining_player.character_object is not None:
                    # Subobject count
                    to_send += struct.pack(">B", 1)

                    # Input & Aiming
                    to_send += struct.pack(">B", joining_player.character_object.key_state)
                    to_send += struct.pack("<H", joining_player.character_object.net_aim_direction)
                    to_send += struct.pack(">B", int(joining_player.character_object.aim_distance/2))
                    
                    if update_type == QUICK_UPDATE or update_type == FULL_UPDATE:
                        to_send += struct.pack("<H", int(joining_player.character_object.x*5))
                        to_send += struct.pack("<H", int(joining_player.character_object.y*5))
                        to_send += struct.pack(">b", int(joining_player.character_object.hspeed*8.5))
                        to_send += struct.pack(">b", int(joining_player.character_object.vspeed*8.5))
                        to_send += struct.pack(">B", math.ceil(joining_player.character_object.hp))
                        to_send += struct.pack(">B", 2)  # Ammo Count (Temp Value)
                        
                        to_send += struct.pack(">B", ((joining_player.character_object.move_status & 0x7) << 1))
                        
                    if update_type == FULL_UPDATE:
                        # Temp Misc and Intel values
                        to_send += struct.pack(">B", 0)
                        to_send += struct.pack(">B", 0)
                        
                        to_send += struct.pack("<h", 0)
                        to_send += struct.pack(">B", 0)
                        to_send += struct.pack("<h", 0)

                        # Temp Weapon Values
                        to_send += struct.pack(">B", 0)
                        to_send += struct.pack(">B", 0)
                        
                else:
                    # Subobject count
                    to_send += struct.pack(">B", 0)

        if update_type == FULL_UPDATE:
            # Red Intel
            to_send += struct.pack("<H", 1)
            to_send += struct.pack("<H", loaded_map.intels[0].x*5)
            to_send += struct.pack("<H", loaded_map.intels[0].y*5)
            to_send += struct.pack("<h", -1)
            # Blue Intel
            to_send += struct.pack("<H", 1)
            to_send += struct.pack("<H", loaded_map.intels[1].x*5)
            to_send += struct.pack("<H", loaded_map.intels[1].y*5)
            to_send += struct.pack("<h", -1)
            # Cap limit, red caps, blue caps, server respawn time
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
            if data[0] == HELLO:
                print("Received Hello")
                to_send = struct.pack(">B", 43)
                if data[1:17] == PROTOCOL_ID:
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

            elif data[0] == RESERVE_SLOT:
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
                if 4 < 5:
                    print("Slot Reserved")
                    to_send = struct.pack(">B", RESERVE_SLOT)
                else:
                    print("Server Full")
                    conn.sendall(to_send)
                    break

            elif data[0] == PLAYER_JOIN:
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
                to_send += self.serialize_state(FULL_UPDATE)

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
        conn.settimeout(0)
        commands_done = 0
        
        while 10 > commands_done:
            data = None
            try:
                data = conn.recv(1)
            except BlockingIOError:
                commands_done = 10
                break
            except ConnectionResetError:
                player_list.remove(player_to_service)
                print("Connection Reset Error")
                print("Player Socket Disconnect")
                commands_done = 10
                break
            except TimeoutError:
                print("Timeout?")
                commands_done = 10
                break
            
            # print("Received Player Data")
            # print(data[0])
            # print(data)

            # Reactions to client data
            if data[0] == PLAYER_LEAVE:
                print("Player Left???")
                conn.close()
                player_list.remove(player_to_service)

            elif data[0] == PLAYER_CHANGETEAM:
                print("Received Change Team")
                # Player Death
                data = conn.recv(1)
                print("Current team: " + str(player_to_service.team) + " New Team: " + str(data[0]))
                if player_to_service.team != data[0] and player_to_service.character_object is not None:
                    self.server_to_send = struct.pack(">B", 10)
                    self.server_to_send += struct.pack(">B", player_list.index(player_to_service))
                    self.server_to_send += struct.pack(">B", player_list.index(player_to_service))
                    self.server_to_send += struct.pack(">B", 255)
                    self.server_to_send += struct.pack(">B", 25)
                    print("Killed Player")

                    player_to_service.respawn_timer = 5
                    player_to_service.character_object = None
                    
                # Player Set Team
                player_to_service.team = data[0]
                self.server_to_send += struct.pack(">B", PLAYER_CHANGETEAM)
                self.server_to_send += struct.pack(">B", player_list.index(player_to_service))
                self.server_to_send += struct.pack(">B", player_to_service.team)

            elif data[0] == PLAYER_CHANGECLASS:
                print("Received Change Class")
                player_to_service.respawn_timer = 5
                player_to_service.character_object = None
                # Player Set Class
                data = conn.recv(1)
                player_to_service._class = data[0]
                self.server_to_send += struct.pack(">B", PLAYER_CHANGECLASS)
                self.server_to_send += struct.pack(">B", player_list.index(player_to_service))
                self.server_to_send += struct.pack(">B", player_to_service._class)

            elif data[0] == INPUTSTATE:
                if player_to_service.character_object is not None:
                    data = conn.recv(1)
                    player_to_service.character_object.key_state = data[0]
                    data = conn.recv(2)
                    player_to_service.character_object.net_aim_direction = struct.unpack("<H", data[0:2])[0]
                    player_to_service.character_object.aim_direction = player_to_service.character_object.net_aim_direction*360/65536
                    data = conn.recv(1)
                    player_to_service.character_object.aim_distance = data[0]

                    player_to_service.character_object.pressed_keys |= player_to_service.character_object.key_state & ~player_to_service.character_object.last_key_state
                    player_to_service.character_object.released_keys |= ~player_to_service.character_object.key_state & player_to_service.character_object.last_key_state
                    player_to_service.character_object.last_key_state = player_to_service.character_object.key_state
                else:
                    data = conn.recv(4)

            else:
                print("Not yet added thing")
                print(struct.unpack(">B", data))
                print(struct.unpack(">b", data))
                print(data)
            
            commands_done += 1

    def process_client_alarms(self, player_to_service):
        # Respawn Alarm
        player_to_service.respawn_timer = player_to_service.respawn_timer - 1
        if (player_to_service.respawn_timer <= 0
                and player_to_service.character_object is None
                and (player_to_service.team == 0
                     or player_to_service.team == 1)
                and (0 <= player_to_service._class
                     and player_to_service._class <= 9)):
            print(player_to_service.team);
            # Player Spawning
            player_to_service.character_object = Character(player_to_service)
            self.server_to_send += struct.pack(">B", PLAYER_SPAWN)
            self.server_to_send += struct.pack(
                ">B",
                player_list.index(player_to_service),
            )
            if player_to_service.team == 0:
                random_spawn = random.randint(0, len(loaded_map.redspawns) - 1)
                self.server_to_send += struct.pack(">B", random_spawn)
                # Spawning red player locally
                player_to_service.character_object.x = loaded_map.redspawns[
                    random_spawn
                ].x
                player_to_service.character_object.y = loaded_map.redspawns[
                    random_spawn
                ].y
            elif player_to_service.team == 1:
                random_spawn = random.randint(0,len(loaded_map.bluespawns) - 1)
                self.server_to_send += struct.pack(">B", random_spawn)
                # Spawning blue player locally
                player_to_service.character_object.x = loaded_map.bluespawns[
                    random_spawn
                ].x
                player_to_service.character_object.y = loaded_map.bluespawns[
                    random_spawn
                ].y
            self.server_to_send += struct.pack(">B", 0)
            print("Spawned Player")

    def run_game_server_networking(self):
        self.server_to_send = bytes("", "utf-8")
        frame = 0
        while True:
            start_time = time.time()

            if len(player_list) > 1:
                # Begin step collisions
                for player_to_service in player_list:
                    if player_to_service._id != 1000:
                        if player_to_service.character_object is not None:
                            player_to_service.character_object.begin_step()
            

            # Joins one new player each loop
            if self.new_connections:
                self.join_player(self.new_connections[0])

            if len(player_list) > 1:
                frame = frame + 1
                
                # Processes player/client commands
                for player_to_service in player_list:
                    if player_to_service._id != 1000:
                        self.process_client_commands(player_to_service)

                # Send players server update
                if (frame % 7) == 0:
                    self.server_to_send += self.serialize_state(QUICK_UPDATE)
                else:
                    self.server_to_send += self.serialize_state(INPUTSTATE)
                    
                # Alarm Updating
                for player_to_service in player_list:
                    if player_to_service._id != 1000:
                        self.process_client_alarms(player_to_service)

                # Position/physics object updating here
                for player_to_service in player_list:
                    if player_to_service._id != 1000:
                        if player_to_service.character_object is not None:
                            player_to_service.character_object.normal_step()

            # Sends update to all players
            if self.server_to_send:
                for player_to_service in player_list:
                    if player_to_service._id != 1000:
                        try:
                            conn = player_to_service.connection
                            conn.sendall(self.server_to_send)
                        except ConnectionResetError:
                            player_list.remove(player_to_service)
                            print("Connection Reset Error")
                            print("Player Socket Disconnect")
                        except BlockingIOError:
                            pass
                        except TimeoutError:
                            print("Server Send Timeout")
                        
            # Clears data to send
            self.server_to_send = bytes("", "utf-8")
            compute_time = time.time() - start_time
            if(compute_time < 0.0333):
                time.sleep(0.0333 - compute_time)
            



# --------------------------------------------------------------------------
# --------------END OF DEFINING START OF CODE EXECUTION---------------------
# --------------------------------------------------------------------------
# Creates list for players
player_list = [Player(None, 1000, host_name, 2, 0)]

# Creates class collision boxes
class_masks = [characterMask(-6, -10, 12, 33)] #33


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
    if USE_UPNP == True:
        upnp_thread = threading.Thread(target = upnp_port_mapping, args = ())
        upnp_thread.start()
        time.sleep(5)


    # Starts registration loop thread
    reg_thread = threading.Thread(target = registration, args = (True,))
    reg_thread.start()

    # Gets map entities and wallmask
    global loaded_map
    loaded_map = GG2Map(map_data_extractor.extract_map_data(map_file_path))

    time.sleep(0.1)
    # Start Game Server
    game_server = GameServer()
    server_networking_thread = threading.Thread(
        target = GameServer.run_game_server_networking,
        args = (game_server,)
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
    assert SERVER_PORT >= 0

    try:
        main()
    except Exception as e:
        print(f"EXCEPTION: {e}")
    finally:
        if USE_UPNP:
            upnp_exit()

        exit()
