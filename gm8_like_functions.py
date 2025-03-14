import numpy as np
import ctypes
import math
np.seterr(over='ignore')


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
    return math.degrees(math.atan2(-(y2-y1), x2-x1)) % 360

# converts degrees to radians
def degtorad(degrees):
    return degrees * math.pi / 180


# returns whether an object at the provided position is
# colliding with the provided rectangles
def place_free(obj, xPos, yPos, collision_rects):
    collisions = []
    rect2_x = xPos + obj.collision_mask.x1
    rect2_y = yPos + obj.collision_mask.y1
    rect2_width = obj.collision_mask.width
    rect2_height = obj.collision_mask.height

    for rect1 in collision_rects:
        if (rect1.x <= rect2_x + rect2_width and
                rect1.x + rect1.width >= rect2_x and
                rect1.y <= rect2_y + rect2_height and
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
        self.seed = np.int32(num)

    def cycle(self):
        self.seed = np.int32(np.int32(self.seed) * self.MULTIPLIER + self.INCREMENT)

    def random(self, upper_range):
        self.cycle()
        int_step_float = ctypes.c_double.from_address(ctypes.addressof(self.INT_STEP)).value
        random_float = np.float64(np.float64(np.uint32(self.seed)) * np.float64(int_step_float) * upper_range)
        # Round to hundredths place
        return math.floor(random_float * 100 + 0.5) / 100

    def irandom(self, upper_range):
        self.cycle()
        ls = np.uint64(self.seed) & 0xFFFF_FFFF
        lb = np.uint64(np.uint32(upper_range) + 1)
        return np.int32(np.uint64(ls * lb) >> 32)
