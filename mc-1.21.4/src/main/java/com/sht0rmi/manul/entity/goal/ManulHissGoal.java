package com.sht0rmi.manul.entity.goal;

import com.sht0rmi.manul.entity.ManulEntity;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.player.Player;

import java.util.EnumSet;

/**
 * Манул шипит.
 *
 * <p>Главная черта настоящего манула — недовольство. Пока зверь не доверяет игроку,
 * он при близком подходе замирает, прижимает уши и шипит вместо того, чтобы просто
 * убежать. Присевшего (крадущегося) игрока терпит — так у игрока появляется
 * работающая тактика приближения.
 */
public class ManulHissGoal extends Goal {
	private static final double TRIGGER_DISTANCE = 5.0D;

	private final ManulEntity manul;
	private Player target;
	private int hissTicks;

	public ManulHissGoal(ManulEntity manul) {
		this.manul = manul;
		this.setFlags(EnumSet.of(Goal.Flag.MOVE, Goal.Flag.LOOK));
	}

	@Override
	public boolean canUse() {
		if (this.manul.isTame() || this.manul.getTrust() >= ManulEntity.TRUST_CALM) {
			return false;
		}

		Player player = this.manul.level().getNearestPlayer(this.manul, TRIGGER_DISTANCE);
		if (player == null || player.isSpectator() || player.isCrouching()) {
			return false;
		}

		this.target = player;
		return this.manul.getRandom().nextInt(10) == 0;
	}

	@Override
	public boolean canContinueToUse() {
		return this.hissTicks > 0
				&& this.target != null
				&& this.target.isAlive()
				&& this.manul.distanceToSqr(this.target) < TRIGGER_DISTANCE * TRIGGER_DISTANCE * 2.0D;
	}

	@Override
	public void start() {
		this.hissTicks = 30 + this.manul.getRandom().nextInt(30);
		this.manul.setHissing(true);
		this.manul.getNavigation().stop();
		this.manul.playHissSound();
	}

	@Override
	public void tick() {
		this.hissTicks--;
		if (this.target != null) {
			this.manul.getLookControl().setLookAt(this.target, 30.0F, 30.0F);
		}
		// Иногда шипит повторно, если игрок не уходит.
		if (this.hissTicks % 20 == 0 && this.manul.getRandom().nextInt(3) == 0) {
			this.manul.playHissSound();
		}
	}

	@Override
	public void stop() {
		this.manul.setHissing(false);
		this.target = null;
	}

	@Override
	public boolean requiresUpdateEveryTick() {
		return true;
	}
}
