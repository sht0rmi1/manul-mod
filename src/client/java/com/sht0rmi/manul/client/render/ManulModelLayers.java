package com.sht0rmi.manul.client.render;

import com.sht0rmi.manul.ManulMod;
import net.minecraft.client.model.geom.ModelLayerLocation;

/**
 * Слои моделей мода.
 *
 * <p>Детского слоя нет намеренно: котёнок — та же сетка, уменьшенная в
 * {@link ManulRenderer#scale}.
 */
public final class ManulModelLayers {
	public static final ModelLayerLocation MANUL =
			new ModelLayerLocation(ManulMod.id("manul"), "main");

	private ManulModelLayers() {
	}
}
