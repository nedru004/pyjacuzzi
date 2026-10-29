#!/usr/bin/env python3
"""
Connects to a Jacuzzi Prolink / RS485-to-TCP bridge and prints raw frames.

Usage:
  python3 tools/sniff_prolink_tcp.py --host 192.168.0.8 --port 8899

Notes:
- Frames are assumed to be Balboa/Jacuzzi style:
    0x7E <len> <payload...> <checksum> 0x7E
  where <len> is the number of bytes between the length byte and the final 0x7E,
  i.e. it includes checksum and excludes the starting 0x7E.
- This script is intentionally conservative: it prints even “weird” frames to help debug.
"""

import argparse
import asyncio
import datetime as _dt


M_STARTEND = 0x7E


def _ts() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def balboa_calc_cs(data: bytes, length: int) -> int:
    """Checksum algorithm used by balboa.py / jacuzzi.py."""
    crc = 0xB5
    for cur in range(length):
        for i in range(8):
            bit = crc & 0x80
            crc = ((crc << 1) & 0xFF) | ((data[cur] >> (7 - i)) & 0x01)
            if bit:
                crc = crc ^ 0x07
        crc &= 0xFF
    for i in range(8):
        bit = crc & 0x80
        crc = (crc << 1) & 0xFF
        if bit:
            crc ^= 0x07
    return crc ^ 0x02


async def read_frame(reader: asyncio.StreamReader) -> bytes | None:
    """Read exactly one frame from a bursty TCP stream.

    The stream can contain back-to-back frames (often `...7e7e...`). This
    implementation buffers bytes and resyncs if it encounters implausible
    lengths or missing end flags.
    """
    MIN_LEN = 5
    MAX_LEN = 0x80

    if not hasattr(read_frame, "_buf"):
        read_frame._buf = bytearray()  # type: ignore[attr-defined]
    buf: bytearray = read_frame._buf  # type: ignore[attr-defined]

    while True:
        if len(buf) < 2:
            chunk = await reader.read(256)
            if not chunk:
                return None
            buf.extend(chunk)

        start_idx = buf.find(bytes([M_STARTEND]))
        if start_idx == -1:
            buf.clear()
            continue
        if start_idx > 0:
            del buf[:start_idx]

        if len(buf) < 2:
            continue

        rlen = buf[1]
        if rlen == M_STARTEND:
            # boundary case
            del buf[0]
            continue
        if rlen < MIN_LEN or rlen > MAX_LEN:
            del buf[0]
            continue

        total = 2 + rlen
        if len(buf) < total:
            chunk = await reader.read(256)
            if not chunk:
                return None
            buf.extend(chunk)
            continue

        frame = bytes(buf[:total])
        if frame[-1] != M_STARTEND:
            del buf[0]
            continue

        del buf[:total]
        return frame


def describe_frame(frame: bytes) -> str:
    # Basic sanity
    if len(frame) < 4:
        return "too short"
    if frame[0] != M_STARTEND:
        return "missing start flag"

    declared = frame[1]
    actual_rest = len(frame) - 2
    end_ok = frame[-1] == M_STARTEND

    # Checksum (for typical frames: checksum is penultimate byte)
    crc_ok = None
    expected = None
    got = None
    if end_ok and len(frame) >= 6:
        got = frame[-2]
        # Compute over bytes 1..(len-3) inclusive, which is (declared - 1) bytes starting at frame[1]
        # This matches balboa.py: balboa_calc_cs(full_data[1:], rlen - 1)
        expected = balboa_calc_cs(frame[1:], declared - 1)
        crc_ok = expected == got

    # Payload type (usually frame[4])
    ptype = frame[4] if len(frame) > 4 else None

    parts = [
        f"declared_len={declared}",
        f"actual_rest={actual_rest}",
        f"end_ok={end_ok}",
    ]
    if ptype is not None:
        parts.append(f"type=0x{ptype:02X}")
    if crc_ok is not None:
        parts.append(f"crc_ok={crc_ok} (exp=0x{expected:02X} got=0x{got:02X})")

    # Flag length mismatch, which is a common root cause
    if declared != actual_rest:
        parts.append("LEN_MISMATCH")

    return " ".join(parts)


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--limit", type=int, default=0, help="stop after N frames (0 = infinite)")
    args = ap.parse_args()

    print(f"{_ts()} connecting to {args.host}:{args.port} ...")
    reader, writer = await asyncio.open_connection(args.host, args.port)
    print(f"{_ts()} connected")

    n = 0
    try:
        while True:
            frame = await read_frame(reader)
            if frame is None:
                print(f"{_ts()} EOF")
                return 0
            n += 1
            print(f"{_ts()} RX {frame.hex()}  {describe_frame(frame)}")
            if args.limit and n >= args.limit:
                return 0
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

