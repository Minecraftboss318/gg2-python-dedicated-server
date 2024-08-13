import subprocess
import struct
import hjson
import zlib
from typing import BinaryIO, List, Tuple

Pixel = Tuple[int, int, int]
Image = List[List[Pixel]]
BLACK_PIXEL: Pixel = (0, 0, 0)
WHITE_PIXEL: Pixel = (255, 255, 255)
HEADER = b'\x89PNG\r\n\x1A\n'


#------------------------
#Code to create png image
#------------------------
def generate_wm(width: int, height: int, wm) -> Image:
    out = []
    for i in range(height):
        row = []
        for j in range(width):
            #print((i*width) + j)
            if int(wm[(i*width) + j]) == 0:
                row.append(WHITE_PIXEL)
            else:
                row.append(BLACK_PIXEL)
        out.append(row)
    return out

def get_checksum(chunk_type: bytes, data: bytes) -> int:
    checksum = zlib.crc32(chunk_type)
    checksum = zlib.crc32(data, checksum)
    return checksum

def chunk(out: BinaryIO, chunk_type: bytes, data: bytes) -> None:
    out.write(struct.pack('>I', len(data)))
    out.write(chunk_type)
    out.write(data)

    checksum = get_checksum(chunk_type, data)
    out.write(struct.pack('>I', checksum))

def make_ihdr(width: int, height: int, bit_depth: int, color_type: int) -> bytes:
    return struct.pack('>2I5B', width, height, bit_depth, color_type, 0, 0, 0)

def encode_data(img: Image) -> List[int]:
    ret = []

    for row in img:
        ret.append(0)

        color_values = [
            color_value
            for pixel in row
            for color_value in pixel
        ]
        ret.extend(color_values)

    return ret

def compress_data(data: List[int]) -> bytes:
    data_bytes = bytearray(data)
    return zlib.compress(data_bytes)

def make_idat(img: Image) -> bytes:
    encoded_data = encode_data(img)
    compressed_data = compress_data(encoded_data)
    return compressed_data

def dump_png(out: BinaryIO, img: Image) -> None:
    out.write(HEADER)  # start by writing the header

    assert len(img) > 0  # assume we were not given empty image data
    width = len(img[0])
    height = len(img)
    bit_depth = 8  # bits per pixel
    color_type = 2  # pixel is RGB triple

    ihdr_data = make_ihdr(width, height, bit_depth, color_type)
    chunk(out, b'IHDR', ihdr_data)

    compressed_data = make_idat(img)
    chunk(out, b'IDAT', data=compressed_data)

    chunk(out, b'IEND', data=b'')

def save_png(img: Image, filename: str) -> None:
    with open(filename, 'wb') as out:
        dump_png(out, img)

        
#------------------------
#Code to extract entities
#------------------------
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

    if(map_image_data[map_image_data.find("{ENTITIES}") + 11] == "["):
        print("New Entity Format")
        image_entities = map_image_data[map_image_data.find("{ENTITIES}")+11:map_image_data.find("{END ENTITIES}")-1]
        image_entities = image_entities.replace(",", "\n")
        image_entities = image_entities.replace("}", "\n}")
        image_entities = hjson.loads(image_entities)

        for entity in image_entities:
            print(entity)
            entity_objects.append(Entity(entity))
                
    else:
        print("Old Entity Format")
        image_entities = map_image_data[map_image_data.find("{ENTITIES}"):map_image_data.find("{END ENTITIES}")-1]

        entity_list = image_entities.split(".")
        entity_list = entity_list[1:len(entity_list)]

        for entity_part_index in range(0, len(entity_list), 3):
            entity = entity_list[entity_part_index:entity_part_index+3]
            print(*entity[0:2], 1, entity[2], 1)
            entity_objects.append(LegacyEntity(*entity[0:2], 1, entity[2], 1))

    return(entity_objects)


#------------------------
#Code to extract wallmask
#------------------------
def get_image_wallmask(map_image_data, map_name):
    image_wm_data = map_image_data[map_image_data.find("{WALKMASK}")+11:map_image_data.find(".{END WALKMASK}")]

    wm_width = ""
    while True:
        if(image_wm_data[0] == "."):
            image_wm_data = image_wm_data[1:len(image_wm_data)]
            break
            
        wm_width += str(image_wm_data[0])
        image_wm_data = image_wm_data[1:len(image_wm_data)]

    wm_height = ""
    while True:
        if(image_wm_data[0] == "."):
            image_wm_data = image_wm_data[1:len(image_wm_data)]
            break
            
        wm_height += str(image_wm_data[0])
        image_wm_data = image_wm_data[1:len(image_wm_data)]

    image_wm_data = image_wm_data.replace("\\\\", "a")
    image_wm_data = image_wm_data.replace("\\\'", "b")
    image_wm_data = [*image_wm_data]
    image_bin_data = []

    for character in image_wm_data:
        if(character == "a"):
            character = 92 - 32
        elif(character == "b"):
            character = 39 - 32
        else:
            character = ord(character) - 32
            
        character = '{0:06b}'.format(character)
        image_bin_data += [*character]
        
    width = int(wm_width)
    height = int(wm_height)
    img = generate_wm(width, height, image_bin_data)
    save_png(img, 'wm_' + map_name)
    return(img)


#Only ever call this to extract embeded image data
def extract_map_data(map_name):
    map_image_data = str(subprocess.run(["exiftool.exe", "", map_name], capture_output=True, text=True))
    map_image_data = map_image_data = map_image_data[map_image_data.find("{ENTITIES}"):map_image_data.find(".{END WALKMASK}")+15]

    return([get_image_entities(map_image_data), get_image_wallmask(map_image_data, map_name)])


#print(extract_map_data("ctf_eiger.png")[0])
