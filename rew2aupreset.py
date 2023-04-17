#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import struct
import sys
import base64
from string import Template

aupreset_template = Template('\
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
')

def rew2iir(filename: str) -> list[dict]:
    #has_width = False
    iir = []
    with open(filename, "r", encoding='ASCII') as fd:
        lines = fd.readlines()
        for line in lines:
            #if line.find("AU_N-Band_EQ"):
            #    has_width = True
            tokens = line.split()
            if len(tokens) != 8 or tokens[0] == "Number" or tokens[3] == "None":
                continue
            iir.append({
                "type": tokens[3],
                "freq": float(tokens[4]),
                "gain": float(tokens[5]),
                "width": float(tokens[6]),
            })

    return iir


def iir2data(iir: list) -> str:

    def type2value(t):
        if t == "PK":
            return 0.0
        elif t == "LS":
            return 8.0
        elif t == "HS":
            return 9.0
        elif t == "BP":
            return 6.0
        return -1.0
       
    len_iir = len(iir)
    #print(len_iir)
    #print(iir)

    params = {}
    for i, current_iir in enumerate(iir):
        params["{}".format(1000+i)] = 0.0
        params["{}".format(2000+i)] = type2value(current_iir["type"])
        params["{}".format(3000+i)] = float(current_iir["freq"])
        params["{}".format(4000+i)] = float(current_iir["gain"])
        params["{}".format(5000+i)] = float(current_iir["width"])

    for i in range(len_iir, 16):
        params["{}".format(1000+i)] = 1.0
        params["{}".format(2000+i)] = 0.0
        params["{}".format(3000+i)] = 0.0
        params["{}".format(4000+i)] = 0.0
        params["{}".format(5000+i)] = 0.0

    #    print(len(params))
    #    print(params)
    assert len(params) == 80

    # some black magic, data is padded, the only important value is number of parameters + 1
    buffer = struct.pack(">lllll", 0, 0, 81, 0, 0)

    # add pairs of (param_id, value) in big endian
    for param_id, value in params.items():
        buffer += struct.pack(">lf", int(param_id), value)

    # convert the byte buffer to base64
    text = base64.standard_b64encode(buffer).decode('ascii')

    # add \t and slice in chunks of 67 chars
    len_text = len(text)//67
    slices = ["\t{}\n".format(text[i*67:(i+1)*67]) for i in range(len_text)]
    slices += ["\t{}".format(text[len_text*67:])]
    return "".join(slices)


def iir2aupreset(iir: list, name: str) -> str:
    number_of_bands = len(iir)
    data = iir2data(iir)
    return aupreset_template.substitute(
        data=data,
        name=name,
        number_of_bands=16
    )
                             

def main():
    if len(sys.argv) != 2:
        sys.exit(-1)
    rew_filename = sys.argv[1]

    iir = rew2iir(rew_filename)
    if len(iir) == 0:
        return 1

    aupreset = iir2aupreset(iir, 'test')
    print(aupreset)
    return 0

if __name__ == "__main__":
    sys.exit(main())
