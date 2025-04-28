import urllib.request
import miniupnpc
import socket
import struct
from io import BytesIO
import os.path
import configparser
import numpy as np
import math
import threading
import time
from constants import *
import map_data_extractor
from gm8_like_functions import *


# --------------------------------------------------------------------------
# --------------------------------Variables---------------------------------
# --------------------------------------------------------------------------
# Creates server configuration file if one doesn't exist
config = configparser.ConfigParser()
if not os.path.isfile("server_conf.ini"):
    config["Connection Settings"] = {"server_port": "8190", "use_upnp": "0", "use_lobby": "1"}
    config["Server Settings"] = {"server_name": "Python Server", "welcome_message": "", "host_name": "Host", "password": "", "max_players": "10"}
    config["Plugin Settings"] = {"server_plugins_required": "0", "server_plugin_list": ""}

    with open("server_conf.ini", "w") as configfile:
        config.write(configfile)

# Reads in server configuration values
config.read("server_conf.ini")
# Connection Settings
SERVER_PORT = int(config["Connection Settings"]["server_port"])
USE_UPNP = bool(int(config["Connection Settings"]["use_upnp"]))
REGISTER_SERVER = bool(int(config["Connection Settings"]["use_lobby"]))
# Server Settings
server_name = str(config["Server Settings"]["server_name"])
welcome_message = str(config["Server Settings"]["welcome_message"])
host_name = str(config["Server Settings"]["host_name"])
server_password = str(config["Server Settings"]["password"])
max_players = int(config["Server Settings"]["max_players"])
# Plugin Settings
server_plugins_required = bool(int(config["Plugin Settings"]["server_plugins_required"]))
server_plugins_list = str(config["Plugin Settings"]["server_plugin_list"])

# Map file
map_file_name = "ctf_eiger"

#Frame/Tick Variables
delta_factor = 1
skip_delta_factor = 1/2
ticks_per_virtual = 1
frameskip = 2
room_speed = 30

# --------------------------------------------------------------------------
# --------------------------------Functions---------------------------------
# --------------------------------------------------------------------------
# Updates lobby server of server existance
def server_registration():
    if REGISTER_SERVER:
        # Assembles Packet
        occupied_slots = struct.pack(">H", len(player_list) - 1)
        num_bots = struct.pack(">H", 0)
        if server_password == "":
            has_password = struct.pack(">H", 0)
        else:
            has_password = struct.pack(">H", 1)
        current_map_key_length = struct.pack(">B", 3)
        current_map_key = bytes("map", "utf-8")
        current_map_length = struct.pack(">H", len(map_file_name))
        current_map = bytes(map_file_name, "utf-8")
        packet = (REG_PACKET_ONE
            + occupied_slots
            + num_bots
            + has_password
            + REG_PACKET_TWO
            + current_map_key_length
            + current_map_key
            + current_map_length
            + current_map
            + REG_PACKET_THREE)

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(packet, (REG_LOBBY_DOMAIN, REG_LOBBY_PORT)) # WAY COOLER UDP WAY
            # sock.connect((REG_LOBBY_DOMAIN, REG_LOBBY_PORT)) # TCP WAY
            # sock.send(packet)
        print("---Registration Packet Sent---")


def upnp_port_mapping():
    # UPNP port forwarding
    upnp = miniupnpc.UPnP()
    # Gets devices
    upnp.discover()
    # Gets router I think
    upnp.selectigd()
    # Gets host's local ip
    HOST_IP = upnp.lanaddr
    while True:
        # Maps port
        upnp.addportmapping(
            SERVER_PORT,
            "TCP",
            HOST_IP,
            SERVER_PORT,
            "GGPDS Port",
            "",
            150
        )
        print("---UPNP Port Mapped---")
        time.sleep(135)


def upnp_exit():
    # UPNP port forwarding
    upnp = miniupnpc.UPnP()
    # Gets devices
    upnp.discover()
    # Gets router I think
    upnp.selectigd()

    # Deletes port mapping
    upnp.deleteportmapping(
        SERVER_PORT,
        "TCP"
    )
    print("UPNP Port Mapping Removed")


def hex_as_int(input_value):
    return int(hex(input_value), 16)

def num_to_bool(input_num):
    if input_num > 0.5:
        return True
    else:
        return False


# --------------------------------------------------------------------------
# ----------------------------------Classes---------------------------------
# --------------------------------------------------------------------------
class ObjectMask:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        
    def rotated_mask(self, direction):
        rot = math.radians(360 - direction)
        point1 = (self.x, self.y)
        point2 = (self.x + self.width, self.y)
        point3 = (self.x + self.width, self.y + self.height)
        point4 = (self.x, self.y + self.height)

        #point1 = (math.cos(rot)*(point1[0]-0.5)-math.sin(rot)*(point1[1]-0.5)+0.5, math.sin(rot)*(point1[0]-0.5)+math.cos(rot)*(point1[1]-0.5)+0.5)
        #point2 = (math.cos(rot)*(point2[0]-0.5)-math.sin(rot)*(point2[1]-0.5)+0.5, math.sin(rot)*(point2[0]-0.5)+math.cos(rot)*(point2[1]-0.5)+0.5)
        #point3 = (math.cos(rot)*(point3[0]-0.5)-math.sin(rot)*(point3[1]-0.5)+0.5, math.sin(rot)*(point3[0]-0.5)+math.cos(rot)*(point3[1]-0.5)+0.5)
        #point4 = (math.cos(rot)*(point4[0]-0.5)-math.sin(rot)*(point4[1]-0.5)+0.5, math.sin(rot)*(point4[0]-0.5)+math.cos(rot)*(point4[1]-0.5)+0.5)
        point1 = (math.cos(rot)*(point1[0]-0)-math.sin(rot)*(point1[1]-0)+0, math.sin(rot)*(point1[0]-0)+math.cos(rot)*(point1[1]-0)+0)
        point2 = (math.cos(rot)*(point2[0]-0)-math.sin(rot)*(point2[1]-0)+0, math.sin(rot)*(point2[0]-0)+math.cos(rot)*(point2[1]-0)+0)
        point3 = (math.cos(rot)*(point3[0]-0)-math.sin(rot)*(point3[1]-0)+0, math.sin(rot)*(point3[0]-0)+math.cos(rot)*(point3[1]-0)+0)
        point4 = (math.cos(rot)*(point4[0]-0)-math.sin(rot)*(point4[1]-0)+0, math.sin(rot)*(point4[0]-0)+math.cos(rot)*(point4[1]-0)+0)

        x = min(point1[0], point2[0], point3[0], point4[0])
        y = min(point1[1], point2[1], point3[1], point4[1])
        width = max(point1[0], point2[0], point3[0], point4[0]) - x
        height = max(point1[1], point2[1], point3[1], point4[1]) - y

        return x, y, width, height


class JoiningPlayer:
    def __init__(self, connection):
        self.conn = connection
        self.client_player = None
        self.new_state = STATE_EXPECT_HELLO
        self.state = self.new_state
        print(
            "Connections:"
            f"{len(joining_players) + len(player_list) - 1}\n"
        )
        
    def service_connection(self, gameserver_object):
        self.conn.settimeout(0)
        try:
            data = self.conn.recv(1)
        except ConnectionError:
            print("New Connection Socket Disconnect")
            return 1
        except BlockingIOError:
            return 0
        if not data:
            print("New Connection Socket Disconnect")
            return 1
        print("Received New Connection Data")
        print(data)

        to_send = BytesIO()

        if self.state == STATE_EXPECT_HELLO:
            if data[0] == HELLO:
                print("Received Hello")
                data = self.conn.recv(16)
                if data[0:16] != PROTOCOL_ID:
                    print("Incompatible Protocol Received")
                    to_send.write(struct.pack(">B", INCOMPATIBLE_PROTOCOL))
                    self.conn.sendall(to_send.getvalue())
                    return 1
                elif server_password == "":
                    print("Compatible Protocol Received")
                    self.state = STATE_CLIENT_AUTHENTICATED
                else:
                    print("Compatible Protocol Received")
                    to_send.write(struct.pack(">B", PASSWORD_REQUEST))
                    self.new_state = STATE_EXPECT_PASSWORD

        elif self.state == STATE_EXPECT_PASSWORD:
            password_length = data[0]
            data = self.conn.recv(password_length)
            if str(data[0:password_length].decode('utf-8')) == server_password:
                print("Received Correct Password")
                self.state = STATE_CLIENT_AUTHENTICATED
            else:
                print("Received Wrong Password")
                to_send.write(struct.pack(">B", PASSWORD_WRONG))
                self.conn.sendall(to_send.getvalue())
                return 1
        
        if self.state == STATE_CLIENT_AUTHENTICATED:
            print("Client Authenticated")
            # Assembles Response to authenticated client
            to_send.write(struct.pack(">B", HELLO))
            to_send.write(struct.pack(">B", len(server_name)))  # Server name length
            to_send.write(bytes(server_name, "utf-8"))  # Server name
            to_send.write(struct.pack(">B", len(map_file_name)))  # Map name length
            to_send.write(bytes(map_file_name, "utf-8"))  # Map name
            to_send.write(struct.pack(">B", 0))  # Map md5 length
            to_send.write(bytes("", "utf-8"))  # Map md5

            plugins_md5_list = ""
            if server_plugins_list:
                plugins_list = list(server_plugins_list.split(", "))
                for plugin_name in plugins_list:
                    if plugins_md5_list:
                        plugins_md5_list += ","
                    plugins_md5_list += plugin_name + "@" + (urllib.request.urlopen("http://www.ganggarrison.com/plugins/" + plugin_name + ".md5").read().decode('utf-8'))
            
            to_send.write(struct.pack(">B", int(server_plugins_required)))  # Server plugins required?
            to_send.write(struct.pack("<H", len(plugins_md5_list)))  # Plugin list length
            to_send.write(bytes(plugins_md5_list, "utf-8"))  # Plugin list
            self.new_state = STATE_EXPECT_COMMAND

        elif self.state == STATE_EXPECT_COMMAND:  
            if data[0] == PING:
                pass

            elif data[0] == RESERVE_SLOT:
                print("Received Reserve Slot")
                # Generates player ID for new player
                client_player_id = np.random.randint(1000, 10000)
                while client_player_id in player_list:
                    client_player_id = np.random.randint(1000, 10000)

                name_length = self.conn.recv(1)[0]
                data = self.conn.recv(name_length)
                # playerID, playerName, playerTeam, playerClass
                self.client_player = Player(
                    self.conn,
                    int(client_player_id),
                    str(data[0:name_length].decode('utf-8')),
                    TEAM_SPECTATOR,
                    CLASS_SCOUT,
                )
                # Making sure this is actually set
                self.client_player.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                # Assembles Response
                if (len(player_list) - 1) < max_players:
                    print("Slot Reserved")
                    to_send.write(struct.pack(">B", RESERVE_SLOT))
                else:
                    print("Server Full")
                    to_send.write(struct.pack(">B", SERVER_FULL))
                    self.conn.sendall(to_send.getvalue())
                    return 1

            elif data[0] == PLAYER_JOIN:
                print("Received Player Join")
                # Writes JOIN_UPDATE with num of players and map area
                to_send.write(struct.pack(">BBB", JOIN_UPDATE, len(player_list), 1))

                # Writes the current map n stuff
                to_send.write(struct.pack(">B", CHANGE_MAP))
                to_send.write(struct.pack(">B", len(map_file_name)))  # Map name length
                to_send.write(bytes(map_file_name, "utf-8"))  # Map name
                to_send.write(struct.pack(">B", 0))  # Map md5 length
                to_send.write(bytes("", "utf-8"))  # Map md5

                # Player joining n stuff
                for player_index, joining_player in enumerate(player_list):
                    to_send.write(struct.pack(">BB", PLAYER_JOIN, len(joining_player.name)))
                    to_send.write(bytes(joining_player.name, "utf-8"))
                    # Set player class then team
                    to_send.write(struct.pack(">BBBBBB",
                        PLAYER_CHANGECLASS,
                        player_index,
                        joining_player.class_,
                        PLAYER_CHANGETEAM,
                        player_index,
                        joining_player.team))
                # Writes FULL_UPDATE stuff
                to_send.write(gameserver_object.serialize_state(FULL_UPDATE))

                player_list.append(self.client_player)
                # Server Player Join
                gameserver_object.server_to_send.write(struct.pack(">BB", PLAYER_JOIN, len(self.client_player.name)))
                gameserver_object.server_to_send.write(bytes(self.client_player.name, "utf-8"))

                # Server Message
                if welcome_message:
                    to_send.write(struct.pack(">BB", MESSAGE_STRING, len(welcome_message)))
                    to_send.write(bytes(welcome_message, "utf-8"))
                print("Sent New Connection Data Back")
                self.conn.sendall(to_send.getvalue())
                print("Connection setup complete")
                server_registration()
                return 1
        print("Sent New Connection Data Back")
        self.conn.sendall(to_send.getvalue())
        self.state = self.new_state

    
class Player:
    def __init__(self, connection, id_, name, team, class_):
        self.id_ = id_
        
        self.character_object = None
        self.team = team
        self.class_ = class_
        self.connection = connection
        self.name = name
        self.kicked = False

        self.queue_jump = False
        
        # Stat tracking array
        self.stats = [0]*13

        # Statistic array for single life/arena
        self.round_stats = [0]*13

        self.times_changed_cap_limit = 0

        self.last_known_x = 0
        self.last_known_y = 0

        self.humiliated = 0

        self.deathmatch_respawn_bypass = 0

        # Sentries for Engies
        self.sentry = None

        # Domination Kill Table
        self.domination_kills = []
    
        self.corpse = None

        self.respawn_timer = 1

    def respawn(self):
        # Player Spawning
        if self.class_ == CLASS_SCOUT:
            self.character_object = Scout(self)
        elif self.class_ == CLASS_SOLDIER:
            self.character_object = Soldier(self)
        elif self.class_ == CLASS_SNIPER:
            self.character_object = Sniper(self)
        elif self.class_ == CLASS_DEMOMAN:
            self.character_object = Demoman(self)
        elif self.class_ == CLASS_MEDIC:
            self.character_object = Medic(self)
        elif self.class_ == CLASS_ENGINEER:
            self.character_object = Engineer(self)
        elif self.class_ == CLASS_HEAVY:
            self.character_object = Heavy(self)
        elif self.class_ == CLASS_SPY:
            self.character_object = Spy(self)
        elif self.class_ == CLASS_PYRO:
            self.character_object = Pyro(self)
        elif self.class_ == CLASS_QUOTE:
            self.character_object = Quote(self)

        game_server.server_to_send.write(struct.pack(">BB", PLAYER_SPAWN, player_list.index(self)))
        
        if self.team == TEAM_RED:
            random_spawn = np.random.randint(0, len(loaded_map.red_spawns))
            game_server.server_to_send.write(struct.pack(">B", random_spawn))
            # Spawning red player locally
            self.character_object.x = loaded_map.red_spawns[
                random_spawn
            ].x
            self.character_object.y = loaded_map.red_spawns[
                random_spawn
            ].y
        elif self.team == TEAM_BLUE:
            random_spawn = np.random.randint(0,len(loaded_map.blue_spawns))
            game_server.server_to_send.write(struct.pack(">B", random_spawn))
            # Spawning blue player locally
            self.character_object.x = loaded_map.blue_spawns[
                random_spawn
            ].x
            self.character_object.y = loaded_map.blue_spawns[
                random_spawn
            ].y
        game_server.server_to_send.write(struct.pack(">B", 0))
        print("Spawned Player")

    def leave_server(self):
        game_server.server_to_send.write(struct.pack(">BB", PLAYER_LEAVE, player_list.index(self)))
        player_list.remove(self)
        print("Player Socket Disconnect")


class Character:
    def __init__(self, player_object):
        self.player_object = player_object
        self.x = 0
        self.y = 0
        self.hspeed = 0
        self.vspeed = 0
        self.rotatable = False

        # Default character values
        self.can_double_jump = 0
        self.can_cloak = 0
        self.can_build = 0
        self.base_jump_strength = 8+(0.6/2)
        self.jump_strength = self.base_jump_strength
        self.cap_strength = 1

        # For frame independent jumping arcs
        self.applied_gravity = 0

        # Setting more values to default
        self.hp = self.max_hp
        self.flame_count = 0
        self.invisible = False
        self.intel = False
        self.taunting = False
        self.double_jump_used = 0
        self.ubered = 0
        self.stabbing = 0
        self.on_cabinet = 0
        self.want_to_jump = False
        self.time_unscathed = 0
        self.sync_wrongness = 0

        # Animation state
        self.equipment_offset = 0
        self.onground = True
        self.still = True
        self.y_offset = 0

        # Afterburn stuff
        self.burn_intensity = 0  # "heat"
        self.leg_intensity = 7  # afterburn intensity after which additional intsity additions are halved.
        self.max_intensity = 13  # maximum afterburn intensity in DPS
        self.burn_duration = 0  # "fuel"
        self.max_duration = 210  # maximum afterburn length in duration ticks (see durationDecay)
        self.decay_delay = 90  # time between last ignition and intensity lowering
        self.decay_duration = 90  # time between intensity lowering and zeroing out
        self.duration_decay = 1  # amount that duration lowers per step
        self.intensity_decay = self.burn_intensity / self.decay_duration
        self.burned_by = -1
        self.afterburn_source = -1
        self.num_flames = 5  # purely cosmetic - the number of flames that someone has with max burnIntensity
        self.real_num_flames = self.num_flames

        # Controls
        self.key_state = 0x0
        self.last_key_state = 0x0
        self.pressed_keys = 0x0
        self.released_keys = 0x0
        self.aim_direction = 0
        self.net_aim_direction = 0
        self.aim_distance = 0

        # Spinjumping state var
        if 90 <= self.aim_direction <= 270:
            self.image_xscale = -1
        else:
            self.image_xscale = 1
        self._last_xscale = self.image_xscale
        self.spin_jumping = False

        # Kill assist/finish off addition
        self.last_damage_dealer = None
        self.last_damage_source = -1
        self.second_to_last_damage_dealer = None

        self.afk = False

        # Cloak for Spies
        self.cloak = False
        self.cloak_alpha = 1
        self.cloak_flicker = False

        # Healer
        self.healer = -1

        # can_grab_intel- used for droppan intel
        self.can_grab_intel = True
        #alarm[1] = 0
        self.intel_recharge = 0
    
        # Control Point
        self.capping_point = None

        # Sandvich
        self.omnomnomnom = False
        self.can_eat = True
        self.eat_cooldown = 1350  # 45 sec cooldown

        # Sniper zoom
        self.zoomed = 0
    
        # nuts n bolts for contructor
        self.nuts_n_bolts = 100
        self.max_nuts_n_bolts = 100
    
        # jugglin'
        # 1 for rocket jump
        # 2 for rocket juggle
        # 3 for getting air blasted
        # 4 for friendly juggles!
        self.move_status = 0

        self.base_control = 0.85
        # Warning that baseFriction cannot be equal to 0 nor 1 or div0 will occur
        self.base_friction = 1.15
        self.control_factor = self.base_control
        self.friction_factor = self.base_friction
        self.run_power = self.base_run_power
        self.base_max_speed = gm8_round(abs(self.base_run_power * self.base_control / (self.base_friction-1)))
        self.highest_base_max_speed = 9.735  # Approximation error < 0.0017 of scout's base max speed

        # Create weapon
        if self.player_object.class_ == CLASS_SCOUT:
            self.current_weapon = Scattergun(self)
        elif self.player_object.class_ == CLASS_SOLDIER:
            # Temporary so choosing other classes doesn't crash
            self.current_weapon = Scattergun(self)
        elif self.player_object.class_ == CLASS_SNIPER:
            # Temporary so choosing other classes doesn't crash
            self.current_weapon = Scattergun(self)
        elif self.player_object.class_ == CLASS_DEMOMAN:
            # Temporary so choosing other classes doesn't crash
            self.current_weapon = Scattergun(self)
        elif self.player_object.class_ == CLASS_MEDIC:
            # Temporary so choosing other classes doesn't crash
            self.current_weapon = Scattergun(self)
        elif self.player_object.class_ == CLASS_ENGINEER:
            # Temporary so choosing other classes doesn't crash
            self.current_weapon = Scattergun(self)
        elif self.player_object.class_ == CLASS_HEAVY:
            # Temporary so choosing other classes doesn't crash
            self.current_weapon = Scattergun(self)
        elif self.player_object.class_ == CLASS_SPY:
            # Temporary so choosing other classes doesn't crash
            self.current_weapon = Scattergun(self)
        elif self.player_object.class_ == CLASS_PYRO:
            # Temporary so choosing other classes doesn't crash
            self.current_weapon = Scattergun(self)
        elif self.player_object.class_ == CLASS_QUOTE:
            # Temporary so choosing other classes doesn't crash
            self.current_weapon = Scattergun(self)

    def move_outside_solid(self, direction, max_dist):
        if direction == 0:
            self.x = gm8_round(self.x + max_dist)
        elif direction == 90:
            self.y = gm8_round(self.y - max_dist)
        elif direction == 180:
            self.x = gm8_round(self.x - max_dist)
        elif direction == 270:
            self.y = gm8_round(self.y + max_dist)

    def good_move_contact_solid(self, arg0, arg1):
        # Function from GG2
        if arg1 <= 0:
            return 0

        MAX_I = 8
        i = 8
        max_distance = arg1
        hvec = gm8_round(gm8_round(math.cos(gm8_round(degtorad(arg0)))) * max_distance)
        vvec = gm8_round(gm8_round(-math.sin(gm8_round(degtorad(arg0)))) * max_distance)
        sfac = max(abs(hvec), abs(vvec))
        total_moved = 0
        last_collision_happened = False

        while total_moved < max_distance and i > 0:
            move_x = gm8_round(gm8_round(gm8_round(hvec/sfac) * i/MAX_I) * min(1, max_distance - total_moved))
            move_y = gm8_round(gm8_round(gm8_round(vvec/sfac) * i/MAX_I) * min(1, max_distance - total_moved))

            new_x = gm8_round(self.x + gm8_round(move_x*i/MAX_I))
            new_y = gm8_round(self.y + gm8_round(move_y*i/MAX_I))
            if place_free(self, new_x, new_y, loaded_map.wm_collision_rects):
                total_moved = gm8_round(total_moved + math.dist([self.x, self.y], [new_x, new_y]))
                self.x = new_x
                self.y = new_y
                if i < MAX_I:
                    break
            else:
                last_collision_happened = True
                i -= 1

        return total_moved

    def character_hit_obstacle(self):
        self.hspeed = gm8_round(self.hspeed * delta_factor)
        self.vspeed = gm8_round(self.vspeed * delta_factor)
        
        old_x = self.x
        old_y = self.y
        old_hspeed = self.hspeed
        old_vspeed = self.vspeed
        bbox_height = self.collision_mask.height
        bbox_width = self.collision_mask.width

        if not place_free(self, self.x, self.y, loaded_map.wm_collision_rects):
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
            
            if not place_free(self, self.x, self.y, loaded_map.wm_collision_rects):
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
            
            self.good_move_contact_solid(point_direction(self.x, self.y, self.x + hleft, self.y + vleft), gm8_round(math.dist([self.x, self.y], [self.x + hleft, self.y + vleft])))

            hleft = gm8_round(hleft - (self.x - prev_x))
            vleft = gm8_round(vleft - (self.y - prev_y))

            if vleft != 0 and not place_free(self, self.x, self.y + sign(vleft), loaded_map.wm_collision_rects):
                if vleft > 0:
                    self.move_status = 0
                vleft = 0
                self.vspeed = 0
                collision_rectified = True

            if hleft != 0 and not place_free(self, self.x + sign(hleft), self.y, loaded_map.wm_collision_rects):
                if place_free(self, self.x + sign(hleft), self.y - 6, loaded_map.wm_collision_rects):
                    self.y = gm8_round(self.y - 6)
                    collision_rectified = True
                    self.move_status = 0
                elif place_free(self, self.x + sign(hleft), self.y + 6, loaded_map.wm_collision_rects) and abs(self.hspeed) >= abs(self.vspeed):
                    self.y = gm8_round(self.y + 6)
                    collision_rectified = True
                    self.move_status = 0
                else:
                    hleft = 0
                    self.hspeed = 0
                    collision_rectified = True
                    
            if not collision_rectified and (abs(hleft) >= 1 or abs(vleft) >= 1):
                self.vspeed = 0
                vleft = 0

        self.hspeed = gm8_round(self.hspeed / delta_factor)
        self.vspeed = gm8_round(self.vspeed / delta_factor)

    def begin_step(self):
        stuck_in_wall = not place_free(self, self.x, self.y, loaded_map.wm_collision_rects)
        obstacle_below = not place_free(self, self.x, self.y+1, loaded_map.wm_collision_rects)
        on_ground = False
        on_non_surfing_ground = False

        if self.vspeed >= 0:
            if obstacle_below:
                on_ground = True
                on_non_surfing_ground = True
            elif not num_to_bool(hex_as_int(self.key_state) & 0x02):
                # I ain't adding dropdowns soon
                pass

        if on_non_surfing_ground:
            self.move_status = 0
        if on_ground:
            self.double_jump_used = 0

        # Afterburn here

        # Input Handling
        if self.player_object.queue_jump:
            if num_to_bool(hex_as_int(self.pressed_keys) & 0x80):
                want_to_jump = True
            elif num_to_bool(hex_as_int(self.released_keys) & 0x80):
                want_to_jump = False

        if not self.taunting and not self.omnomnomnom:
            if not self.player_object.humiliated and num_to_bool((hex_as_int(self.key_state) | hex_as_int(self.pressed_keys)) & 0x10):
                self.current_weapon.fire_weapon()
            if not self.player_object.humiliated and self.pressed_keys & 0x01:
                # Taunting Stuff
                if self.invisible == False and self.cloak_alpha == 1:
                    self.taunting = True

            if ((num_to_bool(hex_as_int(self.pressed_keys) & 0x80)) or (False and want_to_jump)) and self.vspeed > -self.jump_strength:
                if on_ground and not stuck_in_wall:
                    if not self.stabbing:
                        # Jumping
                        want_to_jump = False
                        self.vspeed = -self.jump_strength
                        on_ground = False
                elif self.can_double_jump and not self.double_jump_used:
                    # Double Jumping
                    want_to_jump = False
                    self.vspeed = -self.jump_strength
                    on_ground = False
                    self.double_jump_used = 1
                    self.move_status = 0

        # Friction based on move status
        if self.move_status == 1:
            self.control_factor = 0.65
            self.friction_factor = 1
        elif self.move_status == 2:
            self.control_factor = 0.45
            self.friction_factor = 1.05
        elif self.move_status == 3:
            self.control_factor = 0.35
            self.friction_factor = 1.05
        elif self.move_status == 4:
            self.control_factor = self.base_control
            self.friction_factor = 1
        else:
            if self.player_object.humiliated:
                self.control_factor = self.base_control - 0.2
            elif self.intel:
                self.control_factor = self.base_control - 0.1
            else:
                self.control_factor = self.base_control
            self.friction_factor = self.base_friction

        rocket_jumping = (self.move_status == 1 or self.move_status == 2 or self.move_status == 4)

        # Horizonal Movement
        controlling = False
        for x in range(frameskip):
            if not self.taunting and not self.omnomnomnom:
                if num_to_bool((hex_as_int(self.key_state) | hex_as_int(self.pressed_keys)) & 0x40) and self.hspeed >= -self.base_max_speed:
                    self.hspeed = gm8_round(self.hspeed - (self.run_power * self.control_factor * skip_delta_factor))
                    controlling = True
                if num_to_bool((hex_as_int(self.key_state) | hex_as_int(self.pressed_keys)) & 0x20) and self.hspeed <= self.base_max_speed:
                    self.hspeed = gm8_round(self.hspeed + (self.run_power * self.control_factor * skip_delta_factor))
                    controlling = not controlling

            if abs(self.hspeed) > self.base_max_speed * 2 or (num_to_bool((hex_as_int(self.key_state) | hex_as_int(self.pressed_keys)) & 0x60) and abs(self.hspeed) < self.base_max_speed):
                self.hspeed = gm8_round(self.hspeed / (self.base_friction * skip_delta_factor + (1-1*skip_delta_factor)))
            else:
                self.hspeed = gm8_round(self.hspeed / (self.friction_factor * skip_delta_factor + (1-1*skip_delta_factor)))

        # Reseting key variables
        self.pressed_keys = 0
        self.released_keys = 0

        # Stops "ice skating"
        if abs(self.hspeed) < 0.195 and not controlling:
            self.hspeed = 0

        if not on_ground and not stuck_in_wall:
            if rocket_jumping:
                self.applied_gravity = gm8_round(self.applied_gravity + 0.54)
            else:
                self.applied_gravity = gm8_round(self.applied_gravity + 0.6)

    def normal_step(self):
        self.hspeed = min(abs(self.hspeed), 15) * sign(self.hspeed)
        self.vspeed = min(abs(self.vspeed), 15) * sign(self.vspeed)

        # Updating xscale
        if 90 <= self.aim_direction <= 270:
            self.image_xscale = -1
        else:
            self.image_xscale = 1

        # Spinjumping?
        if sign(self.hspeed) > 0:
            _test = self._last_xscale > self.image_xscale
        else:
            _test = self._last_xscale < self.image_xscale

        if _test and not place_free(self, self.x + sign(self.hspeed), self.y, loaded_map.wm_collision_rects):
            self.spin_jumping = True
        else:
            self.spin_jumping = False
            
        self._last_xscale = self.image_xscale

        # Gravity based on move status
        if self.move_status == 1 or self.move_status == 2 or self.move_status == 4:
            _gravity = 0.54
        else:
            _gravity = 0.6

        if self.spin_jumping and place_free(self, self.x, self.y - _gravity, loaded_map.wm_collision_rects) and (place_free(self, self.x, self.y +1, loaded_map.wm_collision_rects) or self.vspeed < 0):
            self.applied_gravity = gm8_round(self.applied_gravity - _gravity)
        else:
            self.spin_jumping = False

        # Gravity
        self.vspeed = gm8_round(self.vspeed + (self.applied_gravity*delta_factor/2))
        if self.vspeed > 10:
            self.vspeed = 10
            
        yprevious = self.y
        xprevious = self.x
        y_previous = self.y
        x_previous = self.x

        do_hit = not place_free(self, self.x + self.hspeed * delta_factor, self.y + self.vspeed * delta_factor, loaded_map.wm_collision_rects)
        if do_hit:
            # Theres been a collision with the map Wallmask
            self.character_hit_obstacle()
        else:
            self.x = gm8_round(self.x + (self.hspeed * delta_factor))
            self.y = gm8_round(self.y + (self.vspeed * delta_factor))

        # Fallback?
        if place_free(self, self.x, self.y + 1, loaded_map.wm_collision_rects):
            self.vspeed = gm8_round(self.vspeed + (self.applied_gravity*delta_factor/2))
        if self.vspeed > 10:
            self.vspeed = 10
        self.applied_gravity = 0

        # Dropdown platforms? Never heard of them

        self.x = gm8_round(self.x - self.hspeed)
        self.y = gm8_round(self.y - self.vspeed)

        # GM8 updates x & y with horizontal and vertical speeds on its own so this is needed
        self.x = gm8_round(self.x + self.hspeed)
        self.y = gm8_round(self.y + self.vspeed)

    def end_step(self):
        if self.vspeed == 0 and num_to_bool(hex_as_int(self.key_state) & 0x02) or True or False:
            if place_free(self, self.x, self.y + 6, loaded_map.wm_collision_rects):
                if not place_free(self, self.x, self.y + 7, loaded_map.wm_collision_rects):
                    self.y = gm8_round(self.y + 6)
                elif math.sqrt((self.hspeed ** 2) + (self.vspeed ** 2)) > 6:
                    if place_free(self, self.x, self.y + 12, loaded_map.wm_collision_rects):
                        if not place_free(self, self.x, self.y +13, loaded_map.wm_collision_rects):
                            self.y = gm8_round(self.y + 12)

        if self.hp <= 0:
            game_server.server_to_send.write(struct.pack("<BBBBB",
            10,
            player_list.index(self.player_object),
            player_list.index(self.player_object),
            255,
            25))
            self.player_object.respawn_timer = 5
            self.player_object.character_object = None
            print("Killed Player")
            


class Scout(Character):
    def __init__(self, player_object):
        self.collision_mask = ObjectMask(-5.5, -9.5, 12, 33) #-6, -10, 12, 33  Works: -5.5, -9.5, 12, 33
        self.base_run_power = 1.4
        self.max_hp = 100
        #self.weapons = ["Scattergun"]
        self.haxxy_statue = "ScoutHaxxyStatueS"  # Temp Value
        super().__init__(player_object)
        # Override defaults
        self.cap_strength = 2
        self.can_double_jump = 1
        self.num_flames = 3


class Soldier(Character):
    def __init__(self, player_object):
        self.collision_mask = ObjectMask(-5.5, -7.5, 12, 31) #-6, -8, 12, 31
        self.base_run_power = 0.9
        self.max_hp = 160
        #self.weapons = ["Rocketlauncher"]
        self.haxxy_statue = "SoldierHaxxyStatueS"  # Temp Value
        super().__init__(player_object)
        # Override defaults
        self.num_flames = 4


class Sniper(Character):
    def __init__(self, player_object):
        self.collision_mask = ObjectMask(-5.5, -7.5, 12, 31) #-6, -8, 12, 31
        self.base_run_power = 0.9
        self.max_hp = 120
        #self.weapons = ["Rifle"]
        self.haxxy_statue = "SniperHaxxyStatueS"  # Temp Value
        super().__init__(player_object)
        # Override defaults
        self.num_flames = 4


class Demoman(Character):
    def __init__(self, player_object):
        self.collision_mask = ObjectMask(-6.5, -9.5, 14, 33) #-7, -10, 14, 33
        self.base_run_power = 1
        self.max_hp = 120
        #self.weapons = ["Minegun"]
        self.haxxy_statue = "DemomanHaxxyStatueS"  # Temp Value
        super().__init__(player_object)
        # Override defaults
        self.num_flames = 3


class Medic(Character):
    def __init__(self, player_object):
        self.collision_mask = ObjectMask(-6.5, -7.5, 14, 31) #-7, -8, 14, 31
        self.base_run_power = 1.09
        self.max_hp = 120
        #self.weapons = ["Medigun"]
        self.haxxy_statue = "MedicHaxxyStatueS"  # Temp Value
        # Not Implemented Alarm value here <-
        super().__init__(player_object)
        # Override defaults
        self.num_flames = 4


class Engineer(Character):
    def __init__(self, player_object):
        self.collision_mask = ObjectMask(-5.5, -9.5, 12, 33) #-6, -10, 12, 33
        self.base_run_power = 1
        self.max_hp = 120
        #self.weapons = ["Shotgun"]
        self.haxxy_statue = "EngineerHaxxyStatueS"  # Temp Value
        super().__init__(player_object)
        # Override defaults
        self.num_flames = 3


class Heavy(Character):
    def __init__(self, player_object):
        self.collision_mask = ObjectMask(-8.5, -11.5, 18, 35) #-9, -12, 18, 35
        self.base_run_power = 0.8
        self.max_hp = 200
        #self.weapons = ["Minigun"]
        self.haxxy_statue = "HeavyHaxxyStatueS"  # Temp Value
        super().__init__(player_object)
        # Override defaults
        self.num_flames = 5


class Spy(Character):
    def __init__(self, player_object):
        self.collision_mask = ObjectMask(-5.5, -9.5, 12, 33) #-6, -10, 12, 33
        self.base_run_power = 1.08
        self.max_hp = 100
        #self.weapons = ["Revolver"]
        self.haxxy_statue = "SpyHaxxyStatueS"  # Temp Value
        super().__init__(player_object)
        # Override defaults
        self.can_cloak = 1
        self.num_flames = 4


class Pyro(Character):
    def __init__(self, player_object):
        self.collision_mask = ObjectMask(-6.5, -5.5, 14, 29) #-7, -6, 14, 29
        self.base_run_power = 1.1
        self.max_hp = 120
        #self.weapons = ["Flamethrower"]
        self.haxxy_statue = "PyroHaxxyStatueS"  # Temp Value
        super().__init__(player_object)
        # Override defaults
        self.num_flames = 3
        self.max_duration = 10


class Quote(Character):
    def __init__(self, player_object):
        self.collision_mask = ObjectMask(-6.5, -11.5, 14, 23) #-7, -12, 14, 23
        self.base_run_power = 1.07
        self.max_hp = 140
        #self.weapons = ["Blade"]
        self.haxxy_statue = ""  # Temp Value
        super().__init__(player_object)
        # Override defaults
        self.num_flames = 3


class Weapon:
    def __init__(self, character_object):
        self.ready_to_shoot = False
        self.just_shot = False

        self.owner = character_object
        self.owner_player = character_object.player_object

    def ready_shooting(self):
        self.ready_to_shoot = True


class Scattergun(Weapon):
    def __init__(self, character_object):
        self.refire_time = 20
        super().__init__(character_object)

        self.max_ammo = 6
        self.ammo_count = self.max_ammo
        self.reload_time = 15
        self.reload_buffer = 20
        
        self.recoil_time = self.refire_time

        self.ready_to_shoot_alarm = self.refire_time / delta_factor
        self.reload_alarm = 0

    def reload(self):
        if self.ammo_count < self.max_ammo:
            self.ammo_count += 1

        if self.ammo_count < self.max_ammo:
            self.reload_alarm = self.reload_time / delta_factor

    def fire_weapon(self):
        if self.ready_to_shoot and self.ammo_count > 0:
            np.seterr(over='ignore')
            lcg_rand = LcgRandom()
            seed = lcg_rand.irandom(65535)

            game_server.server_to_send.write(struct.pack("<BBHHbbH",
                WEAPON_FIRE,
                player_list.index(self.owner_player),
                round(self.owner.x*5),
                round(self.owner.y*5),
                round(self.owner.hspeed*8.5),
                round(self.owner.vspeed*8.5),
                seed))

            lcg_rand.set_seed(seed)
            self.ammo_count = max(0, self.ammo_count - 1)

            for i in range(6):
                bullet = Shot(self.owner, self.owner.x, self.owner.y, self.owner.aim_direction, 13)
                bullet.hspeed += self.owner.hspeed
                # Sets speed and direction based on hspeed and vspeed (Change later)
                bullet.speed = math.sqrt((bullet.hspeed ** 2) + (bullet.vspeed ** 2))
                bullet.direction = point_direction(bullet.x, bullet.y, bullet.x + bullet.hspeed, bullet.y + bullet.vspeed)
                
                bullet.speed += lcg_rand.random(4) - 2
                bullet.direction += lcg_rand.random(15) - 7.5
                # Sets hspeed and vspeed based on speed and direction (Change later)
                bullet.hspeed = bullet.speed * math.cos(math.radians(bullet.direction))
                bullet.vspeed = bullet.speed * -math.sin(math.radians(bullet.direction))
                
                # Move shot forward to avoid immediate collision with a wall behind the character
                bullet.x += 15 * math.cos(math.radians(bullet.direction))
                bullet.y += 15 * -math.sin(math.radians(bullet.direction))
                self.owner.current_weapon.ready_to_shoot_alarm = 35 * ((min(1, abs(math.cos(degtorad(self.owner.aim_direction))) * 13 / abs(math.cos(degtorad(self.owner.aim_direction)) * 13 + self.owner.hspeed)) - 1) / 2 + 1) / delta_factor


            self.ready_to_shoot = False
            self.ready_to_shoot_alarm = self.refire_time / delta_factor
            self.reload_alarm = (self.reload_buffer + self.reload_time) / delta_factor
            #print("Weapon Fired")

class Shot:
    def __init__(self, owner, x, y, direction, speed):
        self.collision_mask = ObjectMask(-16.5, -1.5, 17, 1) #-17, -2, 17, 1  Works: -16.5, -1.5, 17, 1
        self.rotatable = True
        self.x = x
        self.y = y
        self.direction = direction
        self.speed = speed
        self.hspeed = self.speed * math.cos(math.radians(self.direction))
        self.vspeed = self.speed * -math.sin(math.radians(self.direction))
        
        self.projectile = 7 #DAMAGE_SOURCE_SCATTERGUN
        self.first_step = True

        self.owner = owner
        self.owner_player = owner.player_object
        self.team = self.owner_player.team
        bullet_list.append(self)
        
    def normal_step(self):
        self.vspeed += 0.15 * delta_factor

        colliding = False
        if self.first_step:
            colliding += not place_free(self, self.x, self.y, loaded_map.wm_collision_rects)

        self.x += self.hspeed * delta_factor
        self.y += self.vspeed * delta_factor

        colliding += not place_free(self, self.x, self.y, loaded_map.wm_collision_rects)
        if colliding:
            # Destroy the bullet here
            bullet_list.remove(self)

        self.x -= self.hspeed
        self.y -= self.vspeed

        self.first_step = False
        
        # GM8 updates x & y with horizontal and vertical speeds on its own so this is needed
        self.x += self.hspeed
        self.y += self.vspeed
        
    def collision_step(self):
        for player in player_list:
            if player.id_ != 1000 and player != self.owner_player and player != self.team:
                if player.character_object is not None:
                    if colliding(self, player.character_object):
                        player.character_object.hp -= 8
                        player.character_object.hspeed = gm8_round(player.character_object.hspeed + (self.hspeed * 0.03))
                        player.character_object.vspeed = gm8_round(player.character_object.vspeed + (self.vspeed * 0.03))
                        bullet_list.remove(self)


class GG2Map:
    def __init__(self, gg2_map_data):
        # Wallmask rectangles for collision checking
        self.wm_collision_rects = gg2_map_data[1]

        # GG2 map's collision entities
        self.red_spawns = []
        self.blue_spawns = []
        self.setup_gates = []
        self.intels = [None, None]
        self.generators = [None, None]
        self.arena_control_point = None
        self.koth_control_point = None
        self.dkoth_control_points = [None, None]
        self.control_point_one = []
        self.control_point_two = []

        # Assign found entities
        for entity in gg2_map_data[0]:
            if entity.type == "redspawn":
                self.red_spawns.append(entity)
            elif entity.type == "bluespawn":
                self.blue_spawns.append(entity)

            elif entity.type == "SetupGate":
                self.setup_gates.append(entity)
                
            elif entity.type == "redintel":
                self.intels[0] = entity
            elif entity.type == "blueintel":
                self.intels[1] = entity

            elif entity.type == "GeneratorRed":
                self.generators[0] = entity
            elif entity.type == "GeneratorBlue":
                self.generators[1] = entity

            elif entity.type == "ArenaControlPoint":
                self.arena_control_point = entity

            elif entity.type == "KothControlPoint":
                self.koth_control_point = entity

            elif entity.type == "KothRedControlPoint":
                self.dkoth_control_points[0] = entity
            elif entity.type == "KothBlueControlPoint":
                self.dkoth_control_points[1] = entity

            elif entity.type == "controlPoint1":
                self.control_point_one.append(entity)
            elif entity.type == "controlPoint2":
                self.control_point_two.append(entity)

        # Figure out what HUD to use
        if self.intels != [None, None]:
            if self.setup_gates:
                self.hud_type = "InvasionHUD"
            else:
                self.hud_type = "CTFHUD"
        elif self.generators != [None, None]:
            self.hud_type = "GeneratorHUD"
        elif self.arena_control_point is not None:
            self.hud_type = "ArenaHUD"
        elif self.koth_control_point is not None:        
            self.hud_type = "KothHUD"
        elif self.dkoth_control_points != [None, None]:        
            self.hud_type = "DKothHUD"
        elif self.control_point_one or self.control_point_two:
            self.hud_type = "ControlPointHUD"
        else:
            self.hud_type = "TeamDeathmatchHUD"


class GameServer:
    def __init__(self):
        self.server_to_send = BytesIO()
        self.new_connections = []

    def serialize_state(self, update_type):
        to_send = BytesIO()
        to_send.write(struct.pack(">B", update_type))

        if update_type == FULL_UPDATE:
            # tdm invulnerability ticks
            to_send.write(struct.pack("<H", 30))

        to_send.write(struct.pack(">B", len(player_list)))

        # Adds each player's data for update
        if update_type != CAPS_UPDATE:
            for joining_player in player_list:
                if update_type == FULL_UPDATE:
                    to_send.write(struct.pack("<BBBBBBHBBBBBH",
                        joining_player.stats[0],  # Kills
                        joining_player.stats[1],  # Deaths
                        joining_player.stats[2],  # Caps
                        joining_player.stats[3],  # Assists
                        joining_player.stats[4],  # Destruction
                        joining_player.stats[5],  # Stabs
                        joining_player.stats[6],  # Healing
                        joining_player.stats[7],  # Defenses
                        joining_player.stats[8],  # Invulns
                        joining_player.stats[9],  # Bonus
                        joining_player.stats[12],  # Points
                        0,  # Queue Jump (Temp Value)
                        0))  # Rewards length (Temp Value)
                    to_send.write(bytes("", "utf-8"))  # Rewards String (Temp Value) 
                    
                    # Dominations (Temp value)
                    for victim in player_list:
                        if joining_player != victim:
                            to_send.write(struct.pack(">B", 0))

                # Subojects (Character, Weapon, Sentry)
                if joining_player.character_object is not None:
                    # Subobject count
                    to_send.write(struct.pack(">B", 1))

                    # Input & Aiming
                    to_send.write(struct.pack("<BHB",
                        clip_and_round(joining_player.character_object.key_state, 0, 255),
                        clip_and_round(joining_player.character_object.net_aim_direction, 0, 65535),
                        clip_and_round(joining_player.character_object.aim_distance/2, 0, 255)))
                    
                    if update_type == QUICK_UPDATE or update_type == FULL_UPDATE:
                        to_send.write(struct.pack("<HHbbBBB",
                            clip_and_round(joining_player.character_object.x*5, 0, 65535),
                            clip_and_round(joining_player.character_object.y*5, 0, 65535),
                            clip_and_round(joining_player.character_object.hspeed*8.5, -128, 127),
                            clip_and_round(joining_player.character_object.vspeed*8.5, -128, 127),
                            clip_and_round(math.ceil(joining_player.character_object.hp), 0, 255),
                            clip_and_round(joining_player.character_object.current_weapon.ammo_count, 0, 255),
                            clip_and_round(((joining_player.character_object.move_status & 0x7) << 1), 0, 255)))
                        
                    if update_type == FULL_UPDATE:
                        # Temp Misc and Intel values
                        to_send.write(struct.pack(">B", 0))
                        to_send.write(struct.pack(">B", 0))
                        
                        to_send.write(struct.pack("<h", 0))
                        to_send.write(struct.pack(">B", joining_player.character_object.intel))
                        to_send.write(struct.pack("<h", joining_player.character_object.intel_recharge))

                        # Temp Weapon Values
                        to_send.write(struct.pack("<BB",
                            clip_and_round(joining_player.character_object.current_weapon.ready_to_shoot, 0, 255),
                            clip_and_round(joining_player.character_object.current_weapon.ready_to_shoot_alarm, 0, 255)))
                        
                else:
                    # Subobject count
                    to_send.write(struct.pack(">B", 0))

        if update_type == FULL_UPDATE:
            if loaded_map.intels[0] is not None:
                # Red Intel
                to_send.write(struct.pack("<HHHh", 1,
                    loaded_map.intels[0].x*5,
                    loaded_map.intels[0].y*5,
                    -1))
            else:
                to_send.write(struct.pack("<H", 0))
            if loaded_map.intels[1] is not None:
                # Blue Intel
                to_send.write(struct.pack("<HHHh", 1,
                    loaded_map.intels[1].x*5,
                    loaded_map.intels[1].y*5,
                    -1))
            else:
                to_send.write(struct.pack("<H", 0))
            # Cap limit, red caps, blue caps, server respawn time
            to_send.write(struct.pack("<BBBB", 3, 0, 0, 5))
            # HUD Networking
            if loaded_map.hud_type == "InvasionHUD":
                # Invasion HUD
                to_send.write(struct.pack("<BIH", 15, 25000, 120))
            elif loaded_map.hud_type == "CTFHUD":
                # CTF HUD
                to_send.write(struct.pack("<BI", 15, 25000))
            elif loaded_map.hud_type == "GeneratorHUD":
                # Generator HUD
                to_send.write(struct.pack("<BI", 15, 25000))
                # Blue Gen
                to_send.write(struct.pack("<HH", 2100, 300))
                # Red Gen
                to_send.write(struct.pack("<HH", 2100, 300))
            elif loaded_map.hud_type == "ArenaHUD":
                # Arena HUD
                if update_type == FULL_UPDATE:
                    to_send.write(struct.pack("<BBBbH", 0, 0, 0, 2, 0))
                to_send.write(struct.pack("<BIHB", 15, 25000, 1800, 0))

                to_send.write(struct.pack("<bbH", -1, -1, 0))
            elif loaded_map.hud_type == "KothHUD":
                # Koth HUD
                to_send.write(struct.pack("<HHH", 900, 5400, 5400))

                to_send.write(struct.pack("<bbH", -1, -1, 0))
            elif loaded_map.hud_type == "DKothHUD":
                # Dkoth HUD
                to_send.write(struct.pack("<HHH", 900, 5400, 5400))

                to_send.write(struct.pack("<bbH", -1, -1, 0))

                to_send.write(struct.pack("<bbH", -1, -1, 0))
            elif loaded_map.hud_type == "ControlPointHUD":
                # Control Point HUD
                # Not doing this in this style
                pass
            elif loaded_map.hud_type == "TeamDeathmatchHUD":
                # Team Death Match HUD
                to_send.write(struct.pack("<BIH", 15, 25000, 1))

            # Classlimits
            for x in range(10):
                to_send.write(struct.pack(">B", 255))

        return to_send.getvalue()

    def process_client_commands(self, player_to_service):
        conn = player_to_service.connection
        conn.settimeout(0)
        commands_done = 0
        
        while 10 > commands_done:
            data = None
            try:
                data = conn.recv(1)
            except ConnectionError:
                if player_to_service not in players_to_remove:
                    players_to_remove.append(player_to_service)
                #print("Connection Error")
                commands_done = 10
                break
            except BlockingIOError:
                commands_done = 10
                break
            except TimeoutError:
                print("Timeout???")
                commands_done = 10
                break

            if not data:
                commands_done = 10
                break
            
            # print("Received Player Data")
            # print(data[0])
            # print(data)

            # Reactions to client data
            if data[0] == PLAYER_LEAVE:
                print("Player Left???")
                if player_to_service not in players_to_remove:
                    players_to_remove.append(player_to_service)

            elif data[0] == PLAYER_CHANGETEAM:
                print("Received Change Team")
                # Player Death
                data = conn.recv(1)
                player_to_service.respawn_timer = 1
                print("Current team: " + str(player_to_service.team) + " New Team: " + str(data[0]))
                if player_to_service.team != data[0] and player_to_service.character_object is not None:
                    self.server_to_send.write(struct.pack("<BBBBB",
                        10,
                        player_list.index(player_to_service),
                        player_list.index(player_to_service),
                        255,
                        25))
                    print("Killed Player")

                    player_to_service.respawn_timer = 5
                    player_to_service.character_object = None
                    
                # Player Set Team
                player_to_service.team = data[0]
                self.server_to_send.write(struct.pack("<BBB",
                    PLAYER_CHANGETEAM,
                    player_list.index(player_to_service),
                    player_to_service.team))

            elif data[0] == PLAYER_CHANGECLASS:
                print("Received Change Class")
                player_to_service.respawn_timer = 5
                player_to_service.character_object = None
                # Player Set Class
                data = conn.recv(1)
                player_to_service.class_ = data[0]
                self.server_to_send.write(struct.pack("<BBB",
                    PLAYER_CHANGECLASS,
                    player_list.index(player_to_service),
                    player_to_service.class_))

            elif data[0] == INPUTSTATE:
                data = conn.recv(4)
                if player_to_service.character_object is not None:
                    player_to_service.character_object.key_state = data[0]
                    player_to_service.character_object.net_aim_direction = struct.unpack("<H", data[1:3])[0]
                    player_to_service.character_object.aim_direction = player_to_service.character_object.net_aim_direction*360/65536
                    player_to_service.character_object.aim_distance = data[3]

                    player_to_service.character_object.pressed_keys |= player_to_service.character_object.key_state & ~player_to_service.character_object.last_key_state
                    player_to_service.character_object.released_keys |= ~player_to_service.character_object.key_state & player_to_service.character_object.last_key_state
                    player_to_service.character_object.last_key_state = player_to_service.character_object.key_state

            elif data[0] == CHAT_BUBBLE:
                bubble_image = conn.recv(1)[0]
                self.server_to_send.write(struct.pack("<BBB",
                    CHAT_BUBBLE,
                    player_list.index(player_to_service),
                    bubble_image))

            elif data[0] == OMNOMNOMNOM:
                if player_to_service.character_object is not None:
                    if (not player_to_service.humiliated
                    and not player_to_service.character_object.taunting
                    and not player_to_service.character_object.omnomnomnom
                    and player_to_service.character_object.can_eat
                    and player_to_service.class_ == CLASS_HEAVY):
                        self.server_to_send.write(struct.pack("<BB",
                            OMNOMNOMNOM,
                            player_list.index(player_to_service)))
                        # Thing needs to happen here

            elif data[0] == TOGGLE_ZOOM:
                if player_to_service.character_object is not None:
                    if player_to_service.class_ == CLASS_SNIPER:
                        self.server_to_send.write(struct.pack("<BB",
                            TOGGLE_ZOOM,
                            player_list.index(player_to_service)))
                        # Thing needs to happen here

            elif data[0] == PLAYER_CHANGENAME:
                name_length = conn.recv(1)[0]
                name = str(conn.recv(name_length).decode('utf-8'))
                self.server_to_send.write(struct.pack("<BBB",
                    PLAYER_CHANGENAME,
                    player_list.index(player_to_service),
                    name_length))
                self.server_to_send.write(bytes(name, "utf-8"))
                
            else:
                print("Not yet added thing")
                print(struct.unpack(">B", data))
                print(struct.unpack(">b", data))
                print(data)
            
            commands_done += 1

    def process_client_alarms(self):
        for player_to_service in player_list:
            if player_to_service.id_ != 1000:
                # Respawn Alarm
                if player_to_service.respawn_timer >= 0:
                    player_to_service.respawn_timer -= 1
                if (player_to_service.respawn_timer == 0
                        and player_to_service.character_object is None
                        and (player_to_service.team == TEAM_RED
                             or player_to_service.team == TEAM_BLUE)
                        and (0 <= player_to_service.class_ <= 9)):
                    player_to_service.respawn()

                if player_to_service.character_object is not None:
                    if player_to_service.character_object.current_weapon.reload_alarm >= 0:
                        player_to_service.character_object.current_weapon.reload_alarm -= 1
                    if player_to_service.character_object.current_weapon.reload_alarm == 0:
                        player_to_service.character_object.current_weapon.reload()

                    if player_to_service.character_object.current_weapon.ready_to_shoot_alarm >= 0:
                        player_to_service.character_object.current_weapon.ready_to_shoot_alarm -= 1
                    if player_to_service.character_object.current_weapon.ready_to_shoot_alarm == 0:
                        player_to_service.character_object.current_weapon.ready_shooting()


    def run_game_server_networking(self):
        self.server_to_send = BytesIO()
        start_time = time.time()
        frame = 0
        while True:
            # Registers server with GG2 lobby server
            if (frame % 900) == 0:
                server_registration()
            
            frame += 1

            # Removes players from server
            if players_to_remove:
                for player in players_to_remove:
                    if player in player_list:
                        player.leave_server()
                    players_to_remove.remove(player)
                server_registration()

            if len(player_list) > 1:
                # Processes player/client commands
                for player_to_service in player_list:
                    if player_to_service.id_ != 1000:
                        self.process_client_commands(player_to_service)

                # Send players server update
                test_time = time.time()
                if (frame % 7) == 0:
                    self.server_to_send.write(self.serialize_state(QUICK_UPDATE))
                else:
                    self.server_to_send.write(self.serialize_state(INPUTSTATE))
                    
                # Begin step collisions
                for player_to_service in player_list:
                    if player_to_service.id_ != 1000:
                        if player_to_service.character_object is not None:
                            player_to_service.character_object.begin_step()
                    
                # Alarm Updating
                self.process_client_alarms()

                # Position/physics object updating here
                for player_to_service in player_list:
                    if player_to_service.id_ != 1000:
                        if player_to_service.character_object is not None:
                            player_to_service.character_object.normal_step()

                for bullet in bullet_list:
                    bullet.normal_step()

                for player_to_service in player_list:
                    if player_to_service.id_ != 1000:
                        if player_to_service.character_object is not None:
                            player_to_service.character_object.end_step()

                for bullet in bullet_list:
                    bullet.collision_step()

            # Make sure server updates 30 or 60 times a second
            time.sleep(max(0, (1/room_speed) - (time.time() - start_time) - 0.008)) #0.001 has overruns while 0.01 has high cpu usage
            #if (1/room_speed) - (time.time() - start_time) < 0:
            #    print("Server Sleep Overrun")
            while 0 <= (1/room_speed) - (time.time() - start_time): #was 0.001. 0 <= performs a lot smoother
                pass
            #if (1/room_speed) - (time.time() - start_time) < 0:
            #    print("Server Update Time Overrun")
                
            start_time = time.time()

            # Sends update to all players
            if self.server_to_send:
                for player_to_service in player_list:
                    if player_to_service.id_ != 1000:
                        try:
                            conn = player_to_service.connection
                            conn.sendall(self.server_to_send.getvalue())
                        except ConnectionError:
                            if player_to_service not in players_to_remove:
                                players_to_remove.append(player_to_service)
                            print("Connection Error")
                        except BlockingIOError:
                            print("Blocking IO Error")
                        except TimeoutError:
                            print("Server Send Timeout???")
                        
            # Clears data to send
            self.server_to_send = BytesIO()

            # Joins one new player each loop
            for joining_player in joining_players:
                if joining_player.service_connection(self):
                    # Player either joined succesfully or failed to connect
                    joining_players.remove(joining_player)



# --------------------------------------------------------------------------
# --------------END OF DEFINING START OF CODE EXECUTION---------------------
# --------------------------------------------------------------------------
# Creates list for players
player_list = [Player(None, 1000, host_name, TEAM_SPECTATOR, CLASS_SCOUT)]
joining_players = []
players_to_remove = []

# Creates list for bullets
bullet_list = []


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
    np.random.randint(256),
    np.random.randint(256),
    np.random.randint(256),
    np.random.randint(256),
    np.random.randint(256),
    np.random.randint(256),
    np.random.randint(256),
    np.random.randint(256),
    np.random.randint(256),
    np.random.randint(256),
    np.random.randint(256),
    np.random.randint(256),
    np.random.randint(256),
    np.random.randint(256),
    np.random.randint(256),
    np.random.randint(256),
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
REG_PACKET_ONE += struct.pack(">B", 0)            # Connection Type (UDP or TCP)
REG_PACKET_ONE += struct.pack(">H", SERVER_PORT)  # Hosting Port
REG_PACKET_ONE += struct.pack(">H", max_players)  # Player Limit

# Registration Packet 2
REG_PACKET_TWO = struct.pack(">H", 7) # Amount of Value Groups
# Server Name
# Server Name Key Length
REG_PACKET_TWO += struct.pack(">B", 4)
# Server Name Key
REG_PACKET_TWO += bytes("name", "utf-8")
# Server Name Length
REG_PACKET_TWO += struct.pack(">H", len(server_name))
# Server Name
REG_PACKET_TWO += bytes(server_name, "utf-8")

# Game Name
# Game Name Key Length
REG_PACKET_TWO += struct.pack(">B", 4)
# Game Name Key
REG_PACKET_TWO += bytes("game", "utf-8")
# Game Name Length
REG_PACKET_TWO += struct.pack(">H", 17)
# Game Name
REG_PACKET_TWO += bytes("GG2 Python Server", "utf-8")

# Game Short
# Game Short Key Length
REG_PACKET_TWO += struct.pack(">B", 10)
# Game Short Key
REG_PACKET_TWO += bytes("game_short", "utf-8")
# Game Short Length
REG_PACKET_TWO += struct.pack(">H", 5)
# Game Short
REG_PACKET_TWO += bytes("GGPDS", "utf-8")

# Game Version
# Game Version Key Length
REG_PACKET_TWO += struct.pack(">B", 8)
# Game Version Key
REG_PACKET_TWO += bytes("game_ver", "utf-8")
# Game Version Length
REG_PACKET_TWO += struct.pack(">H", 0)
# Game Version
REG_PACKET_TWO += bytes("", "utf-8")

# Game URL
# Game URL Key Length
REG_PACKET_TWO += struct.pack(">B", 8)
# Game URL Key
REG_PACKET_TWO += bytes("game_url", "utf-8")
# Game URL Length
REG_PACKET_TWO += struct.pack(">H", 63)
# Game URL
REG_PACKET_TWO += bytes("https://github.com/Minecraftboss318/gg2-python-dedicated-server", "utf-8")

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
    if USE_UPNP:
        upnp_thread = threading.Thread(target = upnp_port_mapping, args = ())
        upnp_thread.start()
        time.sleep(2)

    # Gets map entities and wallmask
    global loaded_map
    loaded_map = GG2Map(map_data_extractor.extract_map_data(map_file_name + ".png"))
    

    # Start Game Server
    global game_server
    game_server = GameServer()
    server_networking_thread = threading.Thread(
        target = GameServer.run_game_server_networking,
        args = (game_server,)
    )
    server_networking_thread.start()

    time.sleep(0.05)
    # Listens for connections and starts a thread to handle them
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.bind(("", SERVER_PORT))
        s.settimeout(0)
        s.listen()
        print(f"Listening on port {SERVER_PORT}")
        while True:
            try:
                conn, addr = s.accept()
                print("Accepted connection from", addr)
                joining_client = JoiningPlayer(conn)
                joining_players.append(joining_client)
            except BlockingIOError:
                time.sleep(0.3)


if __name__ == "__main__":
    assert SERVER_PORT >= 0

    try:
        main()
    except Exception as e:
        print(f"EXCEPTION: {e}")
    finally:
        print("")
        if USE_UPNP:
            upnp_exit()

        print("Server Stopped")
        exit()
