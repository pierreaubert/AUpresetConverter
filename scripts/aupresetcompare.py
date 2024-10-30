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
    if len(sys.argv) != 3:
        sys.exit(-1)

    filename1 = sys.argv[1]
    filename2 = sys.argv[2]

    tree2 = ElementTree.parse(filename2)
    root2 = tree2.getroot()
    data2 = root2.findall("./dict/data")
    ascii2 = data2[0].text
    if not ascii2:
        print("{} is empty".format(data2))
        return 1
    lines2 = "".join([a.strip() for a in ascii2])
    bigendian2 = b64decode(lines2)

    tree1 = ElementTree.parse(filename1)
    root1 = tree1.getroot()
    data1 = root1.findall("./dict/data")
    ascii1 = data1[0].text
    if not ascii1:
        print("{} is empty".format(data1))
        return 1
    lines1 = "".join([a.strip() for a in ascii1])
    bigendian1 = b64decode(lines1)

    print("lens #1={} #2={}".format(len(lines1), len(lines2)))
    print("--")
    print(lines1)
    print("--")
    print(lines2)
    print("--")
    if len(lines1) != len(lines2):
        print("error: lens are diff!")

    for i, (b1, b2) in enumerate(zip(bigendian1, bigendian2)):
        if b1 != b2:
            print("{} != {} {}".format(i, b1, b2))

    # debugging begining of buffer
    print("---------------------------- debug")
    for i in range(0, 5):
        debug_i1 = struct.unpack(">l", bigendian1[i * 4 : i * 4 + 4])
        debug_f1 = struct.unpack(">f", bigendian1[i * 4 : i * 4 + 4])
        debug_i2 = struct.unpack(">l", bigendian2[i * 4 : i * 4 + 4])
        debug_f2 = struct.unpack(">f", bigendian2[i * 4 : i * 4 + 4])
        delta = "  "
        if debug_i1 != debug_i2 or debug_f1 != debug_f2:
            delta = "!="
        print(
            "{} {:3d} {:10d} {:10.5f} {:10d} {:10.5f}".format(
                delta, i, debug_i1[0], debug_f1[0], debug_i2[0], debug_f2[0]
            )
        )
    # print eqs
    for i in range(5, 5 + 16 * 5 * 2, 2):
        debug_i1 = struct.unpack(">l", bigendian1[i * 4 : i * 4 + 4])
        debug_f1 = struct.unpack(">f", bigendian1[i * 4 + 4 : i * 4 + 8])
        debug_i2 = struct.unpack(">l", bigendian2[i * 4 : i * 4 + 4])
        debug_f2 = struct.unpack(">f", bigendian2[i * 4 + 4 : i * 4 + 8])
        delta = "  "
        if debug_i1 != debug_i2 or debug_f1 != debug_f2:
            delta = "!="
        print(
            "{} {:3d} {:10d} {:10.5f} {:10d} {:10.5f}".format(
                delta, i, debug_i1[0], debug_f1[0], debug_i2[0], debug_f2[0]
            )
        )
    print("---------------------------- debug")

    i = 2
    count1 = struct.unpack(">l", bigendian1[i * 4 : i * 4 + 4])[0] - 1
    count2 = struct.unpack(">l", bigendian2[i * 4 : i * 4 + 4])[0] - 1
    i = 4
    db_gain1 = struct.unpack(">f", bigendian1[i * 4 : i * 4 + 4])[0]
    db_gain2 = struct.unpack(">f", bigendian2[i * 4 : i * 4 + 4])[0]

    print("1) #params {} db_gain={}".format(count1, db_gain1))
    print("2) #params {} db_gain={}".format(count2, db_gain2))

    return 0


if __name__ == "__main__":
    STATUS = main()
    sys.exit(STATUS)
