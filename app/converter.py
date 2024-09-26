#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import pathlib
from string import Template
import struct
from typing import Literal

from iir.filter_iir import Biquad, q2bw, bw2q
from iir.filter_peq import peq_preamp_gain, Peq

SRATE = 48000

PRESET_DIR = pathlib.PosixPath(
    "~/Library/Audio/Presets/Apple/AUNBandEQ"
).expanduser()

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

# types
IIR = list[dict[str, int | float]]
STATUS = Literal[0] | Literal[1]


def guess_format(lines: list[str]) -> str:
    has_q = False
    has_width = False
    has_filter = False
    for line in lines:
        if line.find("AU_N-Band_EQ") != -1:
            has_width = True
        if line.find("Filter ") != -1:
            has_filter = True
        if line.find(" Q ") != -1:
            has_q = True

    if has_width:
        # generated by REW for AUNBandEQ
        return "AUNBandEQ"

    if has_filter and has_q:
        # more or less EQ APO format / used by autoEQ too
        return "APO"

    return "Unknown"


def parse_aunbandeq(lines: list[str]) -> tuple[STATUS, IIR]:
    iir = []
    for line in lines:
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


def parse_apo(lines: list[str]) -> tuple[STATUS, IIR]:
    iir = []
    for line in lines:
        tokens = line.split()
        len_tokens = len(tokens)
        # if len_tokens == 3 and tokens[0] == "Preamp" and tokens[2] == "dB":
        #    preamp_gain = float(tokens[1])
        #    continue
        if len_tokens == 12 and tokens[0] == "Filter" and tokens[2] == "ON":
            iir.append(
                {
                    "type": tokens[3],
                    "freq": float(tokens[5]),
                    "gain": float(tokens[8]),
                    "q": float(tokens[11]),
                    "width": q2bw(float(tokens[11])),
                }
            )
            continue
    return 0, iir


def iir2peq(iir: IIR) -> Peq:
    peq = []
    for biquad in iir:
        biquad_type = {
            "PK": Biquad.PEAK,
            "LP": Biquad.LOWPASS,
            "HP": Biquad.HIGHPASS,
            "LS": Biquad.LOWSHELF,
            "HS": Biquad.HIGHSHELF,
            "BP": Biquad.BANDPASS,
        }.get(str(biquad["type"]))
        if biquad_type is None:
            continue
        freq = biquad["freq"]
        gain = biquad["gain"]
        width = biquad["width"]
        q = bw2q(width)
        peq.append((1.0, Biquad(biquad_type, freq, SRATE, q, gain)))
    return peq


def lines2iir(lines: list[str]) -> tuple[STATUS, IIR]:
    option = guess_format(lines)
    if option == "AUNBandEQ":
        return parse_aunbandeq(lines)
    elif option == "APO":
        return parse_apo(lines)
    return 1, []


def rew2iir(filename: str) -> tuple[STATUS, IIR]:
    with open(filename, "r", encoding="utf-8") as fd:
        lines = fd.readlines()
        return lines2iir(lines)
    return 1, []


def iir2data(iir: IIR) -> tuple[STATUS, str]:
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

    peq = iir2peq(iir)
    preamp_gain = peq_preamp_gain(peq)

    params = {}
    for i, current_iir in enumerate(iir):
        params["{}".format(1000 + i)] = 0.0  # True
        params["{}".format(2000 + i)] = type2value(str(current_iir["type"]))
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
    buffer = struct.pack(">llllf", 0, 0, 81, 0, preamp_gain)

    # add pairs of (param_id, value) in big endian
    for param_id, value in params.items():
        buffer += struct.pack(">lf", int(param_id), value)

    # convert the byte buffer to base64
    text = base64.standard_b64encode(buffer).decode("ascii")

    # add \t and slice in chunks of 67 chars
    len_text = len(text) // 67
    slices = [
        "\t{}\n".format(text[i * 67 : (i + 1) * 67]) for i in range(len_text)
    ]
    slices += ["\t{}".format(text[len_text * 67 :])]

    return 0, "".join(slices)


def iir2aupreset(iir: list, name: str) -> tuple[STATUS, str]:
    status, data = iir2data(iir)
    if status != 0:
        return status, ""
    # TODO: investigate why only 16 works
    return 0, AUPRESET_TEMPLATE.substitute(
        data=data, name=name, number_of_bands=16
    )
