#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pathlib

import reflex as rx

from rxconfig import config

from .converter import lines2iir, iir2aupreset, PRESET_DIR

def preset_name(name:str) -> str:
    dotpos = name.rfind(".")
    if dotpos != -1:
        return name[:dotpos]
    return name


class Converter(rx.State):
    """The Converter state."""

    # list of name, input/output
    data: list[tuple[str, str, str]] = ()
    err_msg: str = ''

    async def handle_upload(self, files: list[rx.UploadFile]):
        self.data = []
        self.err_msg = ""
        for file in files:
            buffer = await file.read()
            input = buffer.decode("utf-8")
            status, iir = lines2iir(input.split("\n"))
            if status != 0:
                self.err_msg = "failed to parse the input file {}".format(
                    status
                )
                return
            preset = preset_name(preset_name(file.filename))
            status, output = iir2aupreset(iir, preset)
            if status != 0:
                self.err_msg = "failed to generate the preset {} status {}".format(preset, status)
                return
            self.data.append([file.filename, input, output])


    async def save(self, filename):
        for file, _, output_data in self.data:
            if file == filename:
                output_filename = '{}.aupreset'.format(
                    preset_name(filename),
                )
                return rx.download(
                    data=output_data,
                    filename=output_filename
                )

    def error(self):
        return self.err_msg and len(self.err_msg) > 0



color = "rgb(107,99,246)"


def index():
    """The main view."""
    return rx.vstack(
        rx.text(
            "Convert your REW or APO EQ file into an AUpreset file",
            background_clip="text",
            font_weight="bold",
            font_size="2em",
        ),
        rx.upload(
            rx.vstack(
                rx.button(
                    "Select File",
                    color=color,
                    bg="white",
                    border=f"1px solid {color}",
                ),
                rx.text("Drag and drop EQ files here or click to select files"),
                rx.cond(
                    Converter.error(),
                    rx.text(Converter.err_msg),
                ),
            ),
            id="upload2",
            multiple=True,
            accept={
                "application/text": [".txt"],
            },
            max_files=6,
            disabled=False,
            on_drop=Converter.handle_upload(
                rx.upload_files(upload_id="upload2")
            ),
            border=f"1px dotted {color}",
            padding="5em",
        ),
        rx.grid(
            rx.foreach(
                Converter.data,
                lambda data: rx.box(
                    rx.vstack(
                        rx.text(
                            "Successfully loaded {}".format(data[0]),
                            font_weight="bold",
                            font_size="1em",
                        ),
                        rx.vstack(
                            rx.foreach(
                                data[1].split("\n"),
                                lambda txt: rx.text(
                                    txt,
                                    font_size="0.6em"
                                ),
                            ),
                        ),
                        rx.vstack(
                            rx.text(
                                "Successfully generated {}".format(data[0]),
                                font_weight="bold",
                                font_size="1em",
                            ),
                            rx.button(
                                "Save It!",
                                color=color,
                                bg="white",
                                border=f"1px solid {color}",
                                on_click=Converter.save(data[0]),
                            ),
                            rx.text(
                                "and move it to ~/Library/Audio/Presets/Apple/AUNBandEQ",
                                font_weight="bold",
                                font_size="1em",
                            ),
                        ),
                        rx.code_block(
                            data[2],
                            language="xml-doc",
                            font_size="0.6em"
                        ),
                    ),
                ),
            ),
            columns="1",
            spacing="1",
        ),
        padding="5em",
    )


app = rx.App()
app.add_page(index)
