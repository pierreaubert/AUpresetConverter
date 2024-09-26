#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pathlib
import sys

from .app.converter import rew2iir, iir2aupreset, PRESET_DIR


def usage():
    print("Usage:")
    print("{} -i eq.txt".format(sys.argv[0]))
    print("It will copy output to stdout\n")
    print("{} -i eq.txt -o eq.aupreset".format(sys.argv[0]))
    print("It will  copy output to eq.aupreset\n")
    print("{} -i eq.txt -install".format(sys.argv[0]))
    print(
        "It will copy output to ~/Library/Audio/Presets/Apple/AUNBandEQ/eq.aupreset"
    )


def main():
    if (
        (len(sys.argv) < 3 or len(sys.argv) > 5)
        or sys.argv[1] != "-i"
        or (len(sys.argv) > 3 and sys.argv[3] not in ("-o", "-install"))
    ):
        usage()
        sys.exit(-1)
    rew_filename = sys.argv[2]
    rew_base = rew_filename
    dotpos = rew_filename.rfind(".")
    if dotpos != -1:
        rew_base = rew_filename[:dotpos]
    preset_name = pathlib.Path(rew_base).name

    status, iir = rew2iir(rew_filename)
    if status != 0 or len(iir) == 0:
        return 1

    status, aupreset = iir2aupreset(iir, preset_name)

    if status != 0:
        return status

    if len(sys.argv) == 3:
        print(aupreset)
        return 0

    output = "{}.aupreset".format(rew_base)
    if len(sys.argv) == 4:
        PRESET_DIR.mkdir(mode=0o755, parents=True, exist_ok=True)
        output = "{}/{}.aupreset".format(PRESET_DIR, preset_name)

    print(output)

    try:
        with open(output, "w", encoding="ascii") as fd:
            fd.write(aupreset)
    except FileNotFoundError:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
