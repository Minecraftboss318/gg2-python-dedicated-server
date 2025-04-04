import numpy as np
import ctypes
import math
np.seterr(over='ignore')


# GM8's internal rounding
def gm8_round(input_num):
    return math.floor(input_num * 1000000000 + 0.5) / 1000000000


# returns wether number is positive, negative, or neither
def sign(input_num):
    if input_num < 0:
        return -1
    elif 0 < input_num:
        return 1
    else:
        return 0


# returns line's angle in degrees
def point_direction(x1, y1, x2, y2):
    return gm8_round(math.degrees(math.atan2(-(y2-y1), x2-x1)) % 360)

# converts degrees to radians
def degtorad(degrees):
    return gm8_round(math.radians(degrees))


# returns whether an object at the provided position is
# colliding with the provided rectangles
def place_free(obj, x, y, collision_rects):
    collisions = []
    direction = 0
    if obj.rotatable:
        direction = point_direction(obj.x, obj.y, obj.x + obj.hspeed, obj.y + obj.vspeed)
    rect2_x, rect2_y, rect2_w, rect2_h = obj.collision_mask.rotated_mask(direction)
    rect2_x += x
    rect2_y += y

    for rect1 in collision_rects:
        if (rect1.x <= rect2_x + rect2_w and
                rect1.x + rect1.width >= rect2_x and
                rect1.y <= rect2_y + rect2_h and
                rect1.y + rect1.height >= rect2_y):
            collisions.append(rect1)
    if collisions:
        return False
    else:
        return True


# partial implementation of gm8's random functions
class LcgRandom: 
    def __init__(self):
        self.seed = np.random.randint(-2147483648, 2147483647)
        self.INCREMENT = np.int32(1)
        self.MULTIPLIER = np.int32(0x0808_8405)
        self.INT_STEP = ctypes.c_int64(0x3DF0_0000_0000_0000)
        # self.INT_STEP = 2.328306436538696289062500E-10

    def randomize(self):
        self.seed = np.random.randint(-2147483648, 2147483647)

    def set_seed(self, num):
        np.seterr(over='ignore')
        self.seed = np.int32(num)

    def cycle(self):
        np.seterr(over='ignore')
        self.seed = np.int32(np.int32(self.seed) * self.MULTIPLIER + self.INCREMENT)

    def random(self, upper_range):
        np.seterr(over='ignore')
        self.cycle()
        int_step_float = ctypes.c_double.from_address(ctypes.addressof(self.INT_STEP)).value
        random_float = np.float64(np.float64(np.uint32(self.seed)) * np.float64(int_step_float) * upper_range)
        # Round to hundredths place
        return math.floor(random_float * 100 + 0.5) / 100

    def irandom(self, upper_range):
        np.seterr(over='ignore')
        self.cycle()
        ls = np.uint64(self.seed) & 0xFFFF_FFFF
        lb = np.uint64(np.uint32(upper_range) + 1)
        return np.int32(np.uint64(ls * lb) >> 32)
