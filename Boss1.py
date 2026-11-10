import math
import pygame
from Animator import AnimatedSprite
from settings import GROUND_Y, GRAVITY
from VFX import (
    Hitbox,
    SlashVFX,
    DashSlashVFX,
    ProjectileWaveVFX,
    GroundShockwaveVFX,
)


class BossState:
    IDLE = "IDLE"
    CHASE = "CHASE"
    ATTACK_1 = "ATTACK_1"  # 近距離居合二連斬
    ATTACK_2 = "ATTACK_2"  # 中距離疾風突進斬 (Dash Slash)
    ATTACK_3 = "ATTACK_3"  # 遠程次元劍氣波 + 地面次元斬領域
    COOLDOWN = "COOLDOWN"


class AttackPhase:
    NONE = "NONE"
    WINDUP = "WINDUP"      # 前搖預警 (無 Hitbox)
    ACTIVE = "ACTIVE"      # 攻擊判定 (生成 VFX 與 Hitbox)
    RECOVERY = "RECOVERY"  # 後搖收招 (銷毀近戰 Hitbox)


class Vergil(pygame.sprite.Sprite):
    def __init__(self, target_player, start_x=640, ground_y=GROUND_Y):
        super().__init__()

        self.target = target_player
        self.max_health = 100
        self.boss_health = 100
        self.boss_speed = 210.0  # px / s (對應原本 3.5 px/frame @ 60fps)

        # 物理與座標
        self.pos_x = float(start_x)
        self.pos_y = float(ground_y)
        self.ground_y = ground_y
        self.velocity_y = 0.0
        self.gravity = GRAVITY
        self.flip = True

        # FSM 狀態機屬性
        self.state = BossState.IDLE
        self.attack_phase = AttackPhase.NONE
        self.state_timer = 0.0
        self.cooldown_duration = 0.55

        # 各招式獨立冷卻時間 (秒)
        self.skill_cooldowns = {
            BossState.ATTACK_1: 0.0,
            BossState.ATTACK_2: 0.0,
            BossState.ATTACK_3: 0.0,
        }

        # 受擊閃白/閃紅與無敵間隔計時器 (以 dt 計時，受 time_scale 影響)
        self.hit_flash_timer = 0.0
        self.hit_invuln_timer = 0.0

        # 攻擊期間的輔助旗標
        self.combo_step = 0
        self.dash_dir = -1
        self.dash_start_x = 0.0
        self.current_melee_hitbox = None

        # 動畫設定
        self.animation_speed = {
            "idle": 0.10,
            "Run": 0.165,
            "Dash": 0.22,
            "Attack1": 0.14,
        }

        self.animator = AnimatedSprite()
        self.animator.load_animation("idle", "asset/Vergil/vergil_idle.png", 4, 0.11)
        self.animator.load_animation("Run", "asset/Vergil/vergil_run.png", 6, 0.12)
        self.animator.load_animation("Dash", "asset/Vergil/vergil_dash.png", 5, 0.58)
        self.animator.load_animation(
            "Attack1", "asset/Vergil/vergil_attack1.png", 4, 0.12
        )

        self.animator.play("idle")
        self.image = self.animator.update_get_image(self.animation_speed["idle"])

        # ---------- 分離碰撞框 ----------
        # 1. 移動物理碰撞框 (Collision Box)
        self.collision_rect = pygame.Rect(0, 0, 52, 98)
        self.collision_rect.midbottom = (int(self.pos_x), int(self.pos_y))

        # 2. 受擊框 (Hurtbox)
        self.hurtbox = pygame.Rect(0, 0, 44, 92)
        self.hurtbox.center = self.collision_rect.center
        # 相容舊屬性名稱
        self.hitbox = self.hurtbox

        # 3. 繪製對齊框
        self.rect = self.image.get_rect(midbottom=self.collision_rect.midbottom)

    def sync_boxes(self):
        self.collision_rect.midbottom = (int(self.pos_x), int(self.pos_y))
        self.hurtbox.center = self.collision_rect.center
        self.hitbox = self.hurtbox
        self.rect = self.image.get_rect(midbottom=self.collision_rect.midbottom)

    def _clear_melee_hitbox(self):
        if self.current_melee_hitbox is not None:
            self.current_melee_hitbox.destroy()
            self.current_melee_hitbox = None

    def face_target(self):
        if self.target and self.target.alive():
            self.flip = (
                self.target.collision_rect.centerx < self.collision_rect.centerx
            )

    def change_state(self, new_state, cooldown_duration=0.55):
        self._clear_melee_hitbox()
        self.state = new_state
        self.state_timer = 0.0
        self.combo_step = 0

        if new_state in (
            BossState.ATTACK_1,
            BossState.ATTACK_2,
            BossState.ATTACK_3,
        ):
            self.face_target()
            self.attack_phase = AttackPhase.WINDUP
            if new_state == BossState.ATTACK_1:
                self.animator.play("Attack1", force_reset=True)
            elif new_state == BossState.ATTACK_2:
                self.dash_dir = -1 if self.flip else 1
                self.dash_start_x = self.pos_x
                self.animator.play("Dash", force_reset=True)
            elif new_state == BossState.ATTACK_3:
                self.animator.play("Attack1", force_reset=True)
        else:
            self.attack_phase = AttackPhase.NONE
            if new_state == BossState.COOLDOWN:
                self.cooldown_duration = cooldown_duration
                self.animator.play("idle")
            elif new_state == BossState.IDLE:
                self.animator.play("idle")
            elif new_state == BossState.CHASE:
                self.animator.play("Run")

    def decide_next_action(self, distance):
        """
        根據與玩家的距離 (distance) 與各招式冷卻時間動態決定下一個狀態：
        - 近距離 (<= 95px)：優先使用 ATTACK_1 (居合二連斬)
        - 中距離 (95 ~ 280px)：優先使用 ATTACK_2 (疾風突進斬)
        - 遠距離 (> 280px)：優先使用 ATTACK_3 (遠程劍氣波 + 次元斬領域)
        - 若對應距離招式冷卻中，則進入 CHASE 追擊逼近玩家
        """
        cd1 = self.skill_cooldowns[BossState.ATTACK_1] <= 0.0
        cd2 = self.skill_cooldowns[BossState.ATTACK_2] <= 0.0
        cd3 = self.skill_cooldowns[BossState.ATTACK_3] <= 0.0

        if distance <= 95:
            if cd1:
                self.change_state(BossState.ATTACK_1)
                return
            if cd2:
                self.change_state(BossState.ATTACK_2)
                return

        elif distance <= 280:
            if cd2:
                self.change_state(BossState.ATTACK_2)
                return
            if cd3 and distance >= 165:
                self.change_state(BossState.ATTACK_3)
                return

        else:
            if cd3:
                self.change_state(BossState.ATTACK_3)
                return
            if cd2 and distance <= 360:
                self.change_state(BossState.ATTACK_2)
                return

        # 若無立即可放的招式或距離尚遠，進入 CHASE 追擊
        if distance > 75:
            self.change_state(BossState.CHASE)
        else:
            self.change_state(BossState.IDLE)

    # ---------- 3 種攻擊狀態實作 (皆含 WINDUP -> ACTIVE -> RECOVERY) ----------

    def _update_attack_1(self, dt, active_hitboxes, vfx_group):
        """
        ATTACK_1：近距離居合二連斬
        - WINDUP (0.00 ~ 0.32s)：收刀蓄力閃光預警，無 Hitbox
        - ACTIVE (0.32 ~ 0.68s)：第一斬 (0.32s) + 第二斬強化橫斬 (0.50s)，各自綁定 SlashVFX 與 Hitbox
        - RECOVERY (0.68 ~ 0.98s)：銷毀近戰 Hitbox，收刀硬直後進入 COOLDOWN
        """
        windup_end = 0.32
        slash2_time = 0.50
        active_end = 0.68
        recovery_end = 0.98

        if self.state_timer < windup_end:
            self.attack_phase = AttackPhase.WINDUP
            self.animator.play("Attack1")
            # 前搖期間固定在第 0 幀蓄力姿勢
            self.animator.current_frames = 0.0

        elif self.state_timer < active_end:
            self.attack_phase = AttackPhase.ACTIVE
            # 第一斬觸發
            if self.combo_step == 0:
                self.combo_step = 1
                self.face_target()
                step_dir = -1 if self.flip else 1
                self.pos_x += step_dir * 18.0
                self._spawn_melee_slash(
                    active_hitboxes,
                    vfx_group,
                    width=105,
                    height=78,
                    damage=15,
                    duration=0.16,
                    color_outer=(50, 160, 255),
                    tilt_angle=-12.0,
                )

            # 第二斬觸發
            elif self.combo_step == 1 and self.state_timer >= slash2_time:
                self.combo_step = 2
                self._clear_melee_hitbox()
                self.face_target()
                step_dir = -1 if self.flip else 1
                self.pos_x += step_dir * 26.0
                self._spawn_melee_slash(
                    active_hitboxes,
                    vfx_group,
                    width=125,
                    height=88,
                    damage=20,
                    duration=0.17,
                    color_outer=(120, 90, 255),
                    tilt_angle=14.0,
                )

        elif self.state_timer < recovery_end:
            if self.attack_phase != AttackPhase.RECOVERY:
                self.attack_phase = AttackPhase.RECOVERY
                self._clear_melee_hitbox()
        else:
            self._clear_melee_hitbox()
            self.skill_cooldowns[BossState.ATTACK_1] = 1.4
            self.change_state(BossState.COOLDOWN, cooldown_duration=0.55)

    def _update_attack_2(self, dt, active_hitboxes, vfx_group, map_width):
        """
        ATTACK_2：疾風突進斬 (Dash Slash)
        - WINDUP (0.00 ~ 0.38s)：壓低身姿蓄力，顯示突進方向預警，無 Hitbox
        - ACTIVE (0.38 ~ 0.64s)：高速向前突進，生成 DashSlashVFX 與隨身突進 Hitbox
        - RECOVERY (0.64 ~ 1.00s)：停止突進並立即銷毀 Hitbox，進入後搖
        """
        windup_end = 0.38
        active_end = 0.64
        recovery_end = 1.00
        dash_speed = 760.0

        if self.state_timer < windup_end:
            self.attack_phase = AttackPhase.WINDUP
            self.face_target()
            self.dash_dir = -1 if self.flip else 1
            self.dash_start_x = self.pos_x
            self.animator.play("Dash")
            self.animator.current_frames = 0.0

        elif self.state_timer < active_end:
            self.attack_phase = AttackPhase.ACTIVE
            if self.combo_step == 0:
                self.combo_step = 1
                hb = Hitbox(
                    owner="boss",
                    rect=pygame.Rect(
                        int(self.pos_x - 60),
                        int(self.collision_rect.centery - 38),
                        120,
                        76,
                    ),
                    damage=22,
                    knockback_x=self.dash_dir * 300.0,
                    lifetime=active_end - windup_end,
                    tag="boss_dash",
                )
                self.current_melee_hitbox = hb
                if active_hitboxes is not None:
                    active_hitboxes.append(hb)

                if vfx_group is not None:
                    vfx_group.add(
                        DashSlashVFX(
                            anchor_entity=self,
                            start_x=self.dash_start_x,
                            y=self.collision_rect.centery,
                            width=160,
                            height=76,
                            flip=self.flip,
                            duration=active_end - windup_end,
                            hitbox=hb,
                        )
                    )

            # 執行高速突進位移
            self.pos_x += self.dash_dir * dash_speed * dt
            self.pos_x = max(40.0, min(float(map_width - 40), self.pos_x))

        elif self.state_timer < recovery_end:
            if self.attack_phase != AttackPhase.RECOVERY:
                self.attack_phase = AttackPhase.RECOVERY
                self._clear_melee_hitbox()
                self.animator.play("Attack1")
                self.animator.current_frames = 3.0
        else:
            self._clear_melee_hitbox()
            self.skill_cooldowns[BossState.ATTACK_2] = 2.4
            self.change_state(BossState.COOLDOWN, cooldown_duration=0.65)

    def _update_attack_3(self, dt, active_hitboxes, vfx_group):
        """
        ATTACK_3：次元劍氣波 + 遠程次元斬領域 (Ranged Wave + AoE Judgment Cut)
        - WINDUP (0.00 ~ 0.42s)：凝聚紫藍色次元能量預警，無 Hitbox
        - ACTIVE (0.42 ~ 0.72s)：發射飛行劍氣波 ProjectileWaveVFX，同時於玩家位置召喚 GroundShockwaveVFX
        - RECOVERY (0.72 ~ 1.10s)：收刀後搖，等待下一次行動
        """
        windup_end = 0.42
        active_end = 0.72
        recovery_end = 1.10

        if self.state_timer < windup_end:
            self.attack_phase = AttackPhase.WINDUP
            self.face_target()
            self.animator.play("Attack1")
            self.animator.current_frames = 0.0

        elif self.state_timer < active_end:
            self.attack_phase = AttackPhase.ACTIVE
            if self.combo_step == 0:
                self.combo_step = 1
                direction = -1 if self.flip else 1
                spawn_x = self.collision_rect.centerx + direction * 46
                spawn_y = self.collision_rect.centery - 4

                # 1. 發射遠程飛行劍氣波 (掛載隨行 Hitbox)
                wave_hb = Hitbox(
                    owner="boss",
                    rect=pygame.Rect(int(spawn_x - 24), int(spawn_y - 42), 48, 84),
                    damage=18,
                    knockback_x=direction * 240.0,
                    lifetime=1.35,
                    tag="projectile",
                )
                if active_hitboxes is not None:
                    active_hitboxes.append(wave_hb)

                if vfx_group is not None:
                    wave_vfx = ProjectileWaveVFX(
                        x=spawn_x,
                        y=spawn_y,
                        direction=direction,
                        speed=540.0,
                        width=58,
                        height=96,
                        duration=1.35,
                        hitbox=wave_hb,
                    )
                    vfx_group.add(wave_vfx)

                    # 2. 在玩家當前位置召喚延遲爆發的次元斬領域 (含預警圈與動態 Hitbox)
                    if self.target and self.target.alive():
                        aoe_vfx = GroundShockwaveVFX(
                            target_x=self.target.collision_rect.centerx,
                            ground_y=self.ground_y,
                            radius=66,
                            windup_time=0.45,
                            active_time=0.26,
                            recovery_time=0.18,
                            damage=20,
                            hitbox_list=active_hitboxes,
                        )
                        vfx_group.add(aoe_vfx)

        elif self.state_timer < recovery_end:
            self.attack_phase = AttackPhase.RECOVERY
        else:
            self.skill_cooldowns[BossState.ATTACK_3] = 3.2
            self.change_state(BossState.COOLDOWN, cooldown_duration=0.75)

    def _spawn_melee_slash(
        self,
        active_hitboxes,
        vfx_group,
        width=105,
        height=78,
        damage=15,
        duration=0.16,
        color_outer=(50, 160, 255),
        tilt_angle=0.0,
    ):
        offset_x = -52 if self.flip else 52
        hb_rect = pygame.Rect(0, 0, width - 12, height - 10)
        hb_rect.center = (
            int(self.collision_rect.centerx + offset_x),
            int(self.collision_rect.centery - 4),
        )
        kb = -240.0 if self.flip else 240.0
        hb = Hitbox(
            owner="boss",
            rect=hb_rect,
            damage=damage,
            knockback_x=kb,
            lifetime=duration,
            tag="boss_melee",
        )
        self.current_melee_hitbox = hb
        if active_hitboxes is not None:
            active_hitboxes.append(hb)

        if vfx_group is not None:
            slash_vfx = SlashVFX(
                anchor_entity=self,
                offset_x=offset_x,
                offset_y=-4,
                width=width,
                height=height,
                flip=self.flip,
                duration=duration,
                color_outer=color_outer,
                color_inner=(230, 250, 255),
                tilt_angle=tilt_angle,
                hitbox=hb,
            )
            vfx_group.add(slash_vfx)

    def on_parried(self):
        """
        當玩家對 Boss 的近戰/突進攻擊觸發『完美格擋』時：
        立即清除當前近戰 Hitbox，並使 Boss 進入短暫反擊破綻 (RECOVERY)，方便玩家於子彈時間內反擊。
        """
        self._clear_melee_hitbox()
        if self.state in (BossState.ATTACK_1, BossState.ATTACK_2):
            self.attack_phase = AttackPhase.RECOVERY
            self.state_timer = 0.68

    def be_attacked(self, damage=12):
        """受到玩家攻擊扣血"""
        if self.hit_invuln_timer <= 0.0 and self.boss_health > 0:
            self.boss_health = max(0, self.boss_health - damage)
            self.hit_flash_timer = 0.25
            self.hit_invuln_timer = 0.18
            if self.boss_health <= 0:
                self._clear_melee_hitbox()
                self.kill()

    def update(self, dt=1 / 60, active_hitboxes=None, vfx_group=None, map_width=1600):
        # 1. 更新所有計時器 (全部乘上已含 time_scale 的 dt)
        self.state_timer += dt
        if self.hit_flash_timer > 0.0:
            self.hit_flash_timer = max(0.0, self.hit_flash_timer - dt)
        if self.hit_invuln_timer > 0.0:
            self.hit_invuln_timer = max(0.0, self.hit_invuln_timer - dt)

        for k in self.skill_cooldowns:
            if self.skill_cooldowns[k] > 0.0:
                self.skill_cooldowns[k] = max(0.0, self.skill_cooldowns[k] - dt)

        player_x = (
            self.target.collision_rect.centerx
            if (self.target and self.target.alive())
            else self.pos_x
        )
        distance = abs(self.pos_x - player_x)

        # 2. FSM 狀態行為更新
        if self.state == BossState.COOLDOWN:
            if self.state_timer >= self.cooldown_duration:
                self.change_state(BossState.IDLE)

        elif self.state == BossState.IDLE:
            self.face_target()
            if self.state_timer >= 0.15:
                self.decide_next_action(distance)

        elif self.state == BossState.CHASE:
            self.face_target()
            move_dir = -1 if self.pos_x > player_x else 1
            self.pos_x += move_dir * self.boss_speed * dt
            self.pos_x = max(40.0, min(float(map_width - 40), self.pos_x))
            self.decide_next_action(distance)

        elif self.state == BossState.ATTACK_1:
            self._update_attack_1(dt, active_hitboxes, vfx_group)

        elif self.state == BossState.ATTACK_2:
            self._update_attack_2(dt, active_hitboxes, vfx_group, map_width)

        elif self.state == BossState.ATTACK_3:
            self._update_attack_3(dt, active_hitboxes, vfx_group)

        # 3. 地面重力對齊
        if self.pos_y < self.ground_y:
            self.velocity_y += self.gravity * dt
            self.pos_y = min(float(self.ground_y), self.pos_y + self.velocity_y * dt)
        else:
            self.pos_y = float(self.ground_y)
            self.velocity_y = 0.0

        # 4. 動畫幀率更新 (乘上 dt_scale = dt * 60，在子彈時間下自動慢動作)
        anim_state = self.animator.current_state or "idle"
        current_fspeed = self.animation_speed.get(anim_state, 0.12)
        dt_scale = dt * 60.0
        # 前搖期間固定蓄力姿勢，進入 ACTIVE 後才推進攻擊動畫幀
        if self.attack_phase == AttackPhase.WINDUP:
            dt_scale = 0.0

        self.image = self.animator.update_get_image(current_fspeed, dt_scale=dt_scale)

        if self.flip:
            self.image = pygame.transform.flip(self.image, True, False).convert_alpha()

        # 5. 視覺特效疊加：前搖預警光效 & 受擊閃紅
        if self.attack_phase == AttackPhase.WINDUP:
            # 前搖預警閃光：提醒玩家準備按格擋
            pulse = int(abs(math.sin(self.state_timer * 22.0)) * 110)
            self.image = self.image.copy()
            if self.state == BossState.ATTACK_2:
                self.image.fill((pulse, int(pulse * 0.4), 0), special_flags=pygame.BLEND_RGB_ADD)
            elif self.state == BossState.ATTACK_3:
                self.image.fill((int(pulse * 0.6), 0, pulse), special_flags=pygame.BLEND_RGB_ADD)
            else:
                self.image.fill((0, int(pulse * 0.7), pulse), special_flags=pygame.BLEND_RGB_ADD)

        if self.hit_flash_timer > 0.0:
            if int(self.hit_flash_timer * 25) % 2 == 0:
                self.image = self.image.copy()
                self.image.fill((255, 40, 40), special_flags=pygame.BLEND_RGB_ADD)

        self.sync_boxes()
