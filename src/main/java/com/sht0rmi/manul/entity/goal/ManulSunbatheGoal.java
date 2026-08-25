package com.sht0rmi.manul.entity.goal;

import com.sht0rmi.manul.entity.ManulEntity;
import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.level.Level;

import java.util.EnumSet;

/**
 * Манул греется на солнце.
 *
 * <p>Настоящие манулы значительную часть дня просто лежат на камнях под солнцем.
 * Здесь это отдельная цель: днём, под открытым небом и без дождя манул садится
 * и подолгу сидит, изредка урча. Осёдланная поза даёт заметный и узнаваемый
 * «характер» мобу, не требуя сложной анимации.
 */
public class ManulSunbatheGoal extends Goal {
	private final ManulEntity manul;
	private int sitTicks;
	private int cooldown;

	public ManulSunbatheGoal(ManulEntity manul) {
		this.manul = manul;
		this.setFlags(EnumSet.of(Goal.Flag.MOVE, Goal.Flag.JUMP));
	}

	@Override
	public boolean canUse() {
		if (this.cooldown > 0) {
			this.cooldown--;
			return false;
		}

		Level level = this.manul.level();
		if (!level.isBrightOutside() || level.isRaining()) {
			return false;
		}
		if (this.manul.isInWater() || this.manul.isOrderedToSit() || this.manul.getTarget() != null) {
			return false;
		}
		if (this.manul.isHissing() || this.manul.isBaby()) {
			return false;  // котята слишком заняты
		}

		BlockPos pos = this.manul.blockPosition();
		if (!level.canSeeSky(pos)) {
			return false;
		}

		return this.manul.getRandom().nextInt(120) == 0;
	}

	@Override
	public boolean canContinueToUse() {
		Level level = this.manul.level();
		return this.sitTicks > 0
				&& level.isBrightOutside()
				&& !level.isRaining()
				&& !this.manul.isHissing()
				&& this.manul.getTarget() == null;
	}

	@Override
	public void start() {
		this.sitTicks = 200 + this.manul.getRandom().nextInt(400);
		this.manul.getNavigation().stop();
		this.manul.setInSittingPose(true);
	}

	@Override
	public void tick() {
		this.sitTicks--;
		if (this.sitTicks % 80 == 0 && this.manul.isTame()) {
			this.manul.playPurrSound();
		}
	}

	@Override
	public void stop() {
		this.manul.setInSittingPose(false);
		this.cooldown = 600 + this.manul.getRandom().nextInt(600);
	}

	@Override
	public boolean requiresUpdateEveryTick() {
		return true;
	}
}
