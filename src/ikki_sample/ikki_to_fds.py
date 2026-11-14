#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ikki_to_fds.py  -  いっき (ファミコン カセット版) を ディスクシステム (.fds) に変換する

使い方:
    python3 ikki_to_fds.py --bios disksys.rom  Ikki.nes  [-o Ikki_FDS.fds]

  * --bios (FDS BIOS) は必須です。ディスクのライセンス画面データ(KYODAKU-)を
    BIOS の中から取り出すために使います。
  * BIOS の版は問いません (標準版 / ツインファミコン版 など)。
    ファイルの形式の違い(8192 バイト / iNES ヘッダー付き / 16KB 2 回分)は自動で吸収し、
    ライセンスデータの位置は BIOS の中から探します。
    見つからない・壊れている場合は変換せずに終了します。
  * 標準ライブラリだけで動きます (Python 3.6+)。

何をしているか:
  1. BIOS を読み込んで、ライセンス画面データ(224 バイト)を探す
  2. 入力 ROM が「いっき(日本版)」の想定どおりか確認する
       (NROM-128 / PRG 16KB / CHR 8KB / 垂直ミラーリング /
        ベクタ NMI=$83FF RESET=$8000 IRQ=$8472 / 修正箇所のバイト列)
  3. $0100〜$0103 への書き込み 4 箇所を $0130〜$0133 へ付け替える
       (FDS BIOS は $0100/$0101 を NMI/IRQ の振り分けに使うため、
        ゲームがそこへ書き込むと NMI が止まって固まる)
  4. FDS ディスク(片面)を組み立てる
       KYODAKU- : ライセンス画面 (BIOS から取得, PPU $2800)
       IKKI-CHR : キャラクタ 8KB (PPU $0000)
       IKKI-PRG : プログラム 16KB ($8000)  ← 手順 3 の修正済み
       IKKI-RST : 起動用の小さなプログラム ($6000)
       VECTORS- : NMI/RESET/IRQ ベクタ ($DFF6〜$DFFF)

オプション:
  --license-offset 0xNNNN : BIOS 内のライセンスデータの位置を手動で指定する
                            (自動検出できない特殊な BIOS 用)
  --strict-bios           : NMI/IRQ の振り分け処理が標準と違う BIOS を拒否する
"""

import argparse
import hashlib
import struct
import sys

# --- BIOS ----------------------------------------------------------------------
BIOS_SIZE = 8192
BIOS_BASE = 0xE000                        # BIOS は CPU の $E000〜$FFFF に見える
# 登録済みの BIOS (参考表示用。ここに無い版でも、中身が合えば変換できる)
KNOWN_BIOS_MD5 = {"ca30b50f880eb660a320674ed365ef7a": "標準 FDS BIOS (disksys.rom)"}

LICENSE_SIZE = 224                         # 32 タイル x 7 行
# 標準のライセンス画面データの SHA-256 (中身そのものは持たず、照合にだけ使う)
LICENSE_SHA256 = "0ff60f81f193b001ecccc6a280cddba4b99830755aa658c089d566046adfb034"
# BIOS 内部のフォントコードで書かれた語句 (中身の確認用)
def _font(s):
    return bytes(0x24 if c == " " else int(c, 36) for c in s)   # 0-9, A-Z は 0x00〜0x23, 空白は 0x24

PH_NINTENDO = _font("NINTENDO")
PH_FAMICOM = _font("FAMILY COMPUTER")
PH_THIS = _font("THIS PRODUCT IS MANUFACTURED")
PH_LICENSE = _font("LICENSE")
BIOS_REVERSED_MAGIC = b"*CVH-ODNETNIN*"    # 標準 BIOS 内には逆順で入っている

# NMI/IRQ の振り分け処理 (標準 BIOS)。$0100/$0101 の値で飛び先が決まる
NMI_PATTERN = bytes.fromhex("2c0001100850036cfadf6cf8df50036cf6df")
IRQ_HEAD = bytes.fromhex("2c0101301e500b")
IRQ_TAIL = bytes.fromhex("50036cfedf")

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

_TAIL_MARK = bytes([0x04, 0x05, 0x06])   # ディスク末尾の識別用


class ConvertError(Exception):
    pass


def normalize_bios(raw):
    """いろいろな形式の BIOS ダンプを 8192 バイトに揃える。"""
    n = len(raw)
    if n == BIOS_SIZE:
        return raw, "8192 バイト"
    if n == BIOS_SIZE + 16 and raw[:4] == b"NES\x1a":
        return raw[16:], "iNES ヘッダー付き (ヘッダーを除去)"
    if n == BIOS_SIZE * 2 and raw[:BIOS_SIZE] == raw[BIOS_SIZE:]:
        return raw[:BIOS_SIZE], "16KB (同じ内容が 2 回) (前半を使用)"
    raise ConvertError(
        "BIOS のサイズが想定外です: %d バイト\n"
        "  対応する形式: 8192 バイト / iNES ヘッダー付き(8208) / 同じ内容 2 回分(16384)" % n)


def _all_find(data, pat):
    i = data.find(pat)
    while i >= 0:
        yield i
        i = data.find(pat, i + 1)


def find_license_by_hash(bios):
    """標準のライセンスデータと完全に一致する場所を探す。"""
    want = LICENSE_SHA256
    for off in range(0, len(bios) - LICENSE_SIZE + 1):
        if bios[off] != 0x24:                 # 標準データは必ず 0x24 (空白) から始まる
            continue
        if hashlib.sha256(bios[off:off + LICENSE_SIZE]).hexdigest() == want:
            return off
    return None


def _valid_license_window(bios, s):
    if s < 0 or s + LICENSE_SIZE > len(bios):
        return False
    w = bios[s:s + LICENSE_SIZE]
    if max(w) > 0x2F:                         # フォントコードだけで出来ているはず
        return False
    if w.find(PH_NINTENDO) not in range(0, 32):
        return False
    f = w.find(PH_FAMICOM)
    if not 32 <= f < 64:
        return False
    t = w.find(PH_THIS)
    if not 96 <= t < 128:
        return False
    l = w.find(PH_LICENSE)
    if not 192 <= l < 224:
        return False
    return all(b == 0x24 for b in w[64:96])   # 3 行目は空白行


def find_license_by_text(bios):
    """文字(語句)の並びと行の位置関係から、ライセンスデータの場所を推定する。"""
    cands = set()
    for p in _all_find(bios, PH_NINTENDO):
        for row in range(0, 7):
            for col in range(0, 32):
                s = p - row * 32 - col
                if _valid_license_window(bios, s):
                    cands.add(s)
    if not cands:
        return None
    clean = [s for s in sorted(cands) if s == 0 or bios[s - 1] > 0x2F]   # 前の 1 バイトが別物
    return (clean or sorted(cands))[0]


def check_dispatch(bios):
    """NMI/IRQ の振り分け処理が標準と同じか確認し、違うときの警告を返す。"""
    warns = []
    nmi, _rst, irq = struct.unpack("<3H", bios[0x1FFA:0x2000])

    def at(addr, n):
        o = addr - BIOS_BASE
        return bios[o:o + n] if 0 <= o <= len(bios) - n else b""

    if at(nmi, len(NMI_PATTERN)) != NMI_PATTERN:
        warns.append("NMI の振り分け処理が標準と違います (NMI ベクタ $%04X)" % nmi)
    h = at(irq, 48)
    if not (h.startswith(IRQ_HEAD) and IRQ_TAIL in h):
        warns.append("IRQ の振り分け処理が標準と違います (IRQ ベクタ $%04X)" % irq)
    return warns


def load_bios(path, forced_offset=None):
    """BIOS を読み込んで検証し、(ライセンスデータ, 情報の辞書) を返す。"""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as e:
        raise ConvertError("BIOS を開けません: %s (%s)" % (path, e))

    bios, form = normalize_bios(raw)
    md5 = hashlib.md5(bios).hexdigest()

    how = None
    if forced_offset is not None:
        off = forced_offset
        if not 0 <= off <= len(bios) - LICENSE_SIZE:
            raise ConvertError("--license-offset が BIOS の範囲外です: 0x%X" % off)
        how = "手動指定"
    else:
        off = find_license_by_hash(bios)
        how = "標準データと一致"
        if off is None:
            off = find_license_by_text(bios)
            how = "文字の並びから推定 (標準データとは内容が異なります)"
    if off is None:
        raise ConvertError(
            "BIOS の中にライセンス画面データが見つかりません。\n"
            "  FDS の BIOS (disksys.rom など) ではないか、壊れている可能性があります。\n"
            "  位置が分かる場合は --license-offset 0xNNNN で指定できます。")

    lic = bios[off:off + LICENSE_SIZE]
    if forced_offset is None and PH_NINTENDO not in lic:
        raise ConvertError("取り出したデータがライセンス画面ではありません。")

    info = {
        "md5": md5,
        "name": KNOWN_BIOS_MD5.get(md5, "未登録の版"),
        "form": form,
        "offset": off,
        "how": how,
        "magic": BIOS_REVERSED_MAGIC in bios,
        "warnings": check_dispatch(bios),
    }
    return lic, info


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
    side += _TAIL_MARK            # 最後のファイル(VECTORS-)の直後。ファイル数には含めない
    if len(side) > 65500:
        raise ConvertError("ディスクの容量を超えました。")
    side = bytes(side).ljust(65500, b"\0")
    return b"FDS\x1a\x01" + bytes(11) + side


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="いっき(ファミコン版 .nes) を ディスクシステム(.fds) に変換します。FDS BIOS が必須です。")
    ap.add_argument("rom", help="いっき(日本版)の .nes ファイル")
    ap.add_argument("--bios", required=True,
                    help="FDS BIOS (標準版 / ツインファミコン版 など) ※必須")
    ap.add_argument("-o", "--output", help="出力ファイル名 (省略時は ROM 名 + _FDS.fds)")
    ap.add_argument("--mirroring", choices=["header", "vertical", "horizontal"], default="header",
                    help="ミラーリング (既定: ROM ヘッダーに従う。いっきは垂直)")
    ap.add_argument("--license-offset", type=lambda x: int(x, 0), default=None, metavar="0xNNNN",
                    help="BIOS 内のライセンスデータの位置を手動で指定する")
    ap.add_argument("--strict-bios", action="store_true",
                    help="NMI/IRQ の振り分け処理が標準と違う BIOS を拒否する")
    args = ap.parse_args(argv)

    try:
        license_data, bi = load_bios(args.bios, args.license_offset)
        if args.strict_bios and bi["warnings"]:
            raise ConvertError("--strict-bios: " + " / ".join(bi["warnings"]))
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

    print("BIOS      : %s" % args.bios)
    print("            MD5 %s  [%s]  形式: %s" % (bi["md5"], bi["name"], bi["form"]))
    print("            ライセンスデータ: 位置 0x%04X (%s)" % (bi["offset"], bi["how"]))
    for w in bi["warnings"]:
        print("  警告    : %s" % w, file=sys.stderr)
    if bi["warnings"]:
        print("            ※ このディスクは、この BIOS では動作確認できていません。"
              "起動しない場合は標準の BIOS をお試しください。", file=sys.stderr)
    if not bi["magic"]:
        print("  注意    : BIOS 内に標準の識別文字列がありません (別版の可能性)", file=sys.stderr)
    print("ROM       : %s" % args.rom)
    print("ミラーリング: %s" % ("垂直" if vertical else "水平"))
    print("修正箇所  : %d 箇所 ($0100〜$0103 の書き込みを $0130〜$0133 へ付け替え)" % len(IKKI_PATCHES))
    print("出力      : %s (%d バイト)" % (out, len(disk)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
