package com.sht0rmi.manul.registry;

import com.sht0rmi.manul.ManulMod;
import com.sht0rmi.manul.entity.ManulEntity;
import net.fabricmc.fabric.api.object.builder.v1.entity.FabricDefaultAttributeRegistry;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;

/** Регистрация типов сущностей мода. */
public final class ManulEntities {
	public static final ResourceKey<EntityType<?>> MANUL_KEY =
			ResourceKey.create(Registries.ENTITY_TYPE, ManulMod.id("manul"));

	/**
	 * Манул. Габариты подобраны под коренастое телосложение: он ниже и заметно
	 * шире обычной кошки (0.8 × 0.7 против 0.6 × 0.7 у кота).
	 */
	public static final EntityType<ManulEntity> MANUL = Registry.register(
			BuiltInRegistries.ENTITY_TYPE,
			MANUL_KEY,
			EntityType.Builder.of(ManulEntity::new, MobCategory.CREATURE)
					.sized(0.8F, 0.7F)
					.eyeHeight(0.55F)
					.clientTrackingRange(8)
					.build(MANUL_KEY)
	);

	private ManulEntities() {
	}

	public static void register() {
		FabricDefaultAttributeRegistry.register(MANUL, ManulEntity.createAttributes());
	}
}
