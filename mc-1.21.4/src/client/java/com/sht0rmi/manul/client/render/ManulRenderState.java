package com.sht0rmi.manul.client.render;

import net.minecraft.client.renderer.entity.state.LivingEntityRenderState;

/**
 * Снимок состояния манула для рендера.
 *
 * <p>С 1.21.2 рендер не имеет доступа к сущности напрямую: всё нужное переносится
 * в такой объект на этапе extract. Здесь — то, что влияет на позу и на текстуру.
 */
public class ManulRenderState extends LivingEntityRenderState {
	/** Шипит: уши прижаты, голова опущена, спина сгорблена. */
	public boolean isHissing;
	/** Сидит (по приказу или греется на солнце). */
	public boolean isSitting;
	/** Непрерывное время для «дышащих» покачиваний, в тиках. */
	public float idleTime;
	/** Рыжий окрас — от него зависит только выбор текстуры. */
	public boolean isGinger;
	/** Идёт чесание: зверь тянется к чесалке, уши распущены, хвост трубой. */
	public boolean isScratched;
	/** Доля пройденной анимации чесания, 0…1: из неё считается размах позы. */
	public float scratchProgress;
}
