package com.sht0rmi.manul;

import com.sht0rmi.manul.registry.ManulEntities;
import com.sht0rmi.manul.registry.ManulItems;
import com.sht0rmi.manul.registry.ManulSounds;
import com.sht0rmi.manul.world.ManulSpawns;
import net.fabricmc.api.ModInitializer;
import net.minecraft.resources.ResourceLocation;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Точка входа мода «Манулы».
 *
 * <p>Мод добавляет манула (Otocolobus manul) — небольшую пушистую кошку каменистых
 * степей и заснеженных холмов. Манул дикий и недоверчивый: он убегает от игрока,
 * шипит, охотится на кроликов и греется на солнце. Приручить его можно только
 * терпением — постепенно скармливая ему сырое мясо и рыбу.
 */
public class ManulMod implements ModInitializer {
	public static final String MOD_ID = "manul";
	public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

	@Override
	public void onInitialize() {
		ManulSounds.register();
		ManulEntities.register();
		ManulItems.register();
		ManulSpawns.register();
		LOGGER.info("Манулы загружены — не гладь, он не разрешал");
	}

	/** Идентификатор в пространстве имён мода. */
	public static ResourceLocation id(String path) {
		return ResourceLocation.fromNamespaceAndPath(MOD_ID, path);
	}
}
