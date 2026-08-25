#!/usr/bin/env python3
"""Генерация текстур мода «Манулы» из кода.

Развёртка считается из тех же размеров кубов, что стоят в
ManulModel.createBodyLayer(): куб (w, h, d) при texOffs(u, v) занимает
прямоугольник 2*(d+w) x (d+h), внутри которого грани лежат так:

    верхний ряд (высота d):  [d пусто] [w ВЕРХ]  [w НИЗ]
    нижний ряд  (высота h):  [d бок]   [w ПЕРЕД] [d бок] [w ЗАД]

Класс Box отдаёт эти шесть прямоугольников по имени, так что пиксельные
смещения руками не считаются: меняешь размер куба здесь и в модели — и всё
сходится.

Куда смотрит длинная ось внутри грани, без запуска игры не проверить, поэтому
все метки либо тянутся во всю грань, либо симметричны по спорной оси: полосы,
кольца, крапины. Манулу это подходит, несимметричных пятен у него нет.

Рыжий окрас — перекраска готовой развёртки по таблице «серый цвет → рыжий»,
а не второй набор вызовов рисования.

Зависимостей нет: полотно — bytearray, PNG пишется вручную через zlib.

Запуск:  python tools/gen_textures.py
"""

from __future__ import annotations

import os
import struct
import sys
import zlib

# Отчёт скрипта — по-русски, а консоль Windows по умолчанию отдаёт cp1252 и
# падает на первой же кириллической букве. Просим UTF-8 явно.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

# ------------------------------------------------------------------ палитра ---
# Снята с фотографии живого манула.

FUR_BACK = (186, 182, 168)   # серебристо-серая спина
FUR_SIDE = (190, 168, 128)   # бок, уже с рыжинкой
OCHRE    = (170, 138, 94)    # рыжий подпал на бёдрах и плечах
BELLY    = (228, 221, 203)   # брюхо
FACE     = (224, 215, 195)   # светлая морда
RUFF     = (214, 204, 182)   # воротник
DARK     = (150, 134, 108)   # мягкая тень
MARK     = (92, 78, 62)      # чёткие метки: полосы на щеках, крапины на лбу
RING     = (120, 102, 78)    # кольца на хвосте
TIP      = (38, 34, 31)      # чёрный кончик хвоста
EYE      = (198, 190, 118)   # жёлто-зелёный глаз
PUPIL    = (28, 25, 22)
NOSE     = (86, 66, 58)
PAW      = (234, 228, 214)   # белёсые лапы
PAD      = (86, 72, 62)
EARIN    = (152, 133, 110)

# Рыжий (краснопесчаный) манул: та же светлотность, сдвинутая в тепло. Глаза
# остаются жёлто-зелёными, а кончик хвоста чёрным — это у зверя не меняется.
# В таблице обязаны быть все цвета палитры: remap() падает на неучтённом.
GINGER = {
    FUR_BACK: (198, 152, 102),
    FUR_SIDE: (200, 140, 84),
    OCHRE:    (172, 102, 54),
    BELLY:    (240, 222, 190),
    FACE:     (236, 206, 170),
    RUFF:     (226, 192, 152),
    DARK:     (148, 96, 56),
    MARK:     (98, 56, 34),
    RING:     (130, 72, 40),
    TIP:      (40, 30, 24),
    EYE:      (206, 184, 102),
    PUPIL:    (28, 24, 20),
    NOSE:     (106, 62, 50),
    PAW:      (242, 226, 198),
    PAD:      (100, 64, 48),
    EARIN:    (170, 116, 80),
}


def _hash2(x: int, y: int) -> int:
    """Хеш пары координат: узор случайный на вид, но одинаковый при каждом запуске."""
    h = (x * 0x1F1F1F1F) ^ (y * 0x8DA6B343)
    h = ((h ^ (h >> 13)) * 0x5BD1E995) & 0xFFFFFFFF
    return (h ^ (h >> 15)) & 0x7FFFFFFF

# ------------------------------------------------------------------- полотно --


class Canvas:
    """Полотно RGBA. Начальное состояние — полная прозрачность."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.stride = width * 4
        self.data = bytearray(self.stride * height)

    def rect(self, x: int, y: int, w: int, h: int, color) -> None:
        if x < 0 or y < 0 or x + w > self.width or y + h > self.height:
            raise ValueError(f"прямоугольник {x},{y} {w}x{h} вне полотна "
                             f"{self.width}x{self.height}")
        row = bytes((*color, 255)) * w
        for yy in range(y, y + h):
            off = yy * self.stride + x * 4
            self.data[off:off + 4 * w] = row

    def px(self, x: int, y: int, color) -> None:
        self.rect(x, y, 1, 1, color)

    def remap(self, mapping) -> None:
        """Перекрасить полотно по таблице «цвет → цвет».

        Каждый непрозрачный пиксель обязан оказаться в таблице: иначе новый
        цвет молча остался бы от прежней палитры, а такую ошибку на текстуре
        16 x 16 пикселей глазом не найти.
        """
        unknown = set()
        for off in range(0, len(self.data), 4):
            if self.data[off + 3] == 0:
                continue
            src = (self.data[off], self.data[off + 1], self.data[off + 2])
            dst = mapping.get(src)
            if dst is None:
                unknown.add(src)
                continue
            self.data[off:off + 3] = bytes(dst)
        if unknown:
            raise SystemExit("нет в таблице перекраски: "
                             + ", ".join(str(c) for c in sorted(unknown)))

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(_png_bytes(self.data, self.width, self.height))
        print(f"написано: {path}  ({self.width}x{self.height})")

    def save_scaled(self, path: str, scale: int, crop=None) -> None:
        """Увеличенная копия «пиксель в квадрат» — только чтобы разглядеть глазами.

        crop = (x, y, w, h) — вырезать фрагмент развёртки перед увеличением.
        """
        x0, y0, w, h = crop if crop else (0, 0, self.width, self.height)
        out_stride = w * scale * 4
        out = bytearray(out_stride * h * scale)
        for yy in range(h):
            src = self.data[(y0 + yy) * self.stride + x0 * 4:
                            (y0 + yy) * self.stride + (x0 + w) * 4]
            big = bytearray()
            for i in range(w):
                big += src[i * 4:i * 4 + 4] * scale
            for k in range(scale):
                off = (yy * scale + k) * out_stride
                out[off:off + out_stride] = big

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(_png_bytes(out, w * scale, h * scale))
        print(f"предпросмотр: {path}  ({w * scale}x{h * scale})")


def _png_bytes(data: bytes, width: int, height: int) -> bytes:
    stride = width * 4
    # Каждая строка PNG начинается с байта фильтра; 0 — «без фильтра».
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw += data[y * stride:(y + 1) * stride]

    def chunk(tag: bytes, payload: bytes) -> bytes:
        body = tag + payload
        return (struct.pack(">I", len(payload)) + body
                + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8 бит, RGBA
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


# --------------------------------------------------------------- грани куба ---


class Face:
    """Прямоугольник одной грани на развёртке."""

    def __init__(self, canvas: Canvas, x: int, y: int, w: int, h: int, name: str) -> None:
        self.c = canvas
        self.x, self.y, self.w, self.h = x, y, w, h
        self.name = name

    def fill(self, color) -> "Face":
        self.c.rect(self.x, self.y, self.w, self.h, color)
        return self

    def band(self, row: int, height: int, color) -> "Face":
        """Горизонтальная полоса во всю ширину грани."""
        self.c.rect(self.x, self.y + row, self.w, min(height, self.h - row), color)
        return self

    def rows(self, colors) -> "Face":
        """Вертикальный градиент: по цвету на строку, снизу дотягивается последним."""
        for i in range(self.h):
            self.c.rect(self.x, self.y + i, self.w, 1, colors[min(i, len(colors) - 1)])
        return self

    def bars(self, color, count: int, width: int = 1, top: int = 0, height: int = None) -> "Face":
        """`count` вертикальных полос, разнесённых по ширине симметрично."""
        height = self.h - top if height is None else height
        step = self.w / (count + 1)
        for i in range(1, count + 1):
            x = self.x + int(round(i * step)) - width // 2
            x = max(self.x, min(x, self.x + self.w - width))
            self.c.rect(x, self.y + top, width, height, color)
        return self

    def bands(self, color, count: int, height: int = 1, left: int = 0, width: int = None) -> "Face":
        """`count` горизонтальных полос, разнесённых по высоте симметрично.

        Нужны там, где длинная ось грани идёт по вертикали развёртки — на
        верхних и нижних гранях вытянутых кубов (тело, хвост). У манула
        полосы поперечные, поэтому именно так, а не через bars().
        """
        width = self.w - left if width is None else width
        step = self.h / (count + 1)
        for i in range(1, count + 1):
            y = self.y + int(round(i * step)) - height // 2
            y = max(self.y, min(y, self.y + self.h - height))
            self.c.rect(self.x + left, y, width, height, color)
        return self

    def speckle(self, color, density: int = 5, inset: int = 0) -> "Face":
        """Крапины по хешу координат: на вид случайные, но воспроизводимые."""
        for dy in range(inset, self.h - inset):
            for dx in range(inset, self.w - inset):
                if _hash2(dx, dy) % density == 0:
                    self.c.px(self.x + dx, self.y + dy, color)
        return self

    def blob(self, dx: int, dy: int, w: int, h: int, color) -> "Face":
        """Пятно в координатах самой грани."""
        self.c.rect(self.x + dx, self.y + dy, w, h, color)
        return self

    def px(self, dx: int, dy: int, color) -> "Face":
        """Один пиксель в координатах самой грани."""
        self.c.px(self.x + dx, self.y + dy, color)
        return self


class Box:
    """Куб на развёртке: (w, h, d) при texOffs(u, v). Имена — как в модели."""

    def __init__(self, canvas: Canvas, name: str, u: int, v: int, w: int, h: int, d: int) -> None:
        self.canvas, self.name = canvas, name
        self.u, self.v, self.w, self.h, self.d = u, v, w, h, d

    # Занимаемая площадь — для проверки на пересечения.
    @property
    def area(self):
        return self.u, self.v, 2 * (self.d + self.w), self.d + self.h

    def _f(self, x, y, w, h, tag):
        return Face(self.canvas, x, y, w, h, f"{self.name}.{tag}")

    @property
    def top(self):     return self._f(self.u + self.d, self.v, self.w, self.d, "верх")

    @property
    def bottom(self):  return self._f(self.u + self.d + self.w, self.v, self.w, self.d, "низ")

    @property
    def side_a(self):  return self._f(self.u, self.v + self.d, self.d, self.h, "бок A")

    @property
    def front(self):   return self._f(self.u + self.d, self.v + self.d, self.w, self.h, "перед")

    @property
    def side_b(self):  return self._f(self.u + self.d + self.w, self.v + self.d, self.d, self.h, "бок B")

    @property
    def back(self):    return self._f(self.u + 2 * self.d + self.w, self.v + self.d, self.w, self.h, "зад")

    @property
    def sides(self):   return (self.side_a, self.side_b)

    def fill(self, color) -> "Box":
        self.canvas.rect(*self.area[:2], self.area[2], self.area[3], color)
        return self


def check_layout(boxes) -> None:
    """Кубы не должны пересекаться на развёртке и вылезать за полотно."""
    for i, a in enumerate(boxes):
        ax, ay, aw, ah = a.area
        if ax + aw > a.canvas.width or ay + ah > a.canvas.height:
            raise SystemExit(f"{a.name}: развёртка {aw}x{ah} в ({ax},{ay}) не влезает "
                             f"в {a.canvas.width}x{a.canvas.height}")
        for b in boxes[i + 1:]:
            bx, by, bw, bh = b.area
            if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                raise SystemExit(f"{a.name} и {b.name} пересекаются на развёртке")
    used = sum(w * h for _, _, w, h in (b.area for b in boxes))
    total = boxes[0].canvas.width * boxes[0].canvas.height
    print(f"развёртка: {len(boxes)} кубов, занято {used} из {total} пикселей "
          f"({100 * used // total}%), пересечений нет")


# ------------------------------------------------------------ текстура зверя --


def entity_texture(path: str, recolor=None, preview_dir: str = None) -> None:
    c = Canvas(128, 64)

    # Размеры и смещения обязаны совпадать с ManulModel.createBodyLayer().
    body    = Box(c, "тело",      0,   0,   9, 7, 13)
    skirt   = Box(c, "юбка",      0,  20,  10, 4, 14)
    head    = Box(c, "голова",   48,   0,   9, 6,  6)
    tail    = Box(c, "хвост",    48,  12,   4, 4,  8)
    tailtip = Box(c, "кончик",   72,  12,   4, 4,  4)
    leg     = Box(c, "лапа",     88,  12,   3, 3,  3)
    cheek_l = Box(c, "щека L",   78,   0,   2, 5,  5)
    cheek_r = Box(c, "щека R",   92,   0,   2, 5,  5)
    muzzle  = Box(c, "морда",   106,   0,   4, 3,  2)
    ear_l   = Box(c, "ухо L",   106,   6,   3, 2,  1)
    ear_r   = Box(c, "ухо R",   106,  10,   3, 2,  1)

    boxes = [body, skirt, head, tail, tailtip, leg, cheek_l, cheek_r, muzzle, ear_l, ear_r]
    check_layout(boxes)

    # --- тело -----------------------------------------------------------------
    body.fill(FUR_SIDE)
    # Спина светло-серая, с редкой рябью и еле заметными поперечными полосами.
    # Длинная ось этой грани идёт по вертикали развёртки, поэтому bands. Крапины
    # рисуются до полос и с отступом от края: иначе шум съедает и полосы, и
    # силуэт по краям грани.
    body.top.fill(FUR_BACK).speckle(DARK, density=13, inset=1) \
            .bands(DARK, 5, height=1, left=1, width=7)
    body.bottom.fill(BELLY)
    # Бок: сверху серое, ниже рыжий подпал, у брюха светлеет. Полосы по крупу
    # мягкие (DARK, не RING) — на фотографии они еле намечены — и разнесены во
    # всю длину, поэтому рисунок не зависит от ориентации грани.
    for side in body.sides:
        side.rows([FUR_BACK, FUR_BACK, FUR_SIDE, OCHRE, OCHRE, DARK, BELLY])
        side.bars(DARK, 4, width=1, top=1, height=4)
    body.front.rows([FUR_BACK, FACE, FACE, BELLY, BELLY, BELLY, BELLY])  # грудь
    body.back.rows([FUR_BACK, FUR_SIDE, OCHRE, OCHRE, DARK, BELLY, BELLY])  # круп

    # --- юбка (свисающая шерсть) ---------------------------------------------
    skirt.fill(OCHRE)
    skirt.top.fill(FUR_SIDE)          # спрятана внутри тела
    skirt.bottom.fill(BELLY)
    for face in (*skirt.sides, skirt.front, skirt.back):
        face.rows([OCHRE, DARK, BELLY, BELLY])
    for side in skirt.sides:
        side.bars(RING, 5, width=1, top=0, height=2)

    # --- голова ---------------------------------------------------------------
    head.fill(FACE)
    # Темя серое и в редких крапинах — характерная «седая» голова.
    head.top.fill(FUR_BACK).speckle(MARK, density=9, inset=1)
    head.bottom.fill(BELLY)           # светлый подбородок
    # Виски: две тёмные полосы, идущие от глаз назад, во всю ширину грани.
    for side in head.sides:
        side.fill(FACE).band(1, 1, MARK).band(4, 1, MARK)
    head.back.fill(FUR_BACK).speckle(DARK, density=9, inset=1)

    # Лицо 9 x 6: широкое и низкое, глаза высоко и близко друг к другу, между
    # ними светлая переносица; от внутреннего угла глаза вниз тёмный потёк.
    # Всё симметрично относительно середины (x = 4).
    f = head.front
    f.rows([FUR_BACK, FACE, FACE, FACE, BELLY, BELLY])
    for x in (1, 4, 7):                            # крапины на лбу, не полоса
        f.px(x, 0, MARK)
    f.blob(1, 1, 2, 1, EYE).blob(6, 1, 2, 1, EYE)  # глаза высоко на лице
    f.px(2, 1, PUPIL)
    f.px(6, 1, PUPIL)
    f.blob(0, 1, 1, 3, MARK)                       # тёмная кромка у воротника
    f.blob(8, 1, 1, 3, MARK)
    f.blob(3, 2, 3, 4, BELLY)                      # светлая переносица к морде
    f.px(2, 2, MARK)                               # потёки от внутренних углов глаз
    f.px(6, 2, MARK)
    f.px(2, 3, MARK)
    f.px(6, 3, MARK)

    # --- морда ----------------------------------------------------------------
    muzzle.fill(BELLY)
    muzzle.top.fill(FACE)
    muzzle.front.fill(BELLY).blob(1, 0, 2, 1, NOSE).blob(1, 1, 2, 1, DARK)
    for side in muzzle.sides:
        side.fill(BELLY)

    # --- воротник -------------------------------------------------------------
    # Наружные грани (бока) — то, что видно; на них поперечные тёмные полосы.
    for cheek in (cheek_l, cheek_r):
        cheek.fill(RUFF)
        cheek.top.fill(FUR_BACK)
        cheek.bottom.fill(BELLY)
        for side in cheek.sides:
            side.fill(RUFF).band(1, 1, MARK).band(3, 1, MARK)
        cheek.front.fill(RUFF)
        cheek.back.fill(FUR_BACK)

    # --- уши ------------------------------------------------------------------
    for ear in (ear_l, ear_r):
        ear.fill(FUR_BACK)
        ear.front.fill(EARIN)         # внутренняя сторона светлее и теплее
        ear.top.fill(DARK)
        ear.back.fill(DARK)

    # --- лапы -----------------------------------------------------------------
    leg.fill(OCHRE)
    leg.top.fill(FUR_SIDE)
    leg.bottom.fill(PAD)              # подушечки
    for face in (*leg.sides, leg.front, leg.back):
        face.rows([OCHRE, PAW, PAW])  # белёсая ступня, как на фотографии

    # --- хвост ----------------------------------------------------------------
    tail.fill(FUR_SIDE)
    tail.top.fill(FUR_BACK).bands(RING, 3, height=1)
    tail.bottom.fill(BELLY).bands(RING, 3, height=1)
    for side in tail.sides:
        side.fill(FUR_SIDE).bars(RING, 3, width=1)
    tail.front.fill(FUR_SIDE)         # спрятан в крупе
    tail.back.fill(RING)

    # Кончик чёрный целиком — отдельным кубом именно ради этого.
    tailtip.fill(TIP)
    tailtip.front.fill(RING)          # стык с хвостом чуть светлее

    if recolor:
        c.remap(recolor)

    c.save(path)
    if preview_dir:
        name = os.path.splitext(os.path.basename(path))[0]
        c.save_scaled(os.path.join(preview_dir, f"{name}_uv_x8.png"), 8)
        # Голова с воротником вплотную: на 8x лицо 9x6 не разглядеть.
        c.save_scaled(os.path.join(preview_dir, f"{name}_head_x28.png"), 28,
                      crop=(48, 0, 58, 12))


# ---------------------------------------------------------- яйцо призыва ------


def spawn_egg_texture(path: str) -> None:
    c = Canvas(16, 16)

    # Силуэт яйца: (строка) -> (начало, ширина).
    rows = {
        2: (6, 4), 3: (5, 6), 4: (4, 8), 5: (4, 8),
        6: (3, 10), 7: (3, 10), 8: (3, 10), 9: (3, 10),
        10: (4, 8), 11: (4, 8), 12: (5, 6), 13: (6, 4),
    }
    for y, (x, w) in rows.items():
        c.rect(x, y, w, 1, FUR_SIDE)

    for x, y in ((5, 4), (9, 5), (4, 7), (11, 8), (6, 10), (9, 11)):
        c.rect(x, y, 2, 1, MARK)

    c.rect(5, 12, 6, 1, DARK)     # затенение низа
    c.rect(7, 2, 2, 1, BELLY)     # блик сверху

    c.save(path)


# ------------------------------------------------------------------ иконка ----


ICON_MAP = (
    "................",
    "................",
    "....ffffffff....",
    "..ffffffffffff..",
    ".ffffffffffffff.",
    "rffffllllllffffr",
    "rfffllllllllfffr",
    ".fllldlllldlllf.",
    ".fdlebellebeldf.",
    ".fdlllllllllldf.",
    ".fdlllnnnnllldf.",
    ".fdllllmmlllldf.",
    ".ffllllllllllff.",
    "..ffffffffffff..",
    "....ffffffff....",
    "................",
)

ICON_LEGEND = {
    "f": FUR_BACK, "l": FACE, "d": MARK, "e": EYE,
    "b": PUPIL, "n": BELLY, "m": NOSE, "r": DARK,
}


def icon_texture(path: str, scale: int = 8) -> None:
    if len(ICON_MAP) != 16 or any(len(row) != 16 for row in ICON_MAP):
        raise SystemExit("ICON_MAP должен быть 16 строк по 16 символов")

    c = Canvas(16 * scale, 16 * scale)
    for y, row in enumerate(ICON_MAP):
        for x, ch in enumerate(row):
            if ch in ICON_LEGEND:
                c.rect(x * scale, y * scale, scale, scale, ICON_LEGEND[ch])

    c.save(path)


# -------------------------------------------------------------------- запуск --


def main() -> int:
    assets = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "src", "main", "resources", "assets", "manul")
    # `--preview <папка>` кладёт рядом развёртку, увеличенную в 8 раз.
    preview_dir = None
    if "--preview" in sys.argv:
        preview_dir = sys.argv[sys.argv.index("--preview") + 1]

    entities = os.path.join(assets, "textures", "entity")
    entity_texture(os.path.join(entities, "manul.png"), preview_dir=preview_dir)
    entity_texture(os.path.join(entities, "manul_ginger.png"), recolor=GINGER,
                   preview_dir=preview_dir)
    spawn_egg_texture(os.path.join(assets, "textures", "item", "manul_spawn_egg.png"))
    icon_texture(os.path.join(assets, "icon.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
