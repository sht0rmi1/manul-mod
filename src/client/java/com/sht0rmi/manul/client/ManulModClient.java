package com.sht0rmi.manul.client;

import com.sht0rmi.manul.client.render.ManulModel;
import com.sht0rmi.manul.client.render.ManulModelLayers;
import com.sht0rmi.manul.client.render.ManulRenderer;
import com.sht0rmi.manul.registry.ManulEntities;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.rendering.v1.EntityRendererRegistry;
import net.fabricmc.fabric.api.client.rendering.v1.ModelLayerRegistry;

/** Клиентская точка входа: модели и рендер. */
public class ManulModClient implements ClientModInitializer {
	@Override
	public void onInitializeClient() {
		ModelLayerRegistry.registerModelLayer(ManulModelLayers.MANUL, ManulModel::createBodyLayer);
		EntityRendererRegistry.register(ManulEntities.MANUL, ManulRenderer::new);
	}
}
