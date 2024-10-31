#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pathlib
import sys

from converter import (
    file2iir,
    iir2aupreset,
    PRESET_DIR,
    iir2rme_totalmix_channel,
    iir2rme_totalmix_room,
)


def usage():
    print(
        "Usage: {} -input *infiles* -format *format* [-output *outfile*] [-install]".format(
            sys.argv[0]
        )
    )
    print("Parameters")
    print("    *infile* the name of your eq files separated by comma.")
    print("    *format* can be one of aupreset, apo, rmetmeq, rmetmreq.")
    print(
        "    *outfile* the name of the generated eq file, if not specified stdout will be used."
    )
    print(
        "    -install if the specified format as a specific directory the EQ will be copied in it"
    )
    print("")
    print("Examples")
    print(
        "{} -input eq.txt -format aupreset -output eq.aupreset".format(
            sys.argv[0]
        )
    )
    print("{} -input eq.txt -output eq.aupreset -install".format(sys.argv[0]))
    print(
        "   It will copy output to ~/Library/Audio/Presets/Apple/AUNBandEQ/eq.aupreset"
    )
    print(
        "{} -input eq.txt -format rmetmeq -output eq.tmeq".format(sys.argv[0])
    )
    print(
        "{} -input left.txt,rigt.txt -format rmetmreq -output eq.tmreq".format(
            sys.argv[0]
        )
    )
    print("")


def main():
    cond_too_short = len(sys.argv) < 5
    cond_too_long = len(sys.argv) > 8
    cond_no_input = sys.argv[1] != "-input"
    files = sys.argv[2].split(",")
    cond_input_exists = not os.path.exists(files[0])
    cond_input_file = not os.path.isfile(files[0])
    cond_no_format = sys.argv[3] != "-format"
    cond_unknown_format = sys.argv[4] not in (
        "apo",
        "aupreset",
        "rmetmeq",
        "rmetmreq",
    )
    cond_output = len(sys.argv) > 5 and sys.argv[5] != "-output"
    if (
        cond_too_short
        or cond_too_long
        or cond_no_input
        or cond_no_format
        or cond_no_input
        or cond_unknown_format
        or cond_output
        or cond_input_exists
        or cond_input_file
    ):
        usage()
        if cond_too_short:
            print("Error: not enough arguments {}".format(len(sys.argv)))
        if cond_too_long:
            print("Error: too manyarguments {}".format(len(sys.argv)))
        if cond_no_input:
            print("Error: argument 1 {} must be -input".format(sys.argv[1]))
        if cond_input_exists:
            print("Error: argument 2 {} does not exist".format(sys.argv[2]))
        if cond_input_file:
            print("Error: argument 2 {} is not a file".format(sys.argv[2]))
        if cond_no_format:
            print("Error: argument 3 {} must be -format".format(sys.argv[3]))
        if cond_unknown_format:
            print(
                "Error: argument 4 {} must be a known format".format(
                    sys.argv[4]
                )
            )
        if cond_output:
            print("Error: argument 5 {} must be -output".format(sys.argv[5]))
        sys.exit(-1)

    output_format = sys.argv[4]
    rew_filename = files[0]
    rew_base = rew_filename
    dotpos = rew_filename.rfind(".")
    if dotpos != -1:
        rew_base = rew_filename[:dotpos]
    preset_name = pathlib.Path(rew_base).name

    success, iir = file2iir(rew_filename)
    if not success or len(iir) == 0:
        print("Parsing failed! for {}".format(rew_filename))
        return 1

    success = True
    result = ""
    output = ""
    if output_format == "aupreset":
        success, result = iir2aupreset(iir, preset_name)
        if not success:
            print("Generation failed! for {}".format(rew_filename))
            return success
        output = "{}.aupreset".format(rew_base)
    elif output_format == "rmetmeq":
        success, result = iir2rme_totalmix_channel(iir)
        if not success:
            print("Generation failed! for {}".format(rew_filename))
            return success
        output = "{}.tmeq".format(rew_base)
    elif output_format == "rmetmreq":
        if len(files) == 1:
            success, result = iir2rme_totalmix_room(iir, [])
            if not success:
                print("Converting to RME room eq failed {}".format(files[0]))
                return 1
            output = "{}.tmreq".format(rew_base)
        elif len(files) == 2:
            iir_left = iir
            success, iir_right = file2iir(files[1])
            if not success or len(iir_right) == 0:
                print("Parsing failed! for {}".format(files[1]))
                return 1
            success, result = iir2rme_totalmix_room(iir_left, iir_right)
            if not success:
                print(
                    "Converting to RME room eq failed for {} and {}".format(
                        files[0], files[1]
                    )
                )
                return 1
            output = "{}.tmreq".format(rew_base)
        else:
            print(
                "Warning: RME TotalMix Room EQ takes at most 2 EQs (left, right)"
            )
        if not success:
            print("Generation failed! for {}".format(rew_filename))
            return success

    if len(sys.argv) == 5:
        print("Generated file:")
        print(result)
        return 0

    if output_format == "aupreset" and sys.argv[-1] == "-install":
        PRESET_DIR.mkdir(mode=0o755, parents=True, exist_ok=True)
        output = "{}/{}.aupreset".format(PRESET_DIR, preset_name)

    try:
        with open(output, "w", encoding="ascii") as fd:
            fd.write(result)
    except FileNotFoundError:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
