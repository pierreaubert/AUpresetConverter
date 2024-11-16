# -*- coding: utf-8 -*-
import ast
import hashlib
import json
import logging
import math
import re
import os
import sys
from typing_extensions import Annotated

import sqlite3
from fastapi import FastAPI, Depends, UploadFile, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
from pydantic import BaseModel, Field, StringConstraints
from starlette.responses import JSONResponse
import uvicorn

from iir.filter_iir import Biquad
from iir.filter_peq import peq_format_apo, peq_build
from converter import (
    IIR,
    lines2iir,
    iir2aupreset,
    iir2peq,
    iir2rme_totalmix_channel,
    iir2rme_totalmix_room,
)

# ----------------------------------------------------------------------
# constants
# ----------------------------------------------------------------------

API_VERSION = "v1"
CURRENT_VERSION = 3
SOFTWARE_VERSION = f"{API_VERSION}.{CURRENT_VERSION}"

# ----------------------------------------------------------------------
# env variables
# ----------------------------------------------------------------------

ENV = os.getenv("EQCONVERTER_ENV", "dev")

FILES = "/var/www/html/spinorama-eqconverter"
SPIN = "/var/www/html/spinorama-prod"
METADATA = f"{SPIN}/json/metadata.json"
EQDATA = f"{SPIN}/json/eqdata.json"
FASTAPI_DEBUG = False
SERVER = "https://eqconverter.spinorama.org/{}".format(API_VERSION)

if ENV == "dev":
    SERVER = "http://127.0.0.1:8000/{}".format(API_VERSION)
    SPIN = "/Users/pierre/src/spinorama/docs/json"
    METADATA = f"{SPIN}/metadata.json"
    EQDATA = f"{SPIN}/eqdata.json"
    FASTAPI_DEBUG = True


KNOWN_FORMATS = {"txt", "text", "aupreset"}

# ----------------------------------------------------------------------
# data model
# ----------------------------------------------------------------------

HashStr = Annotated[
    str, StringConstraints(min_length=128, max_length=128, pattern=r"[a-z0-9]+")
]


def check_hash(input: str) -> bool:
    if len(input) != 128:
        return False
    return re.search("^[a-z0-9]+$", input)


class EQ(BaseModel):
    eq_hash: HashStr
    name: str = Field(min_length=5, max_length=64)
    peq: str = Field(max_length=4096)


def create_connection():
    connection = sqlite3.connect("eqs.db")
    return connection


def create_table():
    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS eqs (
        eq_hash TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        peq  TEXT NOT NULL
        )
        """
    )
    connection.commit()
    connection.close()


def create_eq(eq: EQ) -> bool:
    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO eqs (eq_hash, name, peq) VALUES (?, ?, ?) ON CONFLICT (eq_hash) DO UPDATE SET name=excluded.name",
        (eq.eq_hash, eq.name, eq.peq),
    )
    connection.commit()
    connection.close()
    return True


def db_get_eqs() -> list[tuple[str, str]]:
    connection = create_connection()
    cursor = connection.cursor()
    results = cursor.execute("SELECT * from  eqs;").fetchall()
    connection.commit()
    connection.close()
    return results


def db_get_eq(eq_hash: str) -> tuple[str, IIR]:
    connection = create_connection()
    cursor = connection.cursor()
    if not check_hash(eq_hash):
        return "error", []
    results = cursor.execute(
        "SELECT name, peq from eqs where eq_hash='{}';".format(eq_hash)  # noqa: S608
    ).fetchone()
    connection.commit()
    connection.close()
    if not results:
        return "error", []
    name, serialized = results
    iir = ast.literal_eval(serialized)
    return name, iir


# ----------------------------------------------------------------------
# load various data
# ----------------------------------------------------------------------


def load_metadata():
    if not os.path.exists(METADATA):
        logging.error("Cannot find %s", METADATA)
        sys.exit(1)

    with open(METADATA, "r", encoding="utf8") as f:
        metadata = json.load(f)
        yield metadata


def load_eqdata():
    if not os.path.exists(EQDATA):
        logging.error("Cannot find %s", EQDATA)
        sys.exit(1)

    with open(EQDATA, "r", encoding="utf8") as f:
        eqdata = json.load(f)
        yield eqdata


# ----------------------------------------------------------------------
# fastpi
# ----------------------------------------------------------------------
backend = FastAPI(
    debug=FASTAPI_DEBUG,
    title="EQ Converter API",
    version=SOFTWARE_VERSION,
    on_startup=[load_metadata],
)

origins = []

if ENV == "dev":
    origins.append("https://127.0.0.1")
    backend.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@backend.get(f"/{API_VERSION}/brands", tags=["Speaker Anechoic EQ"])
async def get_brand_list(metadata: dict = Depends(load_metadata)):  # noqa: B008
    return sorted({v.get("brand") for _, v in metadata.items()})


@backend.get(f"/{API_VERSION}/speakers", tags=["Speaker Anechoic EQ"])
async def get_speaker_list(metadata: dict = Depends(load_metadata)):  # noqa: B008
    return sorted(metadata.keys())


@backend.get(
    f"/{API_VERSION}/speaker/{{speaker_name}}/metadata",
    tags=["Speaker Anechoic EQ"],
)
async def get_speaker_metadata(
    speaker_name: str,
    metadata: dict = Depends(load_metadata),  # noqa: B008
):
    content = metadata.get(speaker_name, {"error": "Speaker not found"})
    encoded = jsonable_encoder(content)
    return JSONResponse(content=encoded)


@backend.get(
    f"/{API_VERSION}/speaker/{{speaker_name}}/eqdata",
    tags=["Speaker Anechoic EQ"],
)
async def get_speaker_eqdata(
    speaker_name: str,
    eqdata: dict = Depends(load_eqdata),  # noqa: B008
):
    content = eqdata.get(speaker_name, {"error": "Speaker not found"})
    flat = []
    if "eqs" in content:
        for key in content["eqs"]:
            eq = content["eqs"][key]
            lines = [
                "{} {}".format(eq["display_name"], eq["filename"]),
                "\n",
                "Preamp gain: {:+3.1f}".format(float(eq["preamp_gain"])),
            ]
            for i, iir in enumerate(eq["peq"]):
                iir_type = Biquad.type2name[iir["type"]][1]
                iir_freq = int(iir["freq"])
                iir_q = float(iir["Q"])
                iir_gain = float(iir["dbGain"])
                lines.append(
                    "Filter {:2d} ON {:s} Fc {:d} Hz Gain {:4.1f} dB Q {:4.2f}".format(
                        i,
                        iir_type,
                        iir_freq,
                        iir_gain,
                        iir_q,
                    )
                )
            lines.append("\n")
            buffer = "\n".join(lines).encode(encoding="utf-8")
            success, hash_or_msg = store_eq(speaker_name, buffer)
            if not success:
                raise HTTPException(status_code=500, detail=hash_or_msg)
            eq["hash"] = hash_or_msg
            flat.append(
                {
                    "hash": hash_or_msg,
                    "eq": "\n".join(lines),
                    "display_name": eq["display_name"],
                    "name": key,
                }
            )
    encoded = jsonable_encoder(flat)
    return JSONResponse(content=encoded)


def eq2hash(buffer: bytes) -> str:
    return hashlib.blake2b(buffer).hexdigest()


def store_eq(filename: str, buffer: bytes) -> tuple[bool, str]:
    input = buffer.decode("utf-8")
    if not input or len(input) == 0:
        return False, "There was an error parsing the file: buffer decoding"
    lines = input.split("\n")
    if not lines or len(lines) == 0:
        return False, "There was an error parsing the file: buffer splitting"
    success, iir = lines2iir(lines)
    if not success:
        return False, "There was an error parsing the file as an EQ"
    eq_hash = eq2hash(buffer)
    if not eq_hash:
        return (
            False,
            "There was an error computing the hash failed",
        )
    name = filename if filename else "eq"
    eq = EQ(eq_hash=eq_hash, name=name, peq=str(iir))
    success = create_eq(eq)
    if not success:
        return False, "Failed to save peq"
    return True, eq_hash


@backend.post(f"/{API_VERSION}/eq/upload", tags=["EQ"])
async def upload_eq(files: list[UploadFile]):
    content = []
    for file in files:
        hash_or_msg: str = ""
        try:
            buffer = await file.read()
            if not buffer or len(buffer) == 0:
                content.append(
                    {
                        "status": "failed",
                        "message": "There was an error parsing the file: buffer looks empty",
                        "hash": None,
                    }
                )
                continue
            if file.filename is None:
                content.append(
                    {
                        "status": "failed",
                        "message": "There was an error with the name of the file",
                        "hash": None,
                    }
                )
                continue
            success, hash_or_msg = store_eq(file.filename, buffer)
            if not success:
                content.append(
                    {
                        "status": "failed",
                        "message": hash_or_msg,
                        "hash": None,
                    }
                )
                continue
        except Exception as e:
            content.append(
                {
                    "status": "failed",
                    "message": "There was an error uploading the file {}".format(
                        e
                    ),
                    "hash": None,
                }
            )
            continue
        await file.close()
        content.append(
            {
                "status": "ok",
                "name": file.filename,
                "hash": hash_or_msg,
            }
        )
    return content


@backend.get(f"/{API_VERSION}/eqs", tags=["EQ"])
async def get_eqs():
    content = db_get_eqs()
    encoded = jsonable_encoder(content)
    return JSONResponse(content=encoded)


@backend.get(f"/{API_VERSION}/eq/target/aupreset", tags=["EQ"])
async def get_eq_aupreset(eq_hash: str):
    name, iir = db_get_eq(eq_hash)
    content = iir2aupreset(iir, name)
    encoded = jsonable_encoder(content)
    return JSONResponse(content=encoded)


@backend.get(f"/{API_VERSION}/eq/target/apo", tags=["EQ"])
async def get_eq_apo(eq_hash: str):
    name, iir = db_get_eq(eq_hash)
    peq = iir2peq(iir)
    content = peq_format_apo(comment=name, peq=peq)
    encoded = jsonable_encoder(content)
    return JSONResponse(content=encoded)


@backend.get(f"/{API_VERSION}/eq/target/rme_totalmix_channel", tags=["EQ"])
async def get_eq_rme_totalmix_channel(eq_hash: str):
    _, iir = db_get_eq(eq_hash)
    success, content = iir2rme_totalmix_channel(iir)
    if not success:
        print(content)
        raise HTTPException(status_code=500, detail=iir)
    encoded = jsonable_encoder(content)
    return JSONResponse(content=encoded)


@backend.get(f"/{API_VERSION}/eq/target/rme_totalmix_room", tags=["EQ"])
async def get_eq_rme_totalmix_room(eq_hash_left: str, eq_hash_right: str):
    _, iir_left = db_get_eq(eq_hash_left)
    iir_right = iir_left
    if eq_hash_right != "":
        _, iir_right = db_get_eq(eq_hash_right)
    success, content = iir2rme_totalmix_room(iir_left, iir_right)
    if not success:
        raise HTTPException(
            status_code=500, detail="{} {}".format(iir_left, iir_right)
        )
    encoded = jsonable_encoder(content)
    return JSONResponse(content=encoded)


@backend.get(f"/{API_VERSION}/eq/graph_spl", tags=["EQ"])
async def get_eq_graph_spl(eq_hash: str):
    _, iir = db_get_eq(eq_hash)
    peq = iir2peq(iir)
    freq = np.logspace(1 + math.log10(2), 4 + math.log10(2), 200)
    spl = peq_build(freq, peq)
    content = {"freq": freq.tolist(), "spl": spl.tolist()}
    encoded = jsonable_encoder(content)
    return JSONResponse(content=encoded)


@backend.get(f"/{API_VERSION}/eq/graph_spl_details", tags=["EQ"])
async def get_eq_graph_spl_details(eq_hash: str):
    _, iir = db_get_eq(eq_hash)
    peq = iir2peq(iir)
    freq = np.logspace(1 + math.log10(2), 4 + math.log10(2), 200)
    spl = {}
    for i, iir in enumerate(peq):
        spl[i] = peq_build(freq, [iir]).tolist()
    content = {"freq": freq.tolist(), "spl": spl}
    encoded = jsonable_encoder(content)
    return JSONResponse(content=encoded)


if __name__ == "__main__":
    create_table()
    if ENV == "dev":
        uvicorn.run(
            "backend:backend",
            host="127.0.0.1",
            port=8000,
        )
    else:
        uvicorn.run(
            "backend:backend",
            host="127.0.0.1",
            port=9999,
            # using a reverse proxy in front
            # ssl_keyfile="/etc/letsencrypt/live/eqcompare.spinorama.org/key.pem",
            # ssl_certfile="path/to/cert.pem",
        )
