from PIL import Image
import json


class Rectangle:
    def __init__(self, x, y):
        self.x = x * 6
        self.y = y * 6
        self.width = 6
        self.height = 6


# ---------------------------------
# Code to create collision entities
# ---------------------------------
def generate_wall_mask_array(width, height, wm):
    wm_rects = []
    for i in range(height):
        current_rect = None
        for j in range(width):
            #print((i*width) + j)
            if int(wm[(i*width) + j]) == 1:
                if current_rect is not None:
                    current_rect.width += 6
                else:
                    current_rect = Rectangle(j, i)
            else:
                if current_rect is not None:
                    wm_rects.append(current_rect)
                    current_rect = None
        if current_rect is not None:
            wm_rects.append(current_rect)

    # Merges rectangles vertically if they have the same X, one is below the other, and they are the same width
    rect_index = 0
    while rect_index < len(wm_rects):
        for other_rect in wm_rects:
            if wm_rects[rect_index] is not other_rect and wm_rects[rect_index].x == other_rect.x and (wm_rects[rect_index].y + wm_rects[rect_index].height) == other_rect.y and wm_rects[rect_index].width == other_rect.width:
                wm_rects[rect_index].height += other_rect.height
                wm_rects.remove(other_rect)
                rect_index -= 1
                break
        rect_index += 1

    print("Map Rectangle Count: " + str(len(wm_rects)))
    return wm_rects


# ------------------------
# Code to extract entities
# ------------------------
class LegacyEntity:
    def __init__(self, _type, x, xscale, y, yscale):
        self.type = _type
        self.x = int(x)
        self.xscale = int(xscale)
        self.y = int(y)
        self.yscale = int(yscale)


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
        # Formats the entities so they can be loaded with the json module
        image_entities = image_entities.replace("{", '{"')
        image_entities = image_entities.replace(":", '":')
        image_entities = image_entities.replace(",", ',"')
        image_entities = image_entities.replace('"{', '{')
        image_entities = image_entities.replace("}", "}\n")
        
        pos = 0
        while image_entities.find(":", pos) != -1:
            pos = image_entities.find(":", pos) + 1
            found_char = image_entities[pos]

            # If the first char isn't a number 1-9 or a negative sign then its assumed to be a string
            # If its determined to be a string then the value is wrapped in double quotes
            if (found_char.isnumeric() == False or found_char == "0") and found_char != "-":
                image_entities = image_entities[:pos] + '"' + image_entities[pos:]
                
                comma_pos = image_entities.find(",", pos)
                bracket_pos = image_entities.find("}", pos)
                if comma_pos != -1 and comma_pos < bracket_pos:
                    image_entities = image_entities[:comma_pos] + '"' + image_entities[comma_pos:]
                else:
                    image_entities = image_entities[:bracket_pos] + '"' + image_entities[bracket_pos:]

        image_entities = json.loads(image_entities)

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
def get_image_wallmask(map_image_data):
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
        get_image_wallmask(map_image_data),
    ]


#extract_map_data("ctf_eiger.png")
