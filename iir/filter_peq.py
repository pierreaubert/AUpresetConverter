# -*- coding: utf-8 -*-
import math
import logging
import numpy as np


from iir.filter_iir import Biquad, Vector, Peq


def peq_build(freq: Vector, peq: Peq) -> Vector:
    """compute SPL for each frequency"""
    current_filter = [0.0]
    if len(peq) > 0:
        for w, iir in peq:
            current_filter += np.multiply(w, iir.np_log_result(freq))
    return current_filter


def peq_preamp_gain_conservative(peq: Peq) -> float:
    """compute preamp gain for a peq

    Computation takes into account that the processor could clip for each EQ and not only for the sum of the PEQs
    It depends how it is implemented. For a computer, the other estimation is better.
    Note that we add 0.2 dB to have a margin for clipping
    """
    freq = np.logspace(1 + math.log10(2), 4 + math.log10(2), 1000)
    spl = np.array(peq_build(freq, peq))
    individual = 0.0
    if len(peq) == 0:
        return 0.0
    for _w, iir in peq:
        individual = max(
            individual,
            max(
                0.0,  # if negative doesn't count
                np.max(peq_build(freq, [(1.0, iir)])),
            ),
        )
    overall = np.max(np.clip(spl, 0, None))
    gain = -(max(individual, overall) + 0.2)
    print(
        "debug preamp gain: {:.2f} (overall {:.2f} individual {:0.2f}".format(
            gain, overall, individual
        )
    )
    return -overall


def peq_preamp_gain(peq: Peq) -> float:
    """compute preamp gain for a peq"""
    freq = np.logspace(1 + math.log10(2), 4 + math.log10(2), 1000)
    spl = np.array(peq_build(freq, peq))
    if len(peq) == 0:
        return 0.0
    return -np.max(np.clip(spl, 0, None))


def peq_print(peq: Peq) -> None:
    for _i, iir in enumerate(peq):
        if iir[0] != 0:
            print(iir[1])


def peq_format_apo(comment: str, peq: Peq) -> str:
    res = [comment]
    res.append("Preamp: {:.1f} dB".format(peq_preamp_gain(peq)))
    res.append("")
    for i, data in enumerate(peq):
        _, iir = data
        if iir.typ in (Biquad.PEAK, Biquad.NOTCH, Biquad.BANDPASS):
            res.append(
                "Filter {:2d}: ON {:2s} Fc {:5d} Hz Gain {:+0.2f} dB Q {:0.2f}".format(
                    i + 1, iir.type2str(), int(iir.freq), iir.db_gain, iir.q
                )
            )
        elif iir.typ in (Biquad.LOWPASS, Biquad.HIGHPASS):
            res.append(
                "Filter {:2d}: ON {:2s} Fc {:5d} Hz".format(
                    i + 1, iir.type2str(), int(iir.freq)
                )
            )
        elif iir.typ in (Biquad.LOWSHELF, Biquad.HIGHSHELF):
            res.append(
                "Filter {:2d}: ON {:2s} Fc {:5d} Hz Gain {:+0.2f} dB".format(
                    i + 1, iir.type2str(), int(iir.freq), iir.db_gain
                )
            )
        else:
            logging.error("kind %s is unkown", iir.typ)
    res.append("")
    return "\n".join(res)
