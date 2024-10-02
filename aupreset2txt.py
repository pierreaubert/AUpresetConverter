#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import struct
import sys
from base64 import b64decode
import defusedxml.ElementTree as ElementTree


def iir_type_2_string(iir_type: float) -> str:
    return {
        0: "PK",
        1: "BLP",
        2: "BHP",
        3: "RLP",
        4: "RHP",
        5: "BP",
        6: "BS",
        7: "LS",
        8: "HS",
        9: "RLS",
        10: "RHS",
    }.get(int(iir_type), "??")


def active_2_string(param: int) -> str:
    if param == 0:
        return "ON"
    elif param == 1:
        return "KO"
    print("error param == {}".format(param))
    return "??"


def main():
    if len(sys.argv) != 2:
        sys.exit(-1)
    rew_filename = sys.argv[1]

    tree = ElementTree.parse(rew_filename)
    root = tree.getroot()
    data = root.findall("./dict/data")
    ascii = data[0].text
    if not ascii:
        print("{} is empty".format(data))
        return 1
    lines = "".join([a.strip() for a in ascii])
    bigendian = b64decode(lines)
    # debugging begining of buffer
    print("---------------------------- debug")
    for i in range(0, 5):
        debug_i = struct.unpack(">l", bigendian[i * 4 : i * 4 + 4])
        debug_f = struct.unpack(">f", bigendian[i * 4 : i * 4 + 4])
        print("{:1d} {} {}".format(i, debug_i[0], debug_f[0]))
    # print eqs
    for i in range(5, 5 + 16 * 5 * 2, 2):
        debug_i = struct.unpack(">l", bigendian[i * 4 : i * 4 + 4])
        debug_f = struct.unpack(">f", bigendian[i * 4 + 4 : i * 4 + 8])
        print("{:1d} {} {}".format(i, debug_i[0], debug_f[0]))
    print("---------------------------- debug")

    i = 2
    count = struct.unpack(">l", bigendian[i * 4 : i * 4 + 4])[0] - 1
    i = 4
    db_gain = struct.unpack(">f", bigendian[i * 4 : i * 4 + 4])[0]

    print("#params {} db_gain={}".format(count, db_gain))

    preset = {}
    for i in range(0, count):
        offset = 20 + i * 8
        param_id = struct.unpack(">l", bigendian[offset : offset + 4])
        value_d = struct.unpack(">l", bigendian[offset + 4 : offset + 8])
        value_f = struct.unpack(">f", bigendian[offset + 4 : offset + 8])
        # print("param_id {} value {}".format(param_id, value_f))
        if param_id[0] // 2 == 2:
            preset["{}".format(param_id[0])] = value_d[0]
        else:
            preset["{}".format(param_id[0])] = value_f[0]

    for i in range(0, 16):
        active = preset["{}".format(1000 + i)]
        iir_type = preset["{}".format(2000 + i)]
        freq = preset["{}".format(3000 + i)]
        gain = preset["{}".format(4000 + i)]
        width = preset["{}".format(5000 + i)]
        print(
            "Filter {:2d}: {:2s} {:9s} Fc {:8.2f} Hz  Gain {:6.2f} dB  BW oct {:1.2f}".format(
                i + 1,
                active_2_string(active),
                iir_type_2_string(iir_type),
                freq,
                gain,
                width,
            )
        )
    return 0


if __name__ == "__main__":
    STATUS = main()
    sys.exit(STATUS)
