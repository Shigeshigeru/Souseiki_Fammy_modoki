#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ikki_to_fds.py  -  いっき (ファミコン カセット版) を ディスクシステム (.fds) に変換する

使い方:
    python3 ikki_to_fds.py --bios disksys.rom  Ikki.nes  [-o Ikki_FDS.fds]

  * --bios (FDS BIOS, 8192 バイト, "disksys.rom") は必須です。
    ディスクのライセンス画面データ(KYODAKU-)を BIOS から取り出すために使います。
    BIOS が無い / 壊れている / 想定外のバージョンのときは変換せずに終了します。
  * 標準ライブラリだけで動きます (Python 3.6+)。

何をしているか:
  1. 入力 ROM が「いっき(日本版)」の想定どおりか確認する
       (NROM-128 / PRG 16KB / CHR 8KB / 垂直ミラーリング /
        ベクタ NMI=$83FF RESET=$8000 IRQ=$8472 / 修正箇所のバイト列)
  2. $0100〜$0103 への書き込み 4 箇所を $0130〜$0133 へ付け替える
       (FDS BIOS は $0100/$0101 を NMI/IRQ の振り分けに使うため、
        ゲームがそこへ書き込むと NMI が止まって固まる)
  3. FDS ディスク(片面)を組み立てる
       KYODAKU- : ライセンス画面 (BIOS から取得, PPU $2800)
       IKKI-CHR : キャラクタ 8KB (PPU $0000)
       IKKI-PRG : プログラム 16KB ($8000)  ← 手順 2 の修正済み
       IKKI-RST : 起動用の小さなプログラム ($6000)
       VECTORS- : NMI/RESET/IRQ ベクタ ($DFF6〜$DFFF)
"""

import argparse
import hashlib
import struct
import sys

# --- 既知の BIOS (disksys.rom) -------------------------------------------------
BIOS_SIZE = 8192
KNOWN_BIOS_MD5 = {"ca30b50f880eb660a320674ed365ef7a": "FDS BIOS (disksys.rom)"}
LICENSE_OFFSET = 0xED37 - 0xE000      # BIOS 内のライセンス画面データの位置
LICENSE_SIZE = 224
# BIOS 内部のフォントコードで "NINTENDO" (N,I,N,T,E,N,D,O)
LICENSE_TEXT = bytes([0x17, 0x12, 0x17, 0x1D, 0x0E, 0x17, 0x0D, 0x18])
BIOS_REVERSED_MAGIC = b"*CVH-ODNETNIN*"   # BIOS 内には逆順で入っている

# --- いっき ROM の想定 ---------------------------------------------------------
PRG_SIZE, CHR_SIZE = 0x4000, 0x2000
IKKI_VECTORS = (0x83FF, 0x8000, 0x8472)    # NMI, RESET, IRQ
# ($0100〜$0103 を使う書き込み, 付け替え先 +$30)
#   (ROM 内アドレス, 期待する元のバイト列, 修正後のバイト列)
IKKI_PATCHES = [
    (0xA213, bytes([0x99, 0x03, 0x01]), bytes([0x99, 0x33, 0x01])),  # STA $0103,Y -> $0133,Y
    (0xA227, bytes([0x8D, 0x01, 0x01]), bytes([0x8D, 0x31, 0x01])),  # STA $0101   -> $0131
    (0xA22D, bytes([0x8D, 0x02, 0x01]), bytes([0x8D, 0x32, 0x01])),  # STA $0102   -> $0132
    (0xA232, bytes([0x8D, 0x00, 0x01]), bytes([0x8D, 0x30, 0x01])),  # STA $0100   -> $0130
]


class ConvertError(Exception):
    pass


def load_bios(path):
    """BIOS を読み込んで検証し、ライセンス画面データ(224 バイト)を返す。"""
    try:
        with open(path, "rb") as f:
            bios = f.read()
    except OSError as e:
        raise ConvertError("BIOS を開けません: %s (%s)" % (path, e))

    if len(bios) != BIOS_SIZE:
        raise ConvertError(
            "BIOS のサイズが違います: %d バイト (8192 バイトの disksys.rom が必要です)" % len(bios))

    md5 = hashlib.md5(bios).hexdigest()
    if md5 not in KNOWN_BIOS_MD5:
        raise ConvertError(
            "未知の BIOS です (MD5 %s)。\n"
            "  ライセンス画面データの位置を確認できないため、変換を中止します。\n"
            "  標準の FDS BIOS (disksys.rom, MD5 ca30b50f880eb660a320674ed365ef7a) を指定してください。" % md5)

    if BIOS_REVERSED_MAGIC not in bios:
        raise ConvertError("BIOS 内に FDS の識別文字列が見つかりません。")

    lic = bios[LICENSE_OFFSET:LICENSE_OFFSET + LICENSE_SIZE]
    if len(lic) != LICENSE_SIZE or LICENSE_TEXT not in lic:
        raise ConvertError("BIOS からライセンス画面データを取り出せませんでした。")
    return lic, md5


def load_ikki(path):
    """いっき ROM を読み込んで検証し、(PRG, CHR, 垂直ミラーか) を返す。"""
    try:
        with open(path, "rb") as f:
            nes = f.read()
    except OSError as e:
        raise ConvertError("ROM を開けません: %s (%s)" % (path, e))

    if len(nes) < 16 or nes[:4] != b"NES\x1a":
        raise ConvertError("iNES 形式 (.nes) ではありません。")
    prg_n, chr_n, flags6, flags7 = nes[4], nes[5], nes[6], nes[7]
    mapper = (flags6 >> 4) | (flags7 & 0xF0)
    if (prg_n, chr_n, mapper) != (1, 1, 0):
        raise ConvertError(
            "想定外の構成です: PRG %d x16KB / CHR %d x8KB / マッパー %d "
            "(いっきは PRG 1 / CHR 1 / マッパー 0 です)" % (prg_n, chr_n, mapper))
    if flags6 & 0x04:
        raise ConvertError("トレーナー付きの ROM には対応していません。")

    off = 16
    prg = nes[off:off + PRG_SIZE]
    chr_ = nes[off + PRG_SIZE:off + PRG_SIZE + CHR_SIZE]
    if len(prg) != PRG_SIZE or len(chr_) != CHR_SIZE:
        raise ConvertError("ROM のサイズが足りません (壊れている可能性があります)。")

    vec = tuple(struct.unpack("<3H", prg[0x3FFA:0x4000]))
    if vec != IKKI_VECTORS:
        raise ConvertError(
            "いっき(日本版)ではないようです: ベクタ NMI/RESET/IRQ = "
            "$%04X/$%04X/$%04X (想定 $%04X/$%04X/$%04X)" % (vec + IKKI_VECTORS))
    return prg, chr_, bool(flags6 & 1)


def patch_prg(prg):
    """$0100〜$0103 への書き込みを付け替えた PRG を返す。"""
    out = bytearray(prg)
    for addr, old, new in IKKI_PATCHES:
        o = addr - 0x8000
        if bytes(out[o:o + len(old)]) != old:
            raise ConvertError(
                "修正箇所 $%04X のバイト列が想定と違います (%s)。\n"
                "  いっき(日本版)の無改造 ROM を指定してください。"
                % (addr, bytes(out[o:o + len(old)]).hex(" ")))
        out[o:o + len(new)] = new
    return bytes(out)


def make_stub(vertical):
    """ゲーム開始前に実行する小さなプログラム ($6000 に置く)。"""
    mirror = [0xA5, 0xFA, 0x29, 0x77]          # LDA $FA ; AND #$77  (disk IRQ off, bit3 clear)
    if not vertical:
        mirror += [0x09, 0x08]                 # ORA #$08            (bit3 set = horizontal)
    mirror += [0x85, 0xFA, 0x8D, 0x25, 0x40]   # STA $FA ; STA $4025
    code = (
        [0x78, 0xD8]                           # SEI ; CLD
        + [0xA9, 0x00, 0x8D, 0x00, 0x20]       # PPUCTRL = 0 (NMI off)
        + [0xA9, 0x00, 0x8D, 0x22, 0x40]       # FDS timer IRQ off
        + [0xA9, 0xC0, 0x8D, 0x00, 0x01]       # $0100 = $C0 : BIOS NMI -> ($DFFA)
        + [0xA9, 0x80, 0x8D, 0x01, 0x01]       # $0101 = $80 : BIOS IRQ 振り分け
        + mirror                               # ミラーリング設定
        + [0x4C, 0x00, 0x80]                   # JMP $8000 (ゲームのリセット)
        + [0x40]                               # RTI  (IRQ の飛び先)
    )
    return bytes(code)


def build_disk(license_data, prg, chr_, vertical):
    stub = make_stub(vertical)
    rti = 0x6000 + len(stub) - 1
    nmi = IKKI_VECTORS[0]
    vectors = struct.pack("<5H", nmi, nmi, nmi, 0x6000, rti)   # NMI x3, RESET, IRQ

    files = [                                  # (名前, 読み込み先, 種別, データ)
        ("KYODAKU-", 0x2800, 2, license_data),  # 種別 2 = ネームテーブル(PPU)
        ("IKKI-CHR", 0x0000, 1, chr_),          # 種別 1 = キャラクタ(PPU)
        ("IKKI-PRG", 0x8000, 0, prg),           # 種別 0 = プログラム(CPU)
        ("IKKI-RST", 0x6000, 0, stub),
        ("VECTORS-", 0xDFF6, 0, vectors),
    ]

    info = bytearray([1]) + b"*NINTENDO-HVC*" + bytes([0x00]) + b"IKK"
    info += bytes([0x20, 0, 0, 0, 0, 0, len(files) - 1]) + b"\xff" * 5
    info += bytes([0x86, 0x11, 0x11, 0x49, 0x61, 0, 0, 2]) + bytes(5)
    info += bytes([0x86, 0x11, 0x11]) + bytes([0, 0x80, 0, 0, 7, 0, 0, 0, 0])
    info = bytes(info).ljust(56, b"\0")

    side = bytearray(info) + bytes([2, len(files)])
    for i, (name, addr, kind, data) in enumerate(files):
        nb = name.encode("ascii")
        assert len(nb) == 8
        side += bytes([3, i, i]) + nb + struct.pack("<HHB", addr, len(data), kind)
        side += bytes([4]) + data
    if len(side) > 65500:
        raise ConvertError("ディスクの容量を超えました。")
    side = bytes(side).ljust(65500, b"\0")
    return b"FDS\x1a\x01" + bytes(11) + side


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="いっき(ファミコン版 .nes) を ディスクシステム(.fds) に変換します。FDS BIOS が必須です。")
    ap.add_argument("rom", help="いっき(日本版)の .nes ファイル")
    ap.add_argument("--bios", required=True,
                    help="FDS BIOS (disksys.rom, 8192 バイト) ※必須")
    ap.add_argument("-o", "--output", help="出力ファイル名 (省略時は ROM 名 + _FDS.fds)")
    ap.add_argument("--mirroring", choices=["header", "vertical", "horizontal"], default="header",
                    help="ミラーリング (既定: ROM ヘッダーに従う。いっきは垂直)")
    args = ap.parse_args(argv)

    try:
        license_data, md5 = load_bios(args.bios)
        prg, chr_, header_vertical = load_ikki(args.rom)
        vertical = header_vertical if args.mirroring == "header" else (args.mirroring == "vertical")
        prg = patch_prg(prg)
        disk = build_disk(license_data, prg, chr_, vertical)
    except ConvertError as e:
        print("エラー: %s" % e, file=sys.stderr)
        return 1

    out = args.output
    if not out:
        base = args.rom[:-4] if args.rom.lower().endswith(".nes") else args.rom
        out = base + "_FDS.fds"
    with open(out, "wb") as f:
        f.write(disk)

    print("BIOS      : %s (MD5 %s)" % (args.bios, md5))
    print("ROM       : %s" % args.rom)
    print("ミラーリング: %s" % ("垂直" if vertical else "水平"))
    print("修正箇所  : %d 箇所 ($0100〜$0103 の書き込みを $0130〜$0133 へ付け替え)" % len(IKKI_PATCHES))
    print("出力      : %s (%d バイト)" % (out, len(disk)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
