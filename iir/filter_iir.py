# -*- coding: utf-8 -*-
import math
from typing import Any

import numpy as np
import numpy.typing as npt

# Vector = npt.NDArray[np.floating[Any]]
Vector = npt.ArrayLike


def bw2q(bw: float) -> float:
    return math.sqrt(math.pow(2, bw)) / (math.pow(2, bw) - 1)


def q2bw(q: float) -> float:
    q2 = (2.0 * q * q + 1) / (2.0 * q * q)
    return math.log(q2 + math.sqrt(q2 * q2 - 1.0)) / math.log(2.0)


class Biquad:
    # pretend enumeration
    LOWPASS, HIGHPASS, BANDPASS, PEAK, NOTCH, LOWSHELF, HIGHSHELF = range(7)

    type2name = {
        LOWPASS: ["Lowpass", "LP"],
        HIGHPASS: ["Highpass", "HP"],
        BANDPASS: ["Bandpath", "BP"],
        PEAK: ["Peak", "PK"],
        NOTCH: ["Notch", "NO"],
        LOWSHELF: ["Lowshelf", "LS"],
        HIGHSHELF: ["Highshelf", "HS"],
    }

    def __init__(
        self, typ: int, freq: float, srate: int, q: float, db_gain: float = 0
    ):
        types = {
            Biquad.LOWPASS: Biquad.lowpass,
            Biquad.HIGHPASS: Biquad.highpass,
            Biquad.BANDPASS: Biquad.bandpass,
            Biquad.PEAK: Biquad.peak,
            Biquad.NOTCH: Biquad.notch,
            Biquad.LOWSHELF: Biquad.lowshelf,
            Biquad.HIGHSHELF: Biquad.highshelf,
        }
        if typ not in types:
            raise AssertionError
        self.typ = typ
        self.freq = float(freq)
        self.srate = float(srate)
        self.q = float(q)
        self.db_gain = float(db_gain)
        # some control over parameters
        if typ == Biquad.NOTCH:
            self.q = 30.0
        elif self.q == 0.0 and type in (
            Biquad.BANDPASS,
            Biquad.HIGHPASS,
            Biquad.LOWPASS,
        ):
            self.q = 1.0 / math.sqrt(2.0)
        elif self.q == 0.0 and type in (Biquad.LOWSHELF, Biquad.HIGHSHELF):
            self.q = bw2q(0.9)
        # initialize the 5 coefs
        self.a0 = self.a1 = self.a2 = 0
        self.b0 = self.b1 = self.b2 = 0
        # and the 4 coordinates
        self.x1 = self.x2 = 0
        self.y1 = self.y2 = 0
        # if self.typ in (Biquad.PEAK, Biquad.LOWSHELF, Biquad.HIGHSHELF):
        a = math.pow(10, db_gain / 40)
        omega = 2 * math.pi * self.freq / self.srate
        sn = math.sin(omega)
        cs = math.cos(omega)
        alpha = sn / (2 * q)
        beta = math.sqrt(a + a)
        # compute
        types[typ](self, a, omega, sn, cs, alpha, beta)
        # prescale constants
        self.b0 /= self.a0
        self.b1 /= self.a0
        self.b2 /= self.a0
        self.a1 /= self.a0
        self.a2 /= self.a0

        # precompute other parameters
        self.r_up0 = (self.b0 + self.b1 + self.b2) ** 2
        self.r_up1 = -4 * (
            self.b0 * self.b1 + 4 * self.b0 * self.b2 + self.b1 * self.b2
        )
        self.r_up2 = 16 * self.b0 * self.b2
        self.r_dw0 = (1 + self.a1 + self.a2) ** 2
        self.r_dw1 = -4 * (self.a1 + 4 * self.a2 + self.a1 * self.a2)
        self.r_dw2 = 16 * self.a2

    def lowpass(self, a, omega, sn, cs, alpha, beta):
        self.b0 = (1 - cs) / 2
        self.b1 = 1 - cs
        self.b2 = (1 - cs) / 2
        self.a0 = 1 + alpha
        self.a1 = -2 * cs
        self.a2 = 1 - alpha

    def highpass(self, a, omega, sn, cs, alpha, beta):
        self.b0 = (1 + cs) / 2
        self.b1 = -(1 + cs)
        self.b2 = (1 + cs) / 2
        self.a0 = 1 + alpha
        self.a1 = -2 * cs
        self.a2 = 1 - alpha

    def bandpass(self, a, omega, sn, cs, alpha, beta):
        self.b0 = alpha
        self.b1 = 0
        self.b2 = -alpha
        self.a0 = 1 + alpha
        self.a1 = -2 * cs
        self.a2 = 1 - alpha

    def notch(self, a, omega, sn, cs, alpha, beta):
        self.b0 = 1
        self.b1 = -2 * cs
        self.b2 = 1
        self.a0 = 1 + alpha
        self.a1 = -2 * cs
        self.a2 = 1 - alpha

    def peak(self, a, omega, sn, cs, alpha, beta):
        self.b0 = 1 + (alpha * a)
        self.b1 = -2 * cs
        self.b2 = 1 - (alpha * a)
        self.a0 = 1 + (alpha / a)
        self.a1 = -2 * cs
        self.a2 = 1 - (alpha / a)

    def lowshelf(self, a, omega, sn, cs, alpha, beta):
        self.b0 = a * ((a + 1) - (a - 1) * cs + beta * sn)
        self.b1 = 2 * a * ((a - 1) - (a + 1) * cs)
        self.b2 = a * ((a + 1) - (a - 1) * cs - beta * sn)
        self.a0 = (a + 1) + (a - 1) * cs + beta * sn
        self.a1 = -2 * ((a - 1) + (a + 1) * cs)
        self.a2 = (a + 1) + (a - 1) * cs - beta * sn

    def highshelf(self, a, omega, sn, cs, alpha, beta):
        self.b0 = a * ((a + 1) + (a - 1) * cs + beta * sn)
        self.b1 = -2 * a * ((a - 1) + (a + 1) * cs)
        self.b2 = a * ((a + 1) + (a - 1) * cs - beta * sn)
        self.a0 = (a + 1) - (a - 1) * cs + beta * sn
        self.a1 = 2 * ((a - 1) - (a + 1) * cs)
        self.a2 = (a + 1) - (a - 1) * cs - beta * sn

    # perform filtering function
    def __call__(self, x):
        y = (
            self.b0 * x
            + self.b1 * self.x1
            + self.b2 * self.x2
            - self.a1 * self.y1
            - self.a2 * self.y2
        )
        self.x2 = self.x1
        self.x1 = x
        self.y2 = self.y1
        self.y1 = y
        return y

    # provide a static result for a given frequency f
    def result_slow(self, f: float) -> float:
        phi = (math.sin(math.pi * f * 2 / (2 * self.srate))) ** 2
        result = (
            (self.b0 + self.b1 + self.b2) ** 2
            - 4
            * (self.b0 * self.b1 + 4 * self.b0 * self.b2 + self.b1 * self.b2)
            * phi
            + 16 * self.b0 * self.b2 * phi * phi
        ) / (
            (1 + self.a1 + self.a2) ** 2
            - 4 * (self.a1 + 4 * self.a2 + self.a1 * self.a2) * phi
            + 16 * self.a2 * phi * phi
        )
        result = max(0, result)
        return result ** (0.5)

    def result(self, f: float) -> float:
        phi = (math.sin(math.pi * f * 2 / (2 * self.srate))) ** 2
        phi2 = phi * phi
        result = (self.r_up0 + self.r_up1 * phi + self.r_up2 * phi2) / (
            self.r_dw0 + self.r_dw1 * phi + self.r_dw2 * phi2
        )
        result = max(0, result)
        return result ** (0.5)

    # provide a static log result for a given frequency f
    def log_result(self, f: float) -> float:
        try:
            result = 20 * math.log10(self.result(f))
        except:
            result = -200
        return result

    # return computed constants
    def constants(self) -> tuple[float, float, float, float, float]:
        return self.a1, self.a2, self.b0, self.b1, self.b2

    def type2str(self) -> str:
        return self.type2name[self.typ][1]

    def __str__(self):
        return "Type:%s,Freq:%.1f,Rate:%.1f,Q:%.1f,Gain:%.1f" % (
            self.type2str(),
            self.freq,
            self.srate,
            self.q,
            self.db_gain,
        )

    # vector version (10x faster)
    def np_log_result(self, freq: Vector) -> Vector:
        coeff = math.pi * 2 / (2 * self.srate)
        phi = np.square(np.sin(np.multiply(coeff, freq)))
        phi2 = np.square(phi)
        r = (self.r_up0 + self.r_up1 * phi + self.r_up2 * phi2) / (
            self.r_dw0 + self.r_dw1 * phi + self.r_dw2 * phi2
        )
        return 20.0 * np.log10(np.sqrt(np.where(r <= 1.0e-20, 1.0e-20, r)))


# type declaration
Peq = list[tuple[float, Biquad]]
