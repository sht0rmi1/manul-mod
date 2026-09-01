package com.sht0rmi.manul.client.render;

import net.minecraft.client.model.EntityModel;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.model.geom.PartPose;
import net.minecraft.client.model.geom.builders.CubeListBuilder;
import net.minecraft.client.model.geom.builders.LayerDefinition;
import net.minecraft.client.model.geom.builders.MeshDefinition;
import net.minecraft.client.model.geom.builders.PartDefinition;
import net.minecraft.util.Mth;

/**
 * Модель манула: своя геометрия, а не ванильная кошка. Приземистое тело 9 × 7 × 13
 * на лапах в 3 пикселя, «юбка» вокруг низа вместо длинной шерсти, крупная плоская
 * голова 9 × 6 × 6 без шеи, воротник по бокам головы, крошечные уши и толстый
 * хвост из двух звеньев с чёрным кончиком.
 *
 * <p>Земля в модели — y = 24, темя на 13,5, то есть 10,5 пикселя при хитбоксе 0,7.
 * Детской сетки нет: котёнок — эта же модель, уменьшенная в
 * {@link ManulRenderer#scale}, плюс голова покрупнее в {@link #setupAnim}.
 *
 * <p>Развёртка 128 × 64 расписана вручную: куб (w, h, d) при texOffs(u, v) занимает
 * 2*(d+w) × (d+h). Те же размеры стоят в <code>tools/gen_textures.py</code>, так что
 * геометрию и текстуру правят вместе.
 */
public class ManulModel extends EntityModel<ManulRenderState> {
	private static final float BODY_Y = 14.0F;
	private static final float HEAD_Y = 16.5F;
	private static final float HEAD_Z = -5.5F;
	private static final float LEG_Y = 21.0F;

	/** Во сколько раз голова котёнка крупнее взрослой относительно тела. */
	private static final float BABY_HEAD_SCALE = 1.35F;

	private final ModelPart body;
	private final ModelPart head;
	private final ModelPart tail;
	private final ModelPart tailTip;
	private final ModelPart leftEar;
	private final ModelPart rightEar;
	private final ModelPart frontLeftLeg;
	private final ModelPart frontRightLeg;
	private final ModelPart hindLeftLeg;
	private final ModelPart hindRightLeg;

	public ManulModel(ModelPart root) {
		super(root);
		this.body = root.getChild("body");
		this.head = root.getChild("head");
		this.tail = this.body.getChild("tail");
		this.tailTip = this.tail.getChild("tail_tip");
		this.leftEar = this.head.getChild("left_ear");
		this.rightEar = this.head.getChild("right_ear");
		this.frontLeftLeg = root.getChild("front_left_leg");
		this.frontRightLeg = root.getChild("front_right_leg");
		this.hindLeftLeg = root.getChild("hind_left_leg");
		this.hindRightLeg = root.getChild("hind_right_leg");
	}

	public static LayerDefinition createBodyLayer() {
		MeshDefinition mesh = new MeshDefinition();
		PartDefinition root = mesh.getRoot();

		// --- тело -------------------------------------------------------------
		// Низкий длинный «валик»: 13 в длину при 7 в высоту. Опорная точка на
		// верхней грани, поэтому наклоны тела в позах считаются от линии спины.
		PartDefinition body = root.addOrReplaceChild("body",
				CubeListBuilder.create()
						.texOffs(0, 0)
						.addBox(-4.5F, 0.0F, -6.5F, 9.0F, 7.0F, 13.0F),
				PartPose.offset(0.0F, BODY_Y, 0.0F));

		// Свисающая шерсть: на пиксель шире и длиннее тела с каждой стороны,
		// поэтому ни одна грань не совпадает с гранью тела и мерцания не будет.
		body.addOrReplaceChild("skirt",
				CubeListBuilder.create()
						.texOffs(0, 20)
						.addBox(-5.0F, 0.0F, -7.0F, 10.0F, 4.0F, 14.0F),
				PartPose.offset(0.0F, 4.0F, 0.0F));

		// --- хвост ------------------------------------------------------------
		// Толстый: 4 × 4 при теле в 9 — примерно как на фотографии.
		PartDefinition tail = body.addOrReplaceChild("tail",
				CubeListBuilder.create()
						.texOffs(48, 12)
						.addBox(-2.0F, -2.0F, 0.0F, 4.0F, 4.0F, 8.0F),
				PartPose.offsetAndRotation(0.0F, 2.5F, 6.5F, 0.55F, 0.0F, 0.0F));

		// Второе звено доламывает хвост вниз — кончик замирает у самой земли.
		tail.addOrReplaceChild("tail_tip",
				CubeListBuilder.create()
						.texOffs(72, 12)
						.addBox(-2.0F, -2.0F, 0.0F, 4.0F, 4.0F, 4.0F),
				PartPose.offsetAndRotation(0.0F, 0.0F, 8.0F, 0.35F, 0.0F, 0.0F));

		// --- голова -----------------------------------------------------------
		// Шире тела (9 против 9 по ширине, но при высоте всего 6) — от этого она
		// читается крупной и плоской. Опорная точка в центре: так поворот взгляда
		// не «вырывает» голову из тела.
		PartDefinition head = root.addOrReplaceChild("head",
				CubeListBuilder.create()
						.texOffs(48, 0)
						.addBox(-4.5F, -3.0F, -6.0F, 9.0F, 6.0F, 6.0F),
				PartPose.offset(0.0F, HEAD_Y, HEAD_Z));

		// Морда короткая, широкая и посажена низко — вровень с подбородком.
		head.addOrReplaceChild("muzzle",
				CubeListBuilder.create()
						.texOffs(106, 0)
						.addBox(-2.0F, 0.0F, -2.0F, 4.0F, 3.0F, 2.0F),
				PartPose.offset(0.0F, 0.0F, -6.0F));

		// Воротник: развал наружу нижним краем — от этого морда кажется плоской.
		head.addOrReplaceChild("left_cheek",
				CubeListBuilder.create()
						.texOffs(78, 0)
						.addBox(0.0F, -2.5F, 0.0F, 2.0F, 5.0F, 5.0F),
				PartPose.offsetAndRotation(4.5F, 0.0F, -5.5F, 0.0F, 0.0F, -0.14F));
		head.addOrReplaceChild("right_cheek",
				CubeListBuilder.create()
						.texOffs(92, 0)
						.addBox(-2.0F, -2.5F, 0.0F, 2.0F, 5.0F, 5.0F),
				PartPose.offsetAndRotation(-4.5F, 0.0F, -5.5F, 0.0F, 0.0F, 0.14F));

		// Уши сидят у самых краёв головы, завалены наружу и выступают над черепом
		// всего на пиксель.
		head.addOrReplaceChild("left_ear",
				CubeListBuilder.create()
						.texOffs(106, 6)
						.addBox(-1.5F, -2.0F, -0.5F, 3.0F, 2.0F, 1.0F),
				PartPose.offsetAndRotation(4.5F, -2.0F, -2.5F, 0.0F, 0.0F, 0.45F));
		head.addOrReplaceChild("right_ear",
				CubeListBuilder.create()
						.texOffs(106, 10)
						.addBox(-1.5F, -2.0F, -0.5F, 3.0F, 2.0F, 1.0F),
				PartPose.offsetAndRotation(-4.5F, -2.0F, -2.5F, 0.0F, 0.0F, -0.45F));

		// --- лапы -------------------------------------------------------------
		// Одна развёртка на все четыре: они одинаковы. В плюсе по x — левая сторона
		// зверя, как принято в ванильных моделях. Ступни ровно на земле: 21 + 3 = 24.
		CubeListBuilder leg = CubeListBuilder.create()
				.texOffs(88, 12)
				.addBox(-1.5F, 0.0F, -1.5F, 3.0F, 3.0F, 3.0F);
		root.addOrReplaceChild("front_left_leg", leg, PartPose.offset(2.5F, LEG_Y, -4.5F));
		root.addOrReplaceChild("front_right_leg", leg, PartPose.offset(-2.5F, LEG_Y, -4.5F));
		root.addOrReplaceChild("hind_left_leg", leg, PartPose.offset(2.5F, LEG_Y, 4.5F));
		root.addOrReplaceChild("hind_right_leg", leg, PartPose.offset(-2.5F, LEG_Y, 4.5F));

		return LayerDefinition.create(mesh, 128, 64);
	}

	@Override
	public void setupAnim(ManulRenderState state) {
		super.setupAnim(state);  // сбрасывает позу к исходной

		// Котёнок: голова крупнее относительно тела. Уши, воротник и морда — дети
		// головы, поэтому подтягиваются вместе с ней. Само уменьшение зверя делает
		// рендер, а не сетка.
		if (state.isBaby) {
			this.head.xScale = BABY_HEAD_SCALE;
			this.head.yScale = BABY_HEAD_SCALE;
			this.head.zScale = BABY_HEAD_SCALE;
		}

		// Взгляд.
		this.head.xRot = state.xRot * Mth.DEG_TO_RAD;
		this.head.yRot = state.yRot * Mth.DEG_TO_RAD;

		// Шаг: у манула он короткий и частый, поэтому фаза быстрая, а размах
		// небольшой — лапы всё равно почти скрыты шерстью.
		float phase = state.walkAnimationPos * 1.3F;
		float amount = Math.min(state.walkAnimationSpeed, 1.0F) * 0.9F;
		this.frontLeftLeg.xRot = Mth.cos(phase) * amount;
		this.frontRightLeg.xRot = Mth.cos(phase + Mth.PI) * amount;
		this.hindLeftLeg.xRot = Mth.cos(phase + Mth.PI) * amount;
		this.hindRightLeg.xRot = Mth.cos(phase) * amount;

		// Покачивание хвоста на месте; кончик отстаёт по фазе, из-за этого
		// хвост «течёт», а не болтается как палка.
		float idle = state.idleTime;
		this.tail.yRot = Mth.sin(idle * 0.07F) * 0.15F;
		this.tail.xRot = 0.55F + Mth.sin(idle * 0.05F) * 0.08F;
		this.tailTip.yRot = Mth.sin(idle * 0.07F - 0.9F) * 0.2F;
		this.tailTip.xRot = 0.35F + Mth.sin(idle * 0.05F - 0.9F) * 0.1F;

		if (state.isSitting) {
			this.applySittingPose();
		}

		if (state.isHissing) {
			this.applyHissingPose(idle);
		}

		// Чешут. Поза идёт поверх остальных и всегда через размах, поэтому
		// подмешивается и к стоячему зверю, и к сидячему, ничего не ломая.
		if (state.isScratched) {
			this.applyScratchPose(idle, scratchAmount(state.scratchProgress));
		}
	}

	/**
	 * Размах позы чесания по доле прошедшего времени: быстро набирается
	 * и плавно гаснет. Без этого на первом и последнем кадре зверь
	 * дёргался бы в позу и из позы рывком.
	 */
	private static float scratchAmount(float progress) {
		return Math.min(1.0F, progress * 8.0F) * Math.min(1.0F, (1.0F - progress) * 4.0F);
	}

	/**
	 * Сидит: зад опущен на землю, передние лапы прямые, грудь и морда подняты.
	 * Положительный xRot опускает нос, поэтому «сесть» — это отрицательный поворот
	 * тела. Передние лапы не двигаются: ступни и так на земле, а просвет под
	 * поднявшейся грудью закрывает «юбка».
	 */
	private void applySittingPose() {
		this.body.y = BODY_Y + 2.0F;
		this.body.xRot = -0.35F;

		this.head.y = HEAD_Y + 0.5F;
		this.head.z = HEAD_Z - 0.5F;

		this.frontLeftLeg.xRot = 0.0F;
		this.frontRightLeg.xRot = 0.0F;

		// Задние лапы сложены и убраны вперёд под тело.
		this.hindLeftLeg.xRot = -1.4F;
		this.hindRightLeg.xRot = -1.4F;
		this.hindLeftLeg.y = LEG_Y + 2.0F;
		this.hindRightLeg.y = LEG_Y + 2.0F;
		this.hindLeftLeg.z = 5.5F;
		this.hindRightLeg.z = 5.5F;

		// Хвост обёрнут вбок вдоль тела.
		this.tail.xRot = 0.15F;
		this.tail.yRot = 0.7F;
		this.tailTip.xRot = 0.1F;
		this.tailTip.yRot = 0.5F;
	}

	/** Шипит: припал к земле, уши плашмя, хвост низко и дрожит. */
	private void applyHissingPose(float idle) {
		this.body.y = BODY_Y + 1.0F;
		this.body.xRot = 0.1F;   // нос вниз, загривок горбом

		this.head.y = HEAD_Y + 0.5F;
		this.head.xRot += 0.2F;

		// Прижатые уши — куда сильнее, чем развал в покое.
		this.leftEar.zRot = 1.25F;
		this.rightEar.zRot = -1.25F;
		this.leftEar.xRot = 0.3F;
		this.rightEar.xRot = 0.3F;

		// Лапы подобраны, зверь готов отпрыгнуть.
		this.frontLeftLeg.xRot = 0.0F;
		this.frontRightLeg.xRot = 0.0F;

		this.tail.xRot = 0.9F;
		this.tail.yRot = Mth.sin(idle * 0.9F) * 0.3F;
		this.tailTip.xRot = 0.2F;
		this.tailTip.yRot = Mth.sin(idle * 0.9F - 0.6F) * 0.4F;
	}

	/**
	 * Чешут: зверь подставляет голову под чесалку, кренится набок, уши
	 * распущены, хвост поднят трубой и подрагивает.
	 *
	 * <p>Всё считается от уже выставленной позы — углы прибавляются или
	 * смешиваются через {@code lerp}, а не присваиваются. Поэтому поза ложится
	 * и на стоячего зверя, и на сидячего, и при {@code amount} = 0 ничего не меняет.
	 */
	private void applyScratchPose(float idle, float amount) {
		// Две разные частоты: медленное «валяние» и мелкая дрожь от удовольствия,
		// иначе движение выглядит заводным.
		float lean = Mth.sin(idle * 0.5F);
		float quiver = Mth.sin(idle * 1.4F);

		// Подбородок кверху (отрицательный xRot), голова кренится набок
		// и почти отпускает взгляд игрока: манулу сейчас не до него.
		this.head.xRot += amount * (-0.32F + lean * 0.12F);
		this.head.zRot += amount * (0.3F + lean * 0.22F);
		this.head.yRot -= amount * this.head.yRot * 0.5F;
		this.head.y -= amount * 0.5F;

		// Тело подаётся навстречу и покачивается в такт голове.
		this.body.zRot += amount * lean * 0.08F;
		this.body.y += amount * 0.4F;

		// Уши распущены наружу — прямая противоположность прижатым при шипении.
		this.leftEar.zRot = Mth.lerp(amount, this.leftEar.zRot, 0.85F + quiver * 0.07F);
		this.rightEar.zRot = Mth.lerp(amount, this.rightEar.zRot, -0.85F - quiver * 0.07F);
		this.leftEar.xRot = Mth.lerp(amount, this.leftEar.xRot, -0.12F);
		this.rightEar.xRot = Mth.lerp(amount, this.rightEar.xRot, -0.12F);

		// Передние лапы переминаются, ступни при этом не отрываются.
		this.frontLeftLeg.xRot += amount * lean * 0.12F;
		this.frontRightLeg.xRot -= amount * lean * 0.12F;

		// Хвост трубой: отрицательный xRot задирает его к спине, а кончик
		// отстаёт по фазе, от чего дрожь бежит волной до самого конца.
		this.tail.xRot = Mth.lerp(amount, this.tail.xRot, -0.45F + quiver * 0.1F);
		this.tail.yRot = Mth.lerp(amount, this.tail.yRot, quiver * 0.22F);
		this.tailTip.xRot = Mth.lerp(amount, this.tailTip.xRot, -0.2F + quiver * 0.14F);
		this.tailTip.yRot = Mth.lerp(amount, this.tailTip.yRot, Mth.sin(idle * 1.4F - 0.7F) * 0.3F);
	}
}
