#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import struct
import sys
import base64
import pathlib
from string import Template

PRESET_DIR = pathlib.PosixPath("~/Library/Audio/Presets/Apple/AUNBandEQ").expanduser()

AUPRESET_TEMPLATE = Template(
    '\
<?xml version="1.0" encoding="UTF-8"?>\n\
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n\
<plist version="1.0">\n\
<dict>\n\
	<key>ParametricType</key>\n\
	<integer>11</integer>\n\
	<key>data</key>\n\
	<data>\n\
$data\n\
	</data>\n\
	<key>manufacturer</key>\n\
	<integer>1634758764</integer>\n\
	<key>name</key>\n\
	<string>$name</string>\n\
	<key>numberOfBands</key>\n\
	<integer>$number_of_bands</integer>\n\
	<key>subtype</key>\n\
	<integer>1851942257</integer>\n\
	<key>type</key>\n\
	<integer>1635083896</integer>\n\
	<key>version</key>\n\
	<integer>0</integer>\n\
</dict>\n\
</plist>\n\
'
)

# type of IIR
IIR = list[dict[str, int | float]]


def rew2iir(filename: str) -> tuple[int, IIR]:
    # has_width = False
    iir = []
    with open(filename, "r", encoding="ASCII") as fd:
        lines = fd.readlines()
        for line in lines:
            # if line.find("AU_N-Band_EQ"):
            #    has_width = True
            tokens = line.split()
            if len(tokens) != 8 or tokens[0] == "Number" or tokens[3] == "None":
                continue
            iir.append(
                {
                    "type": tokens[3],
                    "freq": float(tokens[4]),
                    "gain": float(tokens[5]),
                    "width": float(tokens[6]),
                }
            )

    return 0, iir


def iir2data(iir: IIR) -> str:
    """Build the data field from an iir"""

    def type2value(t: str) -> float:
        """Transform a IIR type into the corresponding value for AUNBandEQ"""
        return {
            "PK": 0.0,
            "LS": 8.0,
            "HS": 9.0,
            "BP": 6.0,
        }.get(t, -1.0)

    len_iir = len(iir)
    # print(len_iir)
    # print(iir)

    params = {}
    for i, current_iir in enumerate(iir):
        params["{}".format(1000 + i)] = 0.0  # True
        params["{}".format(2000 + i)] = type2value(current_iir["type"])
        params["{}".format(3000 + i)] = float(current_iir["freq"])
        params["{}".format(4000 + i)] = float(current_iir["gain"])
        params["{}".format(5000 + i)] = float(current_iir["width"])

    # remainings EQ are required and are set to 0
    for i in range(len_iir, 16):
        params["{}".format(1000 + i)] = 1.0  # False
        params["{}".format(2000 + i)] = 0.0
        params["{}".format(3000 + i)] = 0.0
        params["{}".format(4000 + i)] = 0.0
        params["{}".format(5000 + i)] = 0.0

    # some black magic, data is padded, the only important values are
    # 3. number of parameters + 1
    # 5. db_gain
    buffer = struct.pack(">llllf", 0, 0, 81, 0, 0.0)

    # add pairs of (param_id, value) in big endian
    for param_id, value in params.items():
        buffer += struct.pack(">lf", int(param_id), value)

    # convert the byte buffer to base64
    text = base64.standard_b64encode(buffer).decode("ascii")

    # add \t and slice in chunks of 67 chars
    len_text = len(text) // 67
    slices = ["\t{}\n".format(text[i * 67 : (i + 1) * 67]) for i in range(len_text)]
    slices += ["\t{}".format(text[len_text * 67 :])]

    return 0, "".join(slices)


def iir2aupreset(iir: list, name: str) -> tuple[int | str]:
    status, data = iir2data(iir)
    if status != 0:
        return status, None
    return 0, AUPRESET_TEMPLATE.substitute(data=data, name=name, number_of_bands=16)


def usage():
    print("Usage:")
    print("{} -i eq.txt".format(sys.argv[0]))
    print("It will copy output to stdout\n")
    print("{} -i eq.txt -o eq.aupreset".format(sys.argv[0]))
    print("It will  copy output to eq.aupreset\n")
    print("{} -i eq.txt -install".format(sys.argv[0]))
    print("It will copy output to ~/Library/Audio/Presets/Apple/AUNBandEQ/eq.aupreset")


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

    status, iir = rew2iir(rew_filename)
    if status != 0 or len(iir) == 0:
        return 1

    status, aupreset = iir2aupreset(iir, "test")

    if status != 0:
        return status

    if len(sys.argv) == 3:
        print(aupreset)
        return 0

    output = "{}.aupreset".format(rew_base)
    if len(sys.argv) == 4:
        PRESET_DIR.mkdir(mode=0o755, parents=True, exist_ok=True)
        output = "{}/{}.aupreset".format(PRESET_DIR, pathlib.Path(rew_base).name)

    print(output)

    try:
        with open(output, "w", encoding="ascii") as fd:
            fd.write(aupreset)
    except FileNotFoundError:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
