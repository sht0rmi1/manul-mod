package com.sht0rmi.manul.entity;

import com.sht0rmi.manul.entity.goal.ManulHissGoal;
import com.sht0rmi.manul.entity.goal.ManulSunbatheGoal;
import com.sht0rmi.manul.registry.ManulEntities;
import com.sht0rmi.manul.registry.ManulSounds;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.DifficultyInstance;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.AgeableMob;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.SpawnGroupData;
import net.minecraft.world.entity.TamableAnimal;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.AvoidEntityGoal;
import net.minecraft.world.entity.ai.goal.BreedGoal;
import net.minecraft.world.entity.ai.goal.FloatGoal;
import net.minecraft.world.entity.ai.goal.FollowOwnerGoal;
import net.minecraft.world.entity.ai.goal.LeapAtTargetGoal;
import net.minecraft.world.entity.ai.goal.LookAtPlayerGoal;
import net.minecraft.world.entity.ai.goal.MeleeAttackGoal;
import net.minecraft.world.entity.ai.goal.RandomLookAroundGoal;
import net.minecraft.world.entity.ai.goal.SitWhenOrderedToGoal;
import net.minecraft.world.entity.ai.goal.TemptGoal;
import net.minecraft.world.entity.ai.goal.WaterAvoidingRandomStrollGoal;
import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;
import net.minecraft.world.entity.ai.goal.target.OwnerHurtByTargetGoal;
import net.minecraft.world.entity.ai.goal.target.OwnerHurtTargetGoal;
import net.minecraft.world.entity.animal.Animal;
import net.minecraft.world.entity.animal.Rabbit;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelAccessor;
import net.minecraft.world.level.ServerLevelAccessor;

/**
 * Манул.
 *
 * <p>Ключевая механика — <b>доверие</b> (0…100) вместо мгновенного приручения костью.
 * Дикий манул убегает от игрока и шипит; чтобы подойти, надо крадучись (Shift).
 * Каждое скормленное лакомство добавляет доверия; после {@link #TRUST_TAME} появляется
 * шанс приручения. Удар по манулу отбрасывает доверие назад — терпение здесь и есть
 * геймплей.
 */
public class ManulEntity extends TamableAnimal {
	/** С этого доверия манул перестаёт шипеть и убегать. */
	public static final int TRUST_CALM = 30;
	/** С этого доверия возможно приручение. */
	public static final int TRUST_TAME = 70;
	public static final int TRUST_MAX = 100;

	private static final int TRUST_PER_FEED = 12;
	private static final int TRUST_LOST_ON_HIT = 25;
	private static final String TAG_TRUST = "Trust";
	private static final String TAG_GINGER = "Ginger";

	/** Один манул из восьми при естественном появлении — рыжий. */
	private static final int GINGER_SPAWN_CHANCE = 8;
	/** Один котёнок из шестнадцати меняет окрас относительно родителей. */
	private static final int GINGER_MUTATION_CHANCE = 16;

	private static final EntityDataAccessor<Integer> DATA_TRUST =
			SynchedEntityData.defineId(ManulEntity.class, EntityDataSerializers.INT);
	private static final EntityDataAccessor<Boolean> DATA_HISSING =
			SynchedEntityData.defineId(ManulEntity.class, EntityDataSerializers.BOOLEAN);
	private static final EntityDataAccessor<Boolean> DATA_GINGER =
			SynchedEntityData.defineId(ManulEntity.class, EntityDataSerializers.BOOLEAN);

	/** Создаётся в {@link #registerGoals()}; поле без инициализатора — иначе его обнулит порядок конструкторов. */
	private AvoidEntityGoal<Player> avoidPlayersGoal;

	public ManulEntity(EntityType<? extends ManulEntity> type, Level level) {
		super(type, level);
	}

	public static AttributeSupplier.Builder createAttributes() {
		return Animal.createAnimalAttributes()
				.add(Attributes.MAX_HEALTH, 10.0D)
				.add(Attributes.MOVEMENT_SPEED, 0.32D)
				.add(Attributes.ATTACK_DAMAGE, 3.0D)
				.add(Attributes.TEMPT_RANGE, 8.0D);
	}

	@Override
	protected void registerGoals() {
		this.goalSelector.addGoal(0, new FloatGoal(this));
		this.goalSelector.addGoal(1, new SitWhenOrderedToGoal(this));
		this.goalSelector.addGoal(2, new ManulHissGoal(this));

		// Убегает только от игрока в полный рост: крадущегося подпускает — это и есть
		// способ приблизиться к дикому манулу.
		this.avoidPlayersGoal = new AvoidEntityGoal<>(
				this, Player.class, 10.0F, 0.9D, 1.35D, living -> !living.isCrouching());
		this.goalSelector.addGoal(3, this.avoidPlayersGoal);

		this.goalSelector.addGoal(4, new BreedGoal(this, 0.8D));
		this.goalSelector.addGoal(5, new TemptGoal(this, 0.6D, this::isFood, false));
		this.goalSelector.addGoal(6, new FollowOwnerGoal(this, 1.0D, 10.0F, 4.0F));
		this.goalSelector.addGoal(7, new LeapAtTargetGoal(this, 0.3F));
		this.goalSelector.addGoal(8, new MeleeAttackGoal(this, 1.0D, true));
		this.goalSelector.addGoal(9, new ManulSunbatheGoal(this));
		this.goalSelector.addGoal(10, new WaterAvoidingRandomStrollGoal(this, 0.7D));
		this.goalSelector.addGoal(11, new LookAtPlayerGoal(this, Player.class, 8.0F));
		this.goalSelector.addGoal(12, new RandomLookAroundGoal(this));

		this.targetSelector.addGoal(1, new OwnerHurtByTargetGoal(this));
		this.targetSelector.addGoal(2, new OwnerHurtTargetGoal(this));
		this.targetSelector.addGoal(3, new NearestAttackableTargetGoal<>(this, Rabbit.class, false));
	}

	@Override
	protected void defineSynchedData(SynchedEntityData.Builder builder) {
		super.defineSynchedData(builder);
		builder.define(DATA_TRUST, 0);
		builder.define(DATA_HISSING, false);
		builder.define(DATA_GINGER, false);
	}

	// --- доверие ---------------------------------------------------------------

	public int getTrust() {
		return this.entityData.get(DATA_TRUST);
	}

	public void setTrust(int trust) {
		this.entityData.set(DATA_TRUST, Math.clamp(trust, 0, TRUST_MAX));
		this.reassessAvoidGoal();
	}

	/** Пока доверие низкое, манул держит дистанцию; потом цель убегания снимается. */
	private void reassessAvoidGoal() {
		if (this.avoidPlayersGoal == null) {
			return;
		}
		if (this.isTame() || this.getTrust() >= TRUST_CALM) {
			this.goalSelector.removeGoal(this.avoidPlayersGoal);
		} else {
			this.goalSelector.addGoal(3, this.avoidPlayersGoal);
		}
	}

	// --- шипение ---------------------------------------------------------------

	public boolean isHissing() {
		return this.entityData.get(DATA_HISSING);
	}

	public void setHissing(boolean hissing) {
		this.entityData.set(DATA_HISSING, hissing);
	}

	public void playHissSound() {
		this.playSound(SoundEvents.CAT_HISS, 0.9F, this.getVoicePitch() * 0.8F);
	}

	public void playPurrSound() {
		this.playSound(SoundEvents.CAT_PURR, 0.5F, this.getVoicePitch() * 0.8F);
	}

	// --- окрас -----------------------------------------------------------------

	/**
	 * Рыжий (краснопесчаный) манул — редкая, но настоящая вариация окраса.
	 *
	 * <p>Хранится в синхронизируемых данных, потому что от него зависит текстура,
	 * а её выбирает клиент.
	 */
	public boolean isGinger() {
		return this.entityData.get(DATA_GINGER);
	}

	public void setGinger(boolean ginger) {
		this.entityData.set(DATA_GINGER, ginger);
	}

	// --- взаимодействие --------------------------------------------------------

	@Override
	public boolean isFood(ItemStack stack) {
		Item item = stack.getItem();
		return item == Items.RABBIT || item == Items.COD || item == Items.SALMON;
	}

	@Override
	public InteractionResult mobInteract(Player player, InteractionHand hand) {
		ItemStack stack = player.getItemInHand(hand);
		boolean food = this.isFood(stack);

		if (this.isTame()) {
			// Раненого лечим едой, сытому едой командуем «сидеть»/«за мной».
			if (food && this.getHealth() < this.getMaxHealth()) {
				stack.consume(1, player);
				this.heal(3.0F);
				this.playPurrSound();
				return InteractionResult.SUCCESS;
			}
			if (!food) {
				if (!this.level().isClientSide()) {
					this.setOrderedToSit(!this.isOrderedToSit());
					this.setInSittingPose(this.isOrderedToSit());
					this.getNavigation().stop();
					this.setTarget(null);
				}
				return InteractionResult.SUCCESS;
			}
			return super.mobInteract(player, hand);
		}

		if (food) {
			if (!this.level().isClientSide()) {
				stack.consume(1, player);
				this.gainTrust(player);
			}
			return InteractionResult.SUCCESS;
		}

		return super.mobInteract(player, hand);
	}

	/** Кормление дикого манула: копим доверие, после порога — шанс приручения. */
	private void gainTrust(Player player) {
		this.setTrust(this.getTrust() + TRUST_PER_FEED);
		this.playPurrSound();

		if (this.getTrust() >= TRUST_TAME && this.random.nextInt(3) == 0) {
			this.tame(player);
			this.setOrderedToSit(false);
			this.level().broadcastEntityEvent(this, (byte) 7);  // сердечки
		} else {
			this.level().broadcastEntityEvent(this, (byte) 6);  // дымок: «пока нет»
		}
	}

	@Override
	public boolean hurtServer(ServerLevel level, DamageSource source, float amount) {
		boolean hurt = super.hurtServer(level, source, amount);
		if (hurt && source.getEntity() instanceof Player) {
			this.setTrust(this.getTrust() - TRUST_LOST_ON_HIT);
			this.setInSittingPose(false);
			this.setHissing(false);
		}
		return hurt;
	}

	// --- размножение и спавн ---------------------------------------------------

	@Override
	public ManulEntity getBreedOffspring(ServerLevel level, AgeableMob partner) {
		ManulEntity baby = ManulEntities.MANUL.create(level, EntitySpawnReason.BREEDING);
		if (baby == null) {
			return null;
		}
		if (this.isTame()) {
			baby.setOwnerUUID(this.getOwnerUUID());
			baby.setTame(true, true);
			baby.setTrust(TRUST_MAX);
		}
		baby.setGinger(this.inheritGinger(partner));
		return baby;
	}

	/**
	 * Окрас котёнка: берётся у случайного родителя, изредка переворачивается.
	 *
	 * <p>Из-за мутации рыжих можно вывести и от пары серых — иначе окрас,
	 * не выпавший при спавне, было бы уже не получить.
	 */
	private boolean inheritGinger(AgeableMob partner) {
		boolean fromParent = this.random.nextBoolean()
				? this.isGinger()
				: partner instanceof ManulEntity other && other.isGinger();
		return this.random.nextInt(GINGER_MUTATION_CHANCE) == 0 ? !fromParent : fromParent;
	}

	@Override
	public SpawnGroupData finalizeSpawn(ServerLevelAccessor level, DifficultyInstance difficulty,
			EntitySpawnReason reason, SpawnGroupData spawnData) {
		// super решает, родится ли манул детёнышем, поэтому вызов обязателен.
		SpawnGroupData data = super.finalizeSpawn(level, difficulty, reason, spawnData);
		// Окрас не назначается только призванным командой: /summon вызывает
		// finalizeSpawn уже после чтения NBT, и случайность затёрла бы {Ginger:1b}.
		// Рождённым от родителей окрас ставит getBreedOffspring, а загруженным из
		// файла мира finalizeSpawn вообще не вызывают — их данные уже на месте.
		if (reason != EntitySpawnReason.COMMAND) {
			this.setGinger(this.random.nextInt(GINGER_SPAWN_CHANCE) == 0);
		}
		return data;
	}

	@Override
	public boolean checkSpawnRules(LevelAccessor level, EntitySpawnReason reason) {
		// Манул — дневной хищник открытых пространств: в темноте не появляется.
		if (reason == EntitySpawnReason.NATURAL && !isBrightEnoughToSpawn(level, this.blockPosition())) {
			return false;
		}
		return super.checkSpawnRules(level, reason);
	}

	// --- сохранение ------------------------------------------------------------

	@Override
	public void addAdditionalSaveData(CompoundTag output) {
		super.addAdditionalSaveData(output);
		output.putInt(TAG_TRUST, this.getTrust());
		output.putBoolean(TAG_GINGER, this.isGinger());
	}

	@Override
	public void readAdditionalSaveData(CompoundTag input) {
		super.readAdditionalSaveData(input);
		this.setTrust(input.getInt(TAG_TRUST));
		this.setGinger(input.getBoolean(TAG_GINGER));
	}

	// --- звуки -----------------------------------------------------------------

	@Override
	protected SoundEvent getAmbientSound() {
		// Свой, записанный голос манула; шипение пока ванильное — своей записи нет.
		return this.isHissing() ? SoundEvents.CAT_HISS : ManulSounds.MANUL_AMBIENT;
	}

	@Override
	public int getAmbientSoundInterval() {
		return 260;  // молчаливее кошки
	}

	@Override
	protected SoundEvent getHurtSound(DamageSource source) {
		return SoundEvents.OCELOT_HURT;
	}

	@Override
	protected SoundEvent getDeathSound() {
		return SoundEvents.OCELOT_DEATH;
	}

	@Override
	public float getVoicePitch() {
		return this.isBaby() ? 1.5F : 0.95F;
	}
}
