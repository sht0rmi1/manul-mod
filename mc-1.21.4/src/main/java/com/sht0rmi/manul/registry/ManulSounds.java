package com.sht0rmi.manul.registry;

import com.sht0rmi.manul.ManulMod;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvent;

/**
 * Свои звуковые события манула. Пока есть только запись голоса, она и стоит на
 * ambient; шипение, урчание, урон и смерть берутся из ванильных (см.
 * {@code ManulEntity}) — событие без файла регистрировать нельзя, клиент будет
 * ругаться в лог при каждой попытке его проиграть.
 *
 * <p>Добавить свой звук: моно OGG в {@code assets/manul/sounds/}, поле здесь,
 * событие в {@code sounds.json}, субтитр в локализацию.
 */
public final class ManulSounds {
	/** Зов манула — низкий протяжный крик, звучит примерно раз в 13 секунд. */
	public static final SoundEvent MANUL_AMBIENT = register("entity.manul.ambient");

	private ManulSounds() {
	}

	private static SoundEvent register(String path) {
		ResourceLocation id = ManulMod.id(path);
		return Registry.register(BuiltInRegistries.SOUND_EVENT, id, SoundEvent.createVariableRangeEvent(id));
	}

	/**
	 * Регистрация происходит в статических полях выше — этот вызов лишь гарантирует,
	 * что класс будет загружен до заморозки реестров.
	 */
	public static void register() {
		ManulMod.LOGGER.debug("Звуки манула зарегистрированы, первый — {}", MANUL_AMBIENT.location());
	}
}
