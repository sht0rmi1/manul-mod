package com.sht0rmi.manul.registry;

import com.sht0rmi.manul.ManulMod;
import net.fabricmc.fabric.api.itemgroup.v1.ItemGroupEvents;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.SpawnEggItem;

/** Предметы мода. */
public final class ManulItems {
	/** Вкладка «Яйца призыва» — ключ приватный в {@code CreativeModeTabs}, поэтому собираем его сами. */
	private static final ResourceKey<CreativeModeTab> SPAWN_EGGS_TAB =
			ResourceKey.create(Registries.CREATIVE_MODE_TAB, ResourceLocation.withDefaultNamespace("spawn_eggs"));

	/** Вкладка «Инструменты и утилиты» — сюда встаёт чесалка, рядом с ванильной кистью. */
	private static final ResourceKey<CreativeModeTab> TOOLS_TAB =
			ResourceKey.create(Registries.CREATIVE_MODE_TAB, ResourceLocation.withDefaultNamespace("tools_and_utilities"));

	public static final ResourceKey<Item> MANUL_SPAWN_EGG_KEY =
			ResourceKey.create(Registries.ITEM, ManulMod.id("manul_spawn_egg"));

	/**
	 * Яйцо призыва манула. В 1.21.4 тип сущности ещё передаётся прямо в конструктор
	 * (в 1.21.5 его перенесли в компонент {@code entity_data}).
	 */
	public static final Item MANUL_SPAWN_EGG = Registry.register(
			BuiltInRegistries.ITEM,
			MANUL_SPAWN_EGG_KEY,
			new SpawnEggItem(ManulEntities.MANUL, new Item.Properties().setId(MANUL_SPAWN_EGG_KEY))
	);

	public static final ResourceKey<Item> MANUL_SCRATCHER_KEY =
			ResourceKey.create(Registries.ITEM, ManulMod.id("manul_scratcher"));

	/**
	 * Чесалка — палка с ворсом. Единственное её назначение: чесать манула
	 * (см. {@code ManulEntity#scratch}). Не стакается и изнашивается, 96 чесаний.
	 */
	public static final Item MANUL_SCRATCHER = Registry.register(
			BuiltInRegistries.ITEM,
			MANUL_SCRATCHER_KEY,
			new Item(new Item.Properties()
					.setId(MANUL_SCRATCHER_KEY)
					.stacksTo(1)
					.durability(96))
	);

	private ManulItems() {
	}

	public static void register() {
		// Ставим рядом с оцелотом — соседство по духу.
		ItemGroupEvents.modifyEntriesEvent(SPAWN_EGGS_TAB).register(
				entries -> entries.addAfter(Items.OCELOT_SPAWN_EGG, MANUL_SPAWN_EGG));
		ItemGroupEvents.modifyEntriesEvent(TOOLS_TAB).register(
				entries -> entries.addAfter(Items.BRUSH, MANUL_SCRATCHER));
	}
}
