import subprocess
import struct
import hjson
import zlib
import time
from PIL import Image
from typing import BinaryIO, List, Tuple


class rectangle:
    def __init__(self, xPos, yPos):
        self.x = xPos * 6
        self.y = yPos * 6
        self.width = 6
        self.height = 6


# ---------------------------------
# Code to create collision entities
# ---------------------------------
def generate_wall_mask_array(width, height, wm):
    wm_rect = []
    for i in range(height):
        current_rect = None
        for j in range(width):
            #print((i*width) + j)
            if int(wm[(i*width) + j]) == 1:
                if current_rect is not None:
                    current_rect.width += 6
                else:
                    current_rect = rectangle(j, i)
            else:
                if current_rect is not None:
                    wm_rect.append(current_rect)
                    current_rect = None
        if current_rect is not None:
            wm_rect.append(current_rect)

    return wm_rect


# ------------------------
# Code to extract entities
# ------------------------
class LegacyEntity:
    def __init__(self, _type, x, xscale, y, yscale):
        self.type = _type
        self.x = x
        self.xscale = xscale
        self.y = y
        self.yscale = yscale


class Entity:
    def __init__(self, _dict):
        self.xscale = 1
        self.yscale = 1
        self.__dict__.update(_dict)


def get_image_entities(map_image_data):
    entity_objects = []

    entities_start = map_image_data.find("{ENTITIES}")
    entities_end = map_image_data.find("{END ENTITIES}") - 1

    if map_image_data[entities_start + 11] == "[":
        print("New Entity Format")
        image_entities = map_image_data[entities_start + 11:entities_end]
        image_entities = image_entities.replace(",", "\n")
        image_entities = image_entities.replace("}", "\n}")
        image_entities = hjson.loads(image_entities)

        for entity in image_entities:
            print(entity)
            entity_objects.append(Entity(entity))
    else:
        print("Old Entity Format")
        image_entities = map_image_data[entities_start:entities_end]

        entity_list = image_entities.split(".")
        entity_list = entity_list[1:len(entity_list)]

        for entity_part_index in range(0, len(entity_list), 3):
            entity = entity_list[entity_part_index:entity_part_index + 3]
            print(*entity[0:2], 1, entity[2], 1)
            entity_objects.append(LegacyEntity(*entity[0:2], 1, entity[2], 1))

    return entity_objects


# ------------------------
# Code to extract wallmask
# ------------------------
def get_image_wallmask(map_image_data, map_name):
    wall_mask_start = map_image_data.find("{WALKMASK}") + 11
    wall_mask_end = map_image_data.find(".{END WALKMASK}")
    image_wm_data = map_image_data[wall_mask_start:wall_mask_end]

    wm_width = ""
    while True:
        if image_wm_data[0] == ".":
            image_wm_data = image_wm_data[1:len(image_wm_data)]
            break

        wm_width += str(image_wm_data[0])
        image_wm_data = image_wm_data[1:len(image_wm_data)]

    wm_height = ""
    while True:
        if image_wm_data[0] == ".":
            image_wm_data = image_wm_data[1:len(image_wm_data)]
            break

        wm_height += str(image_wm_data[0])
        image_wm_data = image_wm_data[1:len(image_wm_data)]

    image_wm_data = image_wm_data.replace("\\\\", "a")
    image_wm_data = image_wm_data.replace("\\\'", "b")
    image_wm_data = [*image_wm_data]
    image_bin_data = []

    for character in image_wm_data:
        if character == "a":
            character = 92 - 32
        elif character == "b":
            character = 39 - 32
        else:
            character = ord(character) - 32

        character = "{0:06b}".format(character)
        image_bin_data += [*character]

    width = int(wm_width)
    height = int(wm_height)

    # Creates list of collision boxs from binary list
    wm_collision_rects = generate_wall_mask_array(width, height, image_bin_data)
    #for b in wm_collision_rects:
        #print(b.x + b.width)
    return wm_collision_rects


# Only ever call this to extract embeded image data
def extract_map_data(map_name):
    map_image = Image.open(map_name)
    map_image.load()
    map_image_data = str(map_image.info)

    map_image_data = map_image_data.replace("\\n", ".")
    entities_start = map_image_data.find("{ENTITIES}")
    entities_end = map_image_data.find(".{END WALKMASK}") + 15
    map_image_data = map_image_data[entities_start:entities_end]

    return [
        get_image_entities(map_image_data),
        get_image_wallmask(map_image_data, map_name),
    ]


#extract_map_data("ctf_eiger.png")
