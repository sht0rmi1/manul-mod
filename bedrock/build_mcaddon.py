#!/usr/bin/env python3
"""Сборка бедрок-аддона: проверка паков и упаковка в один .mcaddon.

Запуск:
    python bedrock/build_mcaddon.py            # проверить и собрать
    python bedrock/build_mcaddon.py --check    # только проверить

.mcaddon — это обычный zip с двумя папками внутри (поведение и ресурсы).
Minecraft: Bedrock Edition открывает такой файл двойным щелчком и сам
раскладывает паки по своим папкам.
"""

from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BP = ROOT / "manul_bp"
RP = ROOT / "manul_rp"
VERSION = "1.0.9"

errors: list[str] = []


def fail(message: str) -> None:
    errors.append(message)


def load_json(path: Path) -> dict:
    """Читает JSON строго: свои файлы держим без комментариев, в отличие от ванильных."""
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        fail(f"{path.relative_to(ROOT)}: некорректный JSON — {exc}")
        return {}


def check_manifests() -> None:
    uuids: dict[str, Path] = {}
    for pack in (BP, RP):
        data = load_json(pack / "manifest.json")
        if not data:
            continue
        header = data.get("header", {})
        found = [header.get("uuid")] + [m.get("uuid") for m in data.get("modules", [])]
        for uuid in found:
            if not uuid:
                fail(f"{pack.name}/manifest.json: пустой uuid")
            elif uuid in uuids:
                fail(f"{pack.name}/manifest.json: uuid {uuid} уже занят {uuids[uuid].name}")
            else:
                uuids[uuid] = pack
    deps = load_json(BP / "manifest.json").get("dependencies", [])
    rp_header = load_json(RP / "manifest.json").get("header", {}).get("uuid")
    if rp_header and rp_header not in [d.get("uuid") for d in deps]:
        fail("manul_bp/manifest.json: в dependencies нет uuid пака ресурсов")


def check_entity_groups() -> None:
    data = load_json(BP / "entities" / "manul.json").get("minecraft:entity", {})
    groups = set(data.get("component_groups", {}))
    referenced: set[str] = set()

    def walk(node) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "component_groups":
                    referenced.update(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data.get("events", {}))
    for name in sorted(referenced - groups):
        fail(f"manul_bp/entities/manul.json: событие ссылается на группу {name}, которой нет")
    for name in sorted(groups - referenced):
        fail(f"manul_bp/entities/manul.json: группа {name} никем не добавляется")


def check_entity_events() -> None:
    """Каждое событие, на которое кто-то ссылается, должно быть описано.

    Опечатка в `time_down_event` или в триггере датчика нигде не даёт ошибки —
    событие просто не срабатывает, и зверь, например, навсегда остаётся в позе
    шипения с нулевой скоростью.
    """
    data = load_json(BP / "entities" / "manul.json").get("minecraft:entity", {})
    declared = set(data.get("events", {}))
    called: dict[str, str] = {}

    def walk(node, where: str) -> None:
        if isinstance(node, dict):
            name = node.get("event")
            if isinstance(name, str):
                called.setdefault(name, where)
            for key, value in node.items():
                walk(value, key if isinstance(key, str) else where)
        elif isinstance(node, list):
            for item in node:
                walk(item, where)

    walk(data.get("components", {}), "components")
    walk(data.get("component_groups", {}), "component_groups")
    walk(data.get("events", {}), "events")

    for name, where in sorted(called.items()):
        # События с префиксом minecraft: движок понимает и без нашего описания.
        if name.startswith("minecraft:") or name in declared:
            continue
        fail(f"manul_bp/entities/manul.json: {where} зовёт событие «{name}», которого нет в events")


def check_bp_animations() -> None:
    """Анимации пака поведения: ими манул подаёт голос через /playsound.

    Это server-side анимации (документация «Entity Timeline Events»): в
    `description.animations` они объявляются, в `scripts.animate` включаются, а в
    `timeline` и `on_entry` стоят слэш-команды. Опечатка в имени звука нигде не
    даёт ошибки — зверь просто молчит, поэтому ключи /playsound сверяются с
    sound_definitions.json.
    """
    desc = load_json(BP / "entities" / "manul.json").get("minecraft:entity", {}).get("description", {})
    declared = desc.get("animations", {})

    own_anims: set[str] = set()
    for path in (BP / "animations").rglob("*.json"):
        own_anims.update(load_json(path).get("animations", {}))
    own_controllers: dict[str, dict] = {}
    for path in (BP / "animation_controllers").rglob("*.json"):
        own_controllers.update(load_json(path).get("animation_controllers", {}))

    for short, ident in declared.items():
        if ident.startswith("controller.") and ident not in own_controllers:
            fail(f"manul_bp: контроллера {ident} нет (короткое имя «{short}»)")
        elif ident.startswith("animation.") and ident not in own_anims:
            fail(f"manul_bp: анимации {ident} нет (короткое имя «{short}»)")

    for short in desc.get("scripts", {}).get("animate", []):
        name = short if isinstance(short, str) else next(iter(short))
        if name not in declared:
            fail(f"manul_bp: scripts.animate включает «{name}», которого нет в description.animations")

    defs = load_json(RP / "sounds" / "sound_definitions.json").get("sound_definitions", {})
    commands: list[tuple[str, str]] = []

    for path in (BP / "animations").rglob("*.json"):
        for name, anim in load_json(path).get("animations", {}).items():
            for time, entry in anim.get("timeline", {}).items():
                for line in [entry] if isinstance(entry, str) else entry:
                    commands.append((f"{name} @ {time}", line))

    for name, controller in own_controllers.items():
        states = controller.get("states", {})
        initial = controller.get("initial_state", "default")
        if initial not in states:
            fail(f"manul_bp/{name}: initial_state «{initial}» не описан")
        for state_name, state in states.items():
            for target in state.get("transitions", []):
                for to_state in target:
                    if to_state not in states:
                        fail(f"manul_bp/{name}/{state_name}: переход в неизвестное состояние «{to_state}»")
            for anim in state.get("animations", []):
                short = anim if isinstance(anim, str) else next(iter(anim))
                if short not in declared:
                    fail(f"manul_bp/{name}/{state_name}: играет «{short}», которого нет в description.animations")
            for key in ("on_entry", "on_exit"):
                for line in state.get(key, []):
                    commands.append((f"{name}/{state_name} {key}", line))

    for where, line in commands:
        if not line.startswith("/"):
            continue
        parts = line.split()
        if parts[0] != "/playsound":
            continue
        if len(parts) < 2:
            fail(f"manul_bp/{where}: у /playsound нет имени звука")
        elif parts[1] not in defs:
            fail(f"manul_bp/{where}: /playsound зовёт «{parts[1]}», которого нет в sound_definitions.json")


def check_format_landmines() -> None:
    """Ищет компоненты, которые ломаются при подъёме format_version сущности.

    Сверено с документацией обновлений 1.26.0-1.26.40 и с ванильными cat.json
    и wolf.json (format_version 1.26.50). Сам файл сущности сейчас объявлен как
    1.21.0, и по документации такие файлы продолжают работать на 26.x — но если
    когда-нибудь поднять версию, эти места отвалятся молча.
    """
    entity_path = BP / "entities" / "manul.json"
    data = load_json(entity_path)
    entity = data.get("minecraft:entity", {})
    if not entity:
        return

    raw = entity_path.read_text(encoding="utf-8")
    version = tuple(int(part) for part in data.get("format_version", "0").split("."))

    # Компонент -> (с какой format_version файла он перестаёт разбираться, чем заменён)
    removed_at = {
        "minecraft:pushable": (
            (1, 26, 10),
            "разделён на minecraft:pushable_by_block и minecraft:pushable_by_entity "
            "(второй доступен с format_version 1.26.30)",
        ),
    }
    for name, (since, replacement) in removed_at.items():
        if f'"{name}"' not in raw:
            continue
        if version >= since:
            fail(
                f"{entity_path.relative_to(ROOT)}: {name} не разбирается при "
                f"format_version {'.'.join(map(str, since))} и выше — {replacement}"
            )

    # Компонент -> (обязательная пара, зачем)
    required_pairs = {
        "minecraft:breedable": (
            "minecraft:offspring",
            "с 1.26.0 потомство описывает minecraft:offspring, без него котёнок не рождается",
        ),
    }
    groups = dict(entity.get("component_groups", {}))
    groups["<components>"] = entity.get("components", {})
    for group_name, group in groups.items():
        for name, (partner, why) in required_pairs.items():
            if name in group and partner not in group:
                fail(
                    f"{entity_path.relative_to(ROOT)}: в группе {group_name} есть "
                    f"{name}, но нет {partner} — {why}"
                )


def check_client_entity() -> None:
    """Текстуры, геометрия, анимации и контроллеры должны существовать."""
    desc = load_json(RP / "entity" / "manul.entity.json").get("minecraft:client_entity", {}).get("description", {})

    for name, path in desc.get("textures", {}).items():
        if not (RP / f"{path}.png").exists():
            fail(f"manul_rp: текстуры {path}.png нет, а она указана как «{name}»")

    geo_ids = set()
    for path in (RP / "models").rglob("*.json"):
        for entry in load_json(path).get("minecraft:geometry", []):
            geo_ids.add(entry.get("description", {}).get("identifier"))
    for name, ident in desc.get("geometry", {}).items():
        if ident not in geo_ids:
            fail(f"manul_rp: геометрии {ident} нет (нужна для «{name}»)")

    own_anims: set[str] = set()
    for path in (RP / "animations").rglob("*.json"):
        own_anims.update(load_json(path).get("animations", {}))
    own_controllers: set[str] = set()
    for path in (RP / "animation_controllers").rglob("*.json"):
        own_controllers.update(load_json(path).get("animation_controllers", {}))

    known = own_anims | own_controllers
    for short, ident in desc.get("animations", {}).items():
        # animation.common.* и controller.* из ванили можно использовать, их не проверяем.
        if ident.startswith("animation.manul.") and ident not in known:
            fail(f"manul_rp: анимации {ident} нет (короткое имя «{short}»)")
    for entry in desc.get("animation_controllers", []):
        for short, ident in entry.items():
            if ident.startswith("controller.animation.manul.") and ident not in known:
                fail(f"manul_rp: контроллера {ident} нет (короткое имя «{short}»)")

    shorts = set(desc.get("animations", {}))
    for entry in desc.get("scripts", {}).get("animate", []):
        names = [entry] if isinstance(entry, str) else list(entry)
        for name in names:
            if name not in shorts:
                fail(f"manul_rp: scripts.animate ссылается на «{name}», которого нет в animations")

    own_renderers: set[str] = set()
    for path in (RP / "render_controllers").rglob("*.json"):
        own_renderers.update(load_json(path).get("render_controllers", {}))
    for ident in desc.get("render_controllers", []):
        name = ident if isinstance(ident, str) else next(iter(ident))
        if name.startswith("controller.render.manul") and name not in own_renderers:
            fail(f"manul_rp: рендер-контроллера {name} нет")

    egg = desc.get("spawn_egg", {}).get("texture")
    if egg:
        # Своя иконка яйца: имя должно быть в item_texture.json, а файл — на диске.
        data = load_json(RP / "textures" / "item_texture.json").get("texture_data", {})
        if egg not in data:
            fail(f"manul_rp/textures/item_texture.json: нет записи «{egg}» для иконки яйца")
        else:
            texture = data[egg].get("textures", "")
            if not (RP / f"{texture}.png").exists():
                fail(f"manul_rp: для иконки яйца нет файла {texture}.png")


def check_animation_bones() -> None:
    """Кости в анимациях и контроллерах должны быть в геометрии."""
    bones: set[str] = set()
    for path in (RP / "models").rglob("*.json"):
        for entry in load_json(path).get("minecraft:geometry", []):
            bones.update(bone.get("name") for bone in entry.get("bones", []))

    for path in (RP / "animations").rglob("*.json"):
        for anim_name, anim in load_json(path).get("animations", {}).items():
            for bone in anim.get("bones", {}):
                if bone not in bones:
                    fail(f"{anim_name}: кости {bone} нет в геометрии")

    controller_states: set[str] = set()
    used_anims: set[str] = set()
    for path in (RP / "animation_controllers").rglob("*.json"):
        for name, controller in load_json(path).get("animation_controllers", {}).items():
            states = controller.get("states", {})
            initial = controller.get("initial_state", "default")
            if initial not in states:
                fail(f"{name}: initial_state «{initial}» не описан")
            for state_name, state in states.items():
                controller_states.add(state_name)
                for target in state.get("transitions", []):
                    for to_state in target:
                        if to_state not in states:
                            fail(f"{name}/{state_name}: переход в неизвестное состояние «{to_state}»")
                for anim in state.get("animations", []):
                    used_anims.add(anim if isinstance(anim, str) else next(iter(anim)))

    shorts = set(
        load_json(RP / "entity" / "manul.entity.json")
        .get("minecraft:client_entity", {})
        .get("description", {})
        .get("animations", {})
    )
    for anim in sorted(used_anims - shorts):
        fail(f"контроллер играет «{anim}», а в animations пака такого имени нет")


def check_sounds() -> None:
    """Звук в Bedrock идёт двумя разными путями, и их легко перепутать.

    1. `sound_effects` в анимации: движок сам склеивает ключ «mob.<моб>.<effect>»
       и ищет его в sound_definitions.json. Сверено с ванилью: 15 эффектов из 17
       у camel, breeze, sniffer и warden находятся ровно по этому правилу
       (mob.breeze.whirl, mob.sniffer.sniffsniff, mob.warden.clicking…), причём в
       entity_sounds таких имён нет вообще.
    2. События движка (ambient, hurt, death): их движок переводит через
       sounds.json → entity_sounds → sound_definitions.

    Пропущенное звено нигде не даёт ошибки — зверь просто молчит.
    """
    defs = load_json(RP / "sounds" / "sound_definitions.json").get("sound_definitions", {})
    entities = load_json(RP / "sounds.json").get("entity_sounds", {}).get("entities", {})
    identifier = (
        load_json(RP / "entity" / "manul.entity.json")
        .get("minecraft:client_entity", {})
        .get("description", {})
        .get("identifier", "")
    )
    short = identifier.split(":")[-1]

    if identifier not in entities:
        fail(f"manul_rp/sounds.json: нет записи entity_sounds для «{identifier}»")
    events = entities.get(identifier, {}).get("events", {})
    # Второй ключ без пространства имён — подстраховка: у ванильных записей его нет.
    if short in entities and entities[short].get("events") != events:
        fail(f"manul_rp/sounds.json: записи «{identifier}» и «{short}» разошлись")

    # ambient, hurt и death играет сама игра; без них зверь молчит, получает урон
    # и умирает беззвучно, сколько бы анимаций ему ни добавить.
    for required in ("ambient", "hurt", "death"):
        if required not in events:
            fail(f"manul_rp/sounds.json: нет события «{required}»")

    used: set[str] = set()
    for name, value in events.items():
        key = value["sound"] if isinstance(value, dict) else value
        used.add(key)
        if key not in defs:
            fail(f"manul_rp/sounds.json: событие «{name}» зовёт звук «{key}», которого нет в sound_definitions.json")

    for path in (RP / "animations").rglob("*.json"):
        for anim_name, anim in load_json(path).get("animations", {}).items():
            for time, event in anim.get("sound_effects", {}).items():
                effect = event.get("effect")
                key = f"mob.{short}.{effect}"
                alias = f"mob.{identifier}.{effect}"
                used.update((key, alias))
                if key not in defs:
                    fail(f"{anim_name} @ {time}: эффект «{effect}» ищется как «{key}», а его нет в sound_definitions.json")
                # Дубль с полным идентификатором держим на случай, если движок не
                # обрезает пространство имён у своих сущностей. Разойтись они не должны.
                if alias in defs and defs[alias].get("sounds") != defs.get(key, {}).get("sounds"):
                    fail(f"sound_definitions.json: «{key}» и «{alias}» звучат по-разному")

    for key in sorted(set(defs) - used):
        fail(f"sound_definitions.json: «{key}» не зовёт ни одно событие и ни один эффект анимации")

    bp_entity = (RP.parent / "manul_bp" / "entities" / "manul.json").read_text(encoding="utf-8")
    for key in re.findall(r'"on_damage_sound_event"\s*:\s*"([^"]+)"', bp_entity):
        if key not in defs:
            fail(f"manul_bp/entities/manul.json: звука «{key}» нет в sound_definitions.json")

    for key, entry in defs.items():
        for sound in entry.get("sounds", []):
            name = sound["name"] if isinstance(sound, dict) else sound
            if name.startswith("sounds/mob/manul/") and not (RP / f"{name}.ogg").exists():
                fail(f"sound_definitions.json: для «{key}» нет файла {name}.ogg")


def lang_keys(pack: Path) -> dict[str, set[str]]:
    """Ключи переводов по каждому языку пака."""
    result: dict[str, set[str]] = {}
    for lang in load_json(pack / "texts" / "languages.json"):
        path = pack / "texts" / f"{lang}.lang"
        if not path.exists():
            continue
        result[lang] = {
            line.split("=", 1)[0].strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if "=" in line and not line.startswith("#")
        }
    return result


def check_items() -> None:
    """Свой предмет собран из четырёх файлов, и любой пропуск молчит.

    Без записи в item_texture.json иконка становится розово-чёрным квадратом,
    без ключа в .lang в подсказке видно сам ключ, а без рецепта предмет вообще
    никак не получить, кроме /give. Ошибок в лог игры при этом не попадает.
    """
    langs = lang_keys(RP)
    atlas = load_json(RP / "textures" / "item_texture.json").get("texture_data", {})
    items: dict[str, dict] = {}

    for path in sorted((BP / "items").rglob("*.json")):
        data = load_json(path).get("minecraft:item", {})
        where = path.relative_to(ROOT)
        ident = data.get("description", {}).get("identifier", "")
        if not ident.startswith("manul:"):
            fail(f"{where}: identifier «{ident}» без своего пространства имён")
            continue
        items[ident] = data
        components = data.get("components", {})

        icon = components.get("minecraft:icon", {})
        # До 1.21.100 иконка объявлялась как {"texture": "имя"}, позже — как
        # {"textures": {"default": "имя"}}. Файл написан по старой схеме, но
        # проверяем обе, чтобы проверка не отстала от него.
        name = icon.get("texture") or icon.get("textures", {}).get("default")
        if not name:
            fail(f"{where}: у предмета нет minecraft:icon")
        elif name not in atlas:
            fail(f"manul_rp/textures/item_texture.json: нет записи «{name}» для иконки предмета {ident}")
        elif not (RP / f"{atlas[name].get('textures', '')}.png").exists():
            fail(f"manul_rp: для иконки «{name}» нет файла {atlas[name].get('textures')}.png")

        key = components.get("minecraft:display_name", {}).get("value", f"item.{ident}")
        for lang, keys in langs.items():
            if key not in keys:
                fail(f"manul_rp/texts/{lang}.lang: нет имени предмета «{key}»")

    results: set[str] = set()
    for path in sorted((BP / "recipes").rglob("*.json")):
        data = load_json(path)
        where = path.relative_to(ROOT)
        for kind, recipe in data.items():
            if not kind.startswith("minecraft:recipe"):
                continue
            result = recipe.get("result", {})
            result = result[0] if isinstance(result, list) else result
            made = result.get("item", "") if isinstance(result, dict) else str(result)
            results.add(made)
            if made.startswith("manul:") and made not in items:
                fail(f"{where}: рецепт делает «{made}», а такого предмета в manul_bp/items нет")
            for slot, ingredient in recipe.get("key", {}).items():
                item = ingredient.get("item", "") if isinstance(ingredient, dict) else str(ingredient)
                if item.startswith("manul:") and item not in items:
                    fail(f"{where}: в ячейке «{slot}» предмет «{item}», которого нет в manul_bp/items")
            for row in recipe.get("pattern", []):
                for slot in row.replace(" ", ""):
                    if slot not in recipe.get("key", {}):
                        fail(f"{where}: в pattern есть «{slot}», а в key его нет")

    for ident in sorted(set(items) - results):
        fail(f"manul_bp/items: предмет {ident} ниоткуда не крафтится")

    # Ссылки на предметы и подсказки из карточки сущности.
    entity = load_json(BP / "entities" / "manul.json").get("minecraft:entity", {})
    raw = (BP / "entities" / "manul.json").read_text(encoding="utf-8")
    for value in re.findall(r'"value"\s*:\s*"(manul:[^"]+)"', raw):
        if value not in items and value != entity.get("description", {}).get("identifier"):
            fail(f"manul_bp/entities/manul.json: ссылка на «{value}», которого нет ни среди предметов, ни как сущность")
    for key in re.findall(r'"interact_text"\s*:\s*"([^"]+)"', raw):
        # Ванильные подсказки (action.interact.*) переведены самой игрой; свои — нет.
        if key.startswith("action.interact.manul"):
            for lang, keys in langs.items():
                if key not in keys:
                    fail(f"manul_rp/texts/{lang}.lang: нет подсказки «{key}»")


def check_texts() -> None:
    for pack in (BP, RP):
        languages = load_json(pack / "texts" / "languages.json")
        for lang in languages:
            path = pack / "texts" / f"{lang}.lang"
            if not path.exists():
                fail(f"{pack.name}: нет файла переводов {lang}.lang")
                continue
            keys = {
                line.split("=", 1)[0].strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if "=" in line and not line.startswith("#")
            }
            for required in ("pack.name", "pack.description"):
                if required not in keys:
                    fail(f"{pack.name}/texts/{lang}.lang: нет ключа {required}")


def check_json_syntax() -> None:
    for path in sorted(ROOT.rglob("*.json")):
        if "dist" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"^\s*//", text, re.MULTILINE):
            fail(f"{path.relative_to(ROOT)}: комментарии // ломают строгий JSON")
        load_json(path)


def write_zip(target: Path, pairs: list[tuple[Path, str]]) -> None:
    """Пишет zip с явными записями папок.

    Явные папки нужны не всем импортёрам, но iOS к архивам придирчив, а стоят они
    несколько байт.
    """
    folders: set[str] = set()
    for _, name in pairs:
        parts = name.split("/")[:-1]
        for i in range(1, len(parts) + 1):
            folders.add("/".join(parts[:i]) + "/")
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for folder in sorted(folders):
            archive.writestr(folder, b"")
        for path, name in pairs:
            archive.write(path, name)


def build() -> list[Path]:
    """Собирает три файла: один .mcaddon и по одному .mcpack на каждый пак.

    .mcaddon — два пака в одном файле, папки лежат верхним уровнем архива. Это
    удобно на Windows и Android, но на iOS импорт .mcaddon часто не срабатывает
    вообще. Поэтому рядом кладутся .mcpack: в каждом ровно один пак, и manifest.json
    лежит **в корне архива**, а не в папке — этого требует формат .mcpack.
    """
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    targets: list[Path] = []

    addon = dist / f"manul-{VERSION}.mcaddon"
    pairs = [
        (path, path.relative_to(ROOT).as_posix())
        for pack in (BP, RP)
        for path in sorted(pack.rglob("*"))
        if path.is_file()
    ]
    write_zip(addon, pairs)
    targets.append(addon)

    for pack, suffix in ((BP, "behavior"), (RP, "resources")):
        target = dist / f"manul-{suffix}-{VERSION}.mcpack"
        write_zip(
            target,
            [
                (path, path.relative_to(pack).as_posix())
                for path in sorted(pack.rglob("*"))
                if path.is_file()
            ],
        )
        targets.append(target)

    return targets


def main() -> int:
    check_json_syntax()
    check_manifests()
    check_entity_groups()
    check_entity_events()
    check_format_landmines()
    check_client_entity()
    check_bp_animations()
    check_animation_bones()
    check_sounds()
    check_items()
    check_texts()

    if errors:
        print("Проверка не прошла:")
        for message in errors:
            print(f"  - {message}")
        return 1

    print("Проверка пройдена: JSON корректен, ссылки на файлы и кости на месте.")
    if "--check" in sys.argv:
        return 0

    for target in build():
        size = target.stat().st_size / 1024
        print(f"Собрано: {target.relative_to(ROOT.parent)} ({size:.0f} КиБ)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
