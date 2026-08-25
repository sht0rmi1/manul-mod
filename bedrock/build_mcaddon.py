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
VERSION = "1.0.0"

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
    """Все звуки из sound_effects должны находиться в sound_definitions."""
    defs = load_json(RP / "sounds" / "sound_definitions.json").get("sound_definitions", {})
    for path in (RP / "animations").rglob("*.json"):
        for anim_name, anim in load_json(path).get("animations", {}).items():
            for time, event in anim.get("sound_effects", {}).items():
                effect = event.get("effect")
                if f"mob.manul.{effect}" not in defs and effect not in defs:
                    fail(f"{anim_name} @ {time}: звук «{effect}» не описан в sound_definitions.json")
    for key, entry in defs.items():
        for sound in entry.get("sounds", []):
            name = sound["name"] if isinstance(sound, dict) else sound
            if name.startswith("sounds/mob/manul/") and not (RP / f"{name}.ogg").exists():
                fail(f"sound_definitions.json: для «{key}» нет файла {name}.ogg")
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


def build() -> Path:
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    target = dist / f"manul-{VERSION}.mcaddon"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for pack in (BP, RP):
            for path in sorted(pack.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(ROOT).as_posix())
    return target


def main() -> int:
    check_json_syntax()
    check_manifests()
    check_entity_groups()
    check_client_entity()
    check_animation_bones()
    check_sounds()
    check_texts()

    if errors:
        print("Проверка не прошла:")
        for message in errors:
            print(f"  - {message}")
        return 1

    print("Проверка пройдена: JSON корректен, ссылки на файлы и кости на месте.")
    if "--check" in sys.argv:
        return 0

    target = build()
    size = target.stat().st_size / 1024
    print(f"Собрано: {target.relative_to(ROOT.parent)} ({size:.0f} КиБ)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
