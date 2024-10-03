# -*- coding: utf-8 -*-

import math

import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from plotly.subplots import make_subplots
import reflex as rx

# from rxconfig import config


from app.iir.filter_peq import peq_build
from .converter import lines2iir, iir2aupreset, iir2peq

# ----------------------------------------------------------------------
# generate graphs
# ----------------------------------------------------------------------

colors = [
    "#5c77a5",
    "#dc842a",
    "#c85857",
    "#89b5b1",
    "#71a152",
    "#bab0ac",
    "#e15759",
    "#b07aa1",
    "#76b7b2",
    "#ff9da7",
]


def print_freq(freq: float) -> str:
    """Pretty print frequency"""
    if freq < 1000.0:
        return f"{int(freq)}Hz"

    if int(freq) % 1000 == 0:
        return f"{freq // 1000}kHz"

    return f"{freq / 1000:0.1f}kHz"


def graph_eq_each(freq, peq):
    """take a PEQ and return traces (for plotly) with frequency data"""
    data_frame = pd.DataFrame({"Freq": freq})
    for i, (pos, biquad) in enumerate(peq):
        data_frame[f"{biquad.type2str()} {i}"] = peq_build(
            freq, [(pos, biquad)]
        )

    traces = []
    for i, key in enumerate(data_frame.keys()):
        if key != "Freq":
            traces.append(
                go.Scatter(
                    x=data_frame.Freq,
                    y=data_frame[key],
                    name=key,
                    legendgroup="PEQ",
                    legendgrouptitle_text="EQ",
                    marker_color=colors[i % len(colors)],
                )
            )
    return traces


def graph_eq(freq, peq):
    return go.Scatter(x=freq, y=peq_build(freq, peq), name="EQ")


def generate_xaxis(freq_min=20, freq_max=20000):
    return dict(
        title_text="Frequency (Hz)",
        type="log",
        range=[math.log10(freq_min), math.log10(freq_max)],
        showline=True,
        dtick="D1",
    )


def generate_yaxis():
    return dict(
        title_text="SPL (dB)",
        showline=True,
    )


def iir2graphs(iir):
    freq = np.logspace(1 + math.log10(2), 4 + math.log10(2), 60)
    peq = iir2peq(iir)
    t1 = graph_eq_each(freq, peq)
    t2 = graph_eq(freq, peq)
    fig = make_subplots(
        rows=2, cols=1
    )  # , vertical_spacing=0.05, row_heights=[0.30, 0.30])
    for t in t1:
        fig.add_trace(t, row=1, col=1)
    fig.add_trace(t2, row=2, col=1)
    fig.update_xaxes(generate_xaxis(), row=1, col=1)
    fig.update_xaxes(generate_xaxis(), row=2, col=1)
    fig.update_yaxes(generate_yaxis(), row=1, col=1)
    fig.update_yaxes(generate_yaxis(), row=2, col=1)
    # fig.update_layout(height=800, width=800)
    return fig


def iir2graph(iir):
    freq = np.logspace(1 + math.log10(2), 4 + math.log10(2), 60)
    peq = iir2peq(iir)
    t2 = graph_eq(freq, peq)
    fig = go.Figure()
    fig.add_trace(t2)
    fig.update_xaxes(generate_xaxis())
    fig.update_yaxes(generate_yaxis())
    return fig


def preset_name(name: str) -> str:
    dotpos = name.rfind(".")
    if dotpos != -1:
        return name[:dotpos]
    return name


# ----------------------------------------------------------------------
# Download
# ----------------------------------------------------------------------


class SpeakerDownloader(rx.State):
    """
    Download data for speakers and headphones
    """

    # list of presets EQ
    eq_speakers: list[str] = []
    len_speakers: int = 0
    eq_speaker_selected: str = ""

    def init_speakers(self):
        r = requests.get("https://spinorama.org/json/eqdata.json")
        if r.status_code in (200, 304):
            eqs = r.json()
            self.eq_speakers = list(eqs.keys())
            self.len_speakers = len(self.eq_speakers)
        else:
            self.len_speakers = r.status_code

    @rx.var
    def eq_speakers2(self) -> list[str]:
        self.init_speakers()
        return self.eq_speakers

    @rx.var
    def len_speakers2(self) -> int:
        self.init_speakers()
        return self.len_speakers


class HeadphoneDownloader(rx.State):
    """
    Download data for speakers and headphones
    """

    # list of presets EQ
    eq_headphones: list[str] = []
    len_headphones: int = 0
    eq_headphone_selected: str = ""

    def init_headphones(self):
        r = requests.get("https://spinorama.org/json/eqdata.json")
        if r.status_code in (200, 304):
            eqs = r.json()
            self.eq_headphones = list(eqs.keys())
            self.len_headphones = len(self.eq_headphones)
        else:
            self.len_headphones = r.status_code

    @rx.var
    def eq_headphones2(self) -> list[str]:
        self.init_headphones()
        return self.eq_headphones

    @rx.var
    def len_headphones2(self) -> int:
        self.init_headphones()
        return self.len_headphones


# ----------------------------------------------------------------------
# iir formatter
# ----------------------------------------------------------------------


class Uploader(rx.State):
    """The Uploader state."""

    # list of name, input eq, output eq, plot
    data: list[tuple[str, str, str, go.Figure]] = []
    err_msg: str = ""
    error: bool = False

    def text2data(self, input, name, lines) -> int:
        status, iir = lines2iir(lines)
        if status != 0:
            self.error = True
            self.err_msg = "failed to parse the input file {}".format(status)
            return 1
        preset = preset_name(name)
        status, output = iir2aupreset(iir, preset)
        if status != 0:
            self.error = True
            self.err_msg = "failed to generate the preset {} status {}".format(
                preset, status
            )
            return 1
        fig = go.Figure() # iir2graph(iir)
        self.data.append((preset, input, output, fig))
        return 0

    async def handle_upload(self, files: list[rx.UploadFile]):
        self.data = []
        self.err_msg = ""
        self.error = False

        for file in files:
            if file.filename is None:
                self.error = True
                self.err_msg = "Filename is empty"
                continue
            buffer = await file.read()
            if buffer is None or len(buffer) == 0:
                self.error = True
                self.err_msg = "buffer failed"
                continue
            input = buffer.decode("utf-8")
            if input is None or len(input) == 0:
                self.error = True
                self.err_msg = "input failed"
                continue
            lines = input.split("\n")
            if lines is None or len(lines) == 0:
                self.error = True
                self.err_msg = "splitting failed"
                continue
            status, iir = lines2iir(lines)
            if status != 0:
                self.error = True
                self.err_msg = "failed to parse the input file {}".format(
                    status
                )
                return 1
            preset = preset_name(file.filename)
            status, output = iir2aupreset(iir, preset)
            if status != 0:
                self.error = True
                self.err_msg = (
                    "failed to generate the preset {} status {}".format(
                        preset, status
                    )
                )
                return 1
            fig = iir2graph(iir)
            self.data.append((preset, input, output, fig))

    async def save(self, filename):
        for file, _, output_data, _ in self.data:
            if file == filename:
                output_filename = "{}.aupreset".format(
                    preset_name(filename),
                )
                return rx.download(data=output_data, filename=output_filename)


color = "rgb(107,99,246)"


# ----------------------------------------------------------------------
# page structure
# ----------------------------------------------------------------------


def block_title():
    return rx.text(
        "Convert your REW or APO EQ file into an AUpreset file",
        background_clip="text",
        font_weight="bold",
        font_size="1em",
    )


def block_upload() -> rx.Component:
    return rx.upload(
        rx.vstack(
            rx.button(
                "Select File",
                color=color,
                bg="white",
                border=f"1px solid {color}",
                size="1",
                id="SelectFile",
            ),
            rx.cond(
                Uploader.error,
                rx.callout(
                    Uploader.err_msg,
                    icon="triangle_alert",
                    color_scheme="red",
                    size="1",
                ),
            ),
        ),
        id="upload2",
        multiple=True,
        accept={
            "application/plain": [".txt"],
        },
        max_files=6,
        max_size=10 * 1024,
        disabled=False,
        on_drop=Uploader.handle_upload(rx.upload_files(upload_id="upload2")),
        border=f"1px dotted {color}",
        padding="2em",
    )


@rx.page(on_load=SpeakerDownloader.init_speakers)
def block_pickup_preset_speakers() -> rx.Component:
    return rx.select(
        SpeakerDownloader.eq_speakers2,
        placeholder=f"{SpeakerDownloader.len_speakers2} speakers",
        on_change=SpeakerDownloader.set_eq_speaker_selected,
        id="SelectSpeaker",
    )


@rx.page(on_load=HeadphoneDownloader.init_headphones)
def block_pickup_preset_headphones() -> rx.Component:
    return rx.select(
        HeadphoneDownloader.eq_headphones2,
        placeholder=f"{HeadphoneDownloader.len_headphones2} headphones",
        on_change=HeadphoneDownloader.set_eq_headphone_selected,
        id="SelectHeadphone",
    )


def block_pickup_preset() -> rx.Component:
    return rx.vstack(
        block_pickup_preset_speakers(),
        # block_pickup_preset_headphones(),
        padding="0.5em",
    )


def block_acquire() -> rx.Component:
    return rx.vstack(
        rx.flex(
            rx.vstack(
                rx.text(
                    "Either drag and drop EQ files here",
                    font_size="0.6em",
                ),
                block_upload(),
                padding="1em",
            ),
            #            rx.vstack(
            #                rx.text(
            #                    "Or select a predefined EQ",
            #                    font_size="0.6em",
            #                ),
            #                block_pickup_preset(),
            #                padding="1em",
            #            ),
        ),
        padding="2em",
    )


def block_answer() -> rx.Component:
    return rx.grid(
        rx.foreach(
            Uploader.data,
            lambda item: rx.box(
                rx.vstack(
                    rx.text(
                        "Successfully loaded {}".format(item[0]),
                        size="2",
                        font_weight="bold",
                    ),
                    rx.code_block(item[1], language="yaml", font_size="0.6em"),
#                    rx.text(
#                        "Visually, it looks like:",
#                        size="2",
#                        font_weight="bold",
#                    ),
#                    rx.plotly(data=item[3]),
                    rx.hstack(
                        rx.text(
                            "Successfully generated {}.aupreset".format(
                                item[0]
                            ),
                            font_weight="bold",
                            size="2",
                        ),
                        rx.button(
                            "Save It!",
                            color=color,
                            bg="white",
                            border=f"1px solid {color}",
                            on_click=Uploader.save(item[0]),
                            size="1",
                        ),
                    ),
                    rx.text(
                        "and move it to ~/Library/Audio/Presets/Apple/AUNBandEQ",
                        font_weight="bold",
                        font_size="0.6em",
                    ),
 #                   rx.code_block(
 #                       item[2], language="xml-doc", font_size="0.6em"
 #                   ),
                ),
            ),
        ),
        columns="2",
        spacing="1",
    )


def index() -> rx.Component:
    """The main view."""
    return rx.vstack(
        block_title(),
        block_acquire(),
        block_answer(),
    )


app = rx.App()
app.add_page(index)
