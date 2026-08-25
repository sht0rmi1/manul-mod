package com.sht0rmi.manul.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.sht0rmi.manul.ManulMod;
import com.sht0rmi.manul.entity.ManulEntity;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.MobRenderer;
import net.minecraft.resources.Identifier;

/**
 * Рендер манула. Сетка одна на все возрасты, котёнок — она же, уменьшенная в
 * {@link #scale}. Отдельный детский слой через {@code BabyModelTransform} не
 * годится: он сдвигает готовые позы, и позы с абсолютной высотой части (сидит,
 * шипит) от этого отрываются от лап.
 */
public class ManulRenderer extends MobRenderer<ManulEntity, ManulRenderState, ManulModel> {
	private static final Identifier TEXTURE = ManulMod.id("textures/entity/manul.png");
	/** Рыжий окрас: та же развёртка, перекрашенная генератором. */
	private static final Identifier TEXTURE_GINGER = ManulMod.id("textures/entity/manul_ginger.png");

	public ManulRenderer(EntityRendererProvider.Context context) {
		super(context, new ManulModel(context.bakeLayer(ManulModelLayers.MANUL)), 0.4F);
	}

	@Override
	public ManulRenderState createRenderState() {
		return new ManulRenderState();
	}

	@Override
	public void extractRenderState(ManulEntity manul, ManulRenderState state, float partialTick) {
		super.extractRenderState(manul, state, partialTick);
		state.isHissing = manul.isHissing();
		state.isSitting = manul.isInSittingPose();
		state.idleTime = manul.tickCount + partialTick;
		state.isGinger = manul.isGinger();
	}

	/**
	 * Котёнок — половина взрослого. {@code ageScale} — тот же множитель, каким игра
	 * уменьшает хитбокс и тень, поэтому всё сходится само.
	 */
	@Override
	protected void scale(ManulRenderState state, PoseStack poseStack) {
		poseStack.scale(state.ageScale, state.ageScale, state.ageScale);
	}

	@Override
	public Identifier getTextureLocation(ManulRenderState state) {
		return state.isGinger ? TEXTURE_GINGER : TEXTURE;
	}
}
