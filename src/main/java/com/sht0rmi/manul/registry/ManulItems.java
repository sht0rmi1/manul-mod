package com.sht0rmi.manul.registry;

import com.sht0rmi.manul.ManulMod;
import net.fabricmc.fabric.api.creativetab.v1.CreativeModeTabEvents;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.core.component.DataComponents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.SpawnEggItem;
import net.minecraft.world.item.component.TypedEntityData;

/** Предметы мода. */
public final class ManulItems {
	/** Вкладка «Яйца призыва» — ключ приватный в {@code CreativeModeTabs}, поэтому собираем его сами. */
	private static final ResourceKey<CreativeModeTab> SPAWN_EGGS_TAB =
			ResourceKey.create(Registries.CREATIVE_MODE_TAB, Identifier.withDefaultNamespace("spawn_eggs"));

	/** Вкладка «Инструменты и утилиты» — сюда встаёт чесалка, рядом с ванильной кистью. */
	private static final ResourceKey<CreativeModeTab> TOOLS_TAB =
			ResourceKey.create(Registries.CREATIVE_MODE_TAB, Identifier.withDefaultNamespace("tools_and_utilities"));

	public static final ResourceKey<Item> MANUL_SPAWN_EGG_KEY =
			ResourceKey.create(Registries.ITEM, ManulMod.id("manul_spawn_egg"));

	/**
	 * Яйцо призыва манула. С 1.21.5 тип сущности больше не передаётся в конструктор —
	 * он живёт в компоненте {@code entity_data}.
	 */
	public static final Item MANUL_SPAWN_EGG = Registry.register(
			BuiltInRegistries.ITEM,
			MANUL_SPAWN_EGG_KEY,
			new SpawnEggItem(new Item.Properties()
					.setId(MANUL_SPAWN_EGG_KEY)
					.component(DataComponents.ENTITY_DATA,
							TypedEntityData.<EntityType<?>>of(ManulEntities.MANUL, new CompoundTag())))
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
		CreativeModeTabEvents.modifyOutputEvent(SPAWN_EGGS_TAB).register(
				output -> output.insertAfter(Items.OCELOT_SPAWN_EGG, MANUL_SPAWN_EGG));
		CreativeModeTabEvents.modifyOutputEvent(TOOLS_TAB).register(
				output -> output.insertAfter(Items.BRUSH, MANUL_SCRATCHER));
	}
}
