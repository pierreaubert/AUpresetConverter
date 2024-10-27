# -*- coding: utf-8 -*-
import hashlib
import json
import logging
import math
import os
import sys

import sqlite3
from fastapi import FastAPI, Depends, File, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
import uvicorn
from pydantic import BaseModel, Field
import numpy as np

from iir.filter_iir import Peq
from iir.filter_peq import peq_format_apo, peq_print, peq_build
from converter import IIR, lines2iir, iir2aupreset, iir2peq


# ----------------------------------------------------------------------
# constants
# ----------------------------------------------------------------------

API_VERSION = "v0"
CURRENT_VERSION = 0
SOFTWARE_VERSION = f"{API_VERSION}.{CURRENT_VERSION}"

# ----------------------------------------------------------------------
# env variables
# ----------------------------------------------------------------------

ENV = os.getenv("EQCOMPARE_ENV", "dev")

FILES = "/var/www/html/spinorama-eqconverter"
SPIN = "/var/www/html/spinorama-prod"
METADATA = f"{SPIN}/assets/metadata.json"
EQDATA = f"{SPIN}/assets/eqdata.json"
FASTAPI_DEBUG = False

if ENV == "dev":
    SPIN = "/Users/pierrre/src/spinorama/docs/json"
    METADATA = f"{SPIN}/metadata.json"
    EQDATA = f"{SPIN}/eqdata.json"
    FASTAPI_DEBUG = True


KNOWN_FORMATS = set(["txt", "text"])

# ----------------------------------------------------------------------
# data model
# ----------------------------------------------------------------------


class EQ(BaseModel):
    hash: str = Field(min_length=128, max_length=128)
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
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hash TEXT NOT NULL,
        name TEXT NOT NULL,
        peq  TEXT NOT NULL
        )
        """
    )
    connection.commit()
    connection.close()


def create_eq(eq: EQ) -> int:
    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO eqs (hash, name, peq) VALUES (?, ?, ?)",
        (eq.hash, eq.name, eq.peq),
    )
    connection.commit()
    connection.close()
    return 0


def db_get_eqs() -> list[tuple[str, str]]:
    connection = create_connection()
    cursor = connection.cursor()
    results = cursor.execute("SELECT * from  eqs;").fetchall()
    connection.commit()
    connection.close()
    return results


def db_get_eq(hash: str) -> tuple[str, IIR]:
    connection = create_connection()
    cursor = connection.cursor()
    results = cursor.execute(
        f"SELECT name, peq from eqs where hash='{hash}';"
    ).fetchone()
    connection.commit()
    connection.close()
    if not results:
        return "error", []
    name, serialized = results
    iir = eval(serialized)
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

origins = [
    "http://127.0.0.1:7999",
]

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
    encoded = jsonable_encoder(content)
    return JSONResponse(content=encoded)


@backend.post(f"/{API_VERSION}/eq/upload", tags=["EQ"])
async def upload_eq(file: UploadFile = File(...)):
    hash: str = ""
    try:
        buffer = await file.read()
        if not buffer or len(buffer) == 0:
            return {
                "message": "There was an error parsing the file: buffer looks empty",
                "hash": None,
            }
        input = buffer.decode("utf-8")
        if not input or len(input) == 0:
            return {
                "message": "There was an error parsing the file: buffer decoding",
                "hash": None,
            }
        lines = input.split("\n")
        if not lines or len(lines) == 0:
            return {
                "message": "There was an error parsing the file: buffer splitting",
                "hash": None,
            }
        status, iir = lines2iir(lines)
        if status != 0:
            return {
                "message": "There was an error parsing the file as an EQ",
                "hash": None,
            }
        hash = hashlib.blake2b(buffer).hexdigest()
        if not hash:
            return {
                "message": "There was an error parsing the file: hashing failed",
                "hash": None,
            }
        name = file.filename if file.filename else "eq"
        eq = EQ(hash=hash, name=name, peq=str(iir))
        status = create_eq(eq)
        if status != 0:
            return {"message": "Failed to save peq", "hash": None}
    except Exception as e:
        return {
            "message": "There was an error uploading the file {}".format(e),
            "hash": None,
        }

    await file.close()

    return {"message": f"Successfuly uploaded {file.filename}", "hash": hash}


@backend.get(f"/{API_VERSION}/eqs", tags=["EQ"])
async def get_eqs():
    content = db_get_eqs()
    encoded = jsonable_encoder(content)
    return JSONResponse(content=encoded)


@backend.get(f"/{API_VERSION}/eq/target/aupreset", tags=["EQ"])
async def get_eq_aupreset(hash: str):
    name, iir = db_get_eq(hash)
    content = iir2aupreset(iir, name)
    encoded = jsonable_encoder(content)
    return JSONResponse(content=encoded)


@backend.get(f"/{API_VERSION}/eq/target/apo", tags=["EQ"])
async def get_eq_apo(hash: str):
    name, iir = db_get_eq(hash)
    peq = iir2peq(iir)
    content = peq_format_apo(comment=name, peq=peq)
    encoded = jsonable_encoder(content)
    return JSONResponse(content=encoded)


@backend.get(f"/{API_VERSION}/eq/graph_spl", tags=["EQ"])
async def get_eq_graph_spl(hash: str):
    name, iir = db_get_eq(hash)
    peq = iir2peq(iir)
    freq = np.logspace(1+math.log10(2), 4+math.log10(2), 200)
    spl = peq_build(freq, peq)
    content = {'freq': freq.tolist(), 'spl': spl.tolist()}
    encoded = jsonable_encoder(content)
    return JSONResponse(content=encoded)


@backend.get(f"/{API_VERSION}/eq/graph_spl_details", tags=["EQ"])
async def get_eq_graph_spl_details(hash: str):
    name, iir = db_get_eq(hash)
    peq = iir2peq(iir)
    freq = np.logspace(1+math.log10(2), 4+math.log10(2), 200)
    spl = {}
    for i, iir in enumerate(peq):
        spl[i] = peq_build(freq, [iir]).tolist()
    content = {'freq': freq.tolist(), 'spl': spl}
    encoded = jsonable_encoder(content)
    return JSONResponse(content=encoded)


if __name__ == "__main__":
    create_table()
    if ENV == "dev":
        uvicorn.run(
            "backend:backend",
            host="0.0.0.0",
            port=8000,
        )
    elif ENV == "prod":
        uvicorn.run(
            "backend:backend",
            host="0.0.0.0",
            port=9999,
            # using a reverse proxy in front
            # ssl_keyfile="/etc/letsencrypt/live/eqcompare.spinorama.org/key.pem",
            # ssl_certfile="path/to/cert.pem",
        )
