#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import struct
import sys
from base64 import b64decode
import xml.etree.ElementTree as ET

def iir_type_2_string(iir_type: float) -> str:
    iir = int(iir_type)
    if iir == 0:
        return "PK"
    elif iir == 1:
        return "BLP"
    elif iir == 2:
        return "BHP"
    elif iir == 3:
        return "RLP"
    elif iir == 4:
        return "RHP"
    elif iir == 5:
        return "BP"
    elif iir == 6:
        return "BS"
    elif iir == 7:
        return "LS"
    elif iir == 8:
        return "HS"
    elif iir == 9:
        return "RLS"
    elif iir == 10:
        return "RHS"
    return "??"

def active_2_string(active: float) -> str:
    param = int(active)
    if param == 0.0:
        return "ON"
    elif param == 1.0
        return "KO"
    return "??"

def main():
    if len(sys.argv) != 2:
        sys.exit(-1)
    rew_filename = sys.argv[1]
    tree = ET.parse(rew_filename)
    root = tree.getroot()
    data = root.findall("./dict/data")
    ascii = data[0].text
    lines = ''.join([a.strip() for a in ascii])
    bigendian = b64decode(lines)
    # debugging begining of buffer
    # for i in range(0, 5):
    #    debug = struct.unpack('>L', bigendian[i*4:i*4+4])
    #    # print("{:1d} {}".format(i, debug))
    # 
    count = 80
    preset = {}
    for i in range(0, count):
        offset = 20+i*8
        param_id = struct.unpack('>L', bigendian[offset:offset+4])
        value = struct.unpack('>f', bigendian[offset+4:offset+8])
        preset["{}".format(param_id[0])] = value[0]
        # print('param_id {} value {}'.format(param_id, value))

    iir = {}
    for i in range(0, 15):
        iir_type = preset["{}".format(1000+i)]
        active = preset["{}".format(2000+i)]
        freq = preset["{}".format(3000+i)]
        gain = preset["{}".format(4000+i)]
        width = preset["{}".format(5000+i)]
        print("{:2s} {:2s} {:5.0f}Hz {:+2.2f}dB {:1.2f}".format(
            active_2_string(active), iir_type_2_string(iir_type), freq, gain, width))
    return 0

if __name__ == "__main__":
    STATUS = main()
    sys.exit(STATUS)
