package com.sht0rmi.manul.world;

import com.sht0rmi.manul.registry.ManulEntities;
import net.fabricmc.fabric.api.biome.v1.BiomeModifications;
import net.fabricmc.fabric.api.biome.v1.BiomeSelectors;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.level.biome.Biomes;

/**
 * Естественный спавн манула.
 *
 * <p>В природе манул живёт в холодных каменистых степях Центральной Азии, поэтому
 * в игре он появляется в заснеженных равнинах, на склонах и в каменистых пиках,
 * на альпийских лугах и в продуваемых холмах — плюс немного в саванновом плато
 * как аналог сухой степи. Группы маленькие (1–2): манул — одиночка.
 */
public final class ManulSpawns {
	private ManulSpawns() {
	}

	public static void register() {
		BiomeModifications.addSpawn(
				BiomeSelectors.includeByKey(
						Biomes.SNOWY_PLAINS,
						Biomes.SNOWY_SLOPES,
						Biomes.GROVE,
						Biomes.MEADOW,
						Biomes.WINDSWEPT_HILLS,
						Biomes.STONY_PEAKS,
						Biomes.SAVANNA_PLATEAU),
				MobCategory.CREATURE,
				ManulEntities.MANUL,
				8,  // вес — реже кроликов (10), чтобы встреча оставалась событием
				1,
				2);
	}
}
