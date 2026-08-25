"""Читает параметры Ogg/Vorbis-файла без внешних библиотек.

Ogg — контейнер из страниц; первый пакет Vorbis (identification header)
содержит число каналов и частоту, а granule position последней страницы —
позицию в сэмплах, то есть длительность.
"""
import struct
import sys


def pages(data):
    """Перебирает страницы Ogg: (offset, header_type, granule, segments_len)."""
    off = 0
    while True:
        idx = data.find(b"OggS", off)
        if idx < 0:
            return
        if idx + 27 > len(data):
            return
        version = data[idx + 4]
        header_type = data[idx + 5]
        granule = struct.unpack_from("<q", data, idx + 6)[0]
        seq = struct.unpack_from("<I", data, idx + 18)[0]
        nsegs = data[idx + 26]
        seg_table = data[idx + 27:idx + 27 + nsegs]
        body = sum(seg_table)
        header_len = 27 + nsegs
        yield idx, version, header_type, granule, seq, header_len, body
        off = idx + header_len + body


def main(path):
    with open(path, "rb") as fh:
        data = fh.read()

    if not data.startswith(b"OggS"):
        print("НЕ Ogg: файл не начинается с OggS")
        return 1

    plist = list(pages(data))
    print(f"размер            : {len(data)} байт")
    print(f"страниц Ogg       : {len(plist)}")

    first = plist[0]
    body_start = first[0] + first[5]
    packet = data[body_start:body_start + 30]
    if not packet.startswith(b"\x01vorbis"):
        print(f"кодек             : НЕ Vorbis (первые байты {packet[:8]!r})")
        return 1

    channels = packet[11]
    rate = struct.unpack_from("<I", packet, 12)[0]
    br_max, br_nom, br_min = struct.unpack_from("<iii", packet, 16)

    last_granule = max(p[3] for p in plist)
    eos = [p for p in plist if p[2] & 0x04]

    print("кодек             : Vorbis")
    print(f"каналов           : {channels} ({'моно' if channels == 1 else 'СТЕРЕО' if channels == 2 else '?'})")
    print(f"частота           : {rate} Гц")
    print(f"битрейт (ном.)    : {br_nom // 1000 if br_nom else 0} кбит/с")
    print(f"сэмплов           : {last_granule}")
    print(f"длительность      : {last_granule / rate:.2f} с")
    print(f"страница EOS      : {'есть' if eos else 'НЕТ (файл обрезан)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
