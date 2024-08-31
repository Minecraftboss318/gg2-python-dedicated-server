# Lobby Registration Server Domain and port
REG_LOBBY_DOMAIN = "ganggarrison.com"
REG_LOBBY_PORT = 29944

# Team Constants
TEAM_RED = 0
TEAM_BLUE = 1
TEAM_SPECTATOR = 2
TEAM_ANY = 3

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
CHANGE_MAP = 7

INPUTSTATE = 6
FULL_UPDATE = 8
QUICK_UPDATE = 9
CAPS_UPDATE = 28
JOIN_UPDATE = 44

PLAYER_DEATH = 10
SERVER_FULL = 11
RED_TEAM_CAP = 12
BLUE_TEAM_CAP = 13
MAP_END = 14
CHAT_BUBBLE = 15
BUILD_SENTRY = 16
DESTROY_SENTRY = 17
BALANCE = 18

GRAB_INTEL = 19
SCORE_INTEL = 20
DROP_INTEL = 21

UBER_CHARGED = 22
UBER = 23

OMNOMNOMNOM = 24
PASSWORD_REQUEST = 25
PASSWORD_WRONG = 27
CP_CAPTURED = 30
PLAYER_CHANGENAME = 31
GENERATOR_DESTROY = 32

ARENA_WAIT_FOR_PLAYERS = 33
ARENA_ENDROUND = 34
ARENA_RESTART = 35
UNLOCKCP = 36

SERVER_KICK = 37
KICK = 38
KICK_NAME = 39
ARENA_STARTROUND = 40
TOGGLE_ZOOM = 41
RETURN_INTEL = 42
INCOMPATIBLE_PROTOCOL = 43
DOWNLOAD_MAP = 45
SENTRY_POSITION = 46

REWARD_UPDATE = 47
REWARD_REQUEST = 50
REWARD_CHALLENGE_CODE = 51
REWARD_CHALLENGE_RESPONSE = 52

MESSAGE_STRING = 53
WEAPON_FIRE = 54
PLUGIN_PACKET = 55
KICK_BAD_PLUGIN_PACKET = 56
PING = 57
CLIENT_SETTINGS = 58
KICK_MULTI_CLIENT = 59
RESERVE_SLOT = 60

# MISC Constants
MAX_PLAYERNAME_LENGTH = 20
STATE_UPDATE = 8
ASSIST_TIME = 120
NOTICE_NUTSNBOLTS = 0
NOTICE_TOOCLOSE = 1
NOTICE_AUTOGUNSCRAPPED = 2
NOTICE_HAVEINTEL = 4
NOTICE_SETCHECKPOINT = 5
NOTICE_DESTROYCHECKPOINT = 6
NOTICE_CUSTOM = 9
INTEL_MAX_TIMER = 900