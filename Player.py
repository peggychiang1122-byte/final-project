import pygame
from Animator import AnimatedSprite
from settings import (
    GROUND_Y,
    GRAVITY,
    PLAYER_JUMP_VELOCITY,
    PLAYER_SPEED,
    PARRY_WINDOW,
    PARRY_COOLDOWN,
    BLOCK_DAMAGE_FACTOR,
    BLOCK_KNOCKBACK_SPEED,
    PLAYER_IFRAME_DURATION,
)
from VFX import Hitbox, SlashVFX, ParrySparkVFX


class Player(pygame.sprite.Sprite):
    def __init__(self, start_x=260, ground_y=GROUND_Y):
        super().__init__()

        # 基礎數值與屬性 (保留原有命名風格並擴充)
        self.max_hp = 100
        self.player_hp = 100
        self.player_stamina = 100
        self.player_speed = PLAYER_SPEED

        # 固定跳躍高度與重力物理參數
        self.jump_velocity = PLAYER_JUMP_VELOCITY
        self.player_jump_power = PLAYER_JUMP_VELOCITY
        self.gravity = GRAVITY
        self.velocity_y = 0.0
        self.knockback_vel_x = 0.0
        self.ground_y = ground_y

        # 狀態旗標
        self.on_ground = True
        self.is_jumping = False
        self.is_attacking = False
        self.flip = False

        # 防禦與完美格擋 (Perfect Parry) 狀態
        self.is_blocking = False
        self.parry_timer = 0.0       # > 0 代表處於完美格擋時間窗 (前 0.15 秒)
        self.parry_cooldown = 0.0    # 防連點冷卻計時器
        self.invincible_timer = 0.0  # 受擊無敵幀 (i-frames) 計時器
        self.status_text = ""        # 格擋提示文字 (如 "PERFECT PARRY!")
        self.status_timer = 0.0

        # 動畫速率設定 (以 60 FPS 為基準)
        self.animation_speed = {
            "Run": 0.20,
            "idle": 0.12,
            "Attack": 0.32,
            "Jump": 0.18,
        }

        self.animator = AnimatedSprite()
        self.animator.load_animation(
            "idle",
            "asset/Legacy-Fantasy - High Forest 2.3/Character/Idle/Idle-Sheet.png",
            4,
            1.2,
        )
        self.animator.load_animation(
            "Run",
            "asset/Legacy-Fantasy - High Forest 2.3/Character/Run/Run-Sheet.png",
            8,
            1.2,
        )
        self.animator.load_animation(
            "Attack",
            "asset/Legacy-Fantasy - High Forest 2.3/Character/Attack-01/Attack-01-Sheet.png",
            8,
            1.2,
        )
        self.animator.load_animation(
            "Jump",
            "asset/Legacy-Fantasy - High Forest 2.3/Character/Jump-Start/Jump-Start-Sheet.png",
            4,
            1.2,
        )

        self.animator.play("idle")
        self.image = self.animator.update_get_image(self.animation_speed["idle"])

        # ---------- 分離三種碰撞框 ----------
        # 1. 移動物理碰撞框 (Collision Box)
        self.pos_x = float(start_x)
        self.pos_y = float(ground_y)
        self.collision_rect = pygame.Rect(0, 0, 34, 54)
        self.collision_rect.midbottom = (int(self.pos_x), int(self.pos_y))

        # 2. 受擊框 (Hurtbox)
        self.hurtbox = pygame.Rect(0, 0, 28, 48)
        self.hurtbox.center = self.collision_rect.center

        # 3. 格擋判定框 (Parry / Block Box，防禦時啟用)
        self.parry_box = pygame.Rect(0, 0, 42, 56)

        # 4. 攻擊判定框 (Hitbox，絕不常駐，僅在揮刀 Active Frames 期間實例化)
        self.current_attack_hitbox = None
        self.spawned_hitbox_this_swing = False

        # 繪製對齊矩形
        self.rect = self.image.get_rect(midbottom=self.collision_rect.midbottom)

    @property
    def is_parrying(self):
        """是否處於完美格擋時間窗內"""
        return self.is_blocking and self.parry_timer > 0.0

    def jump(self):
        """
        固定跳躍高度機制：
        僅當玩家在地面上 (on_ground) 時可觸發跳躍，賦予完全固定的初始垂直速度 -jump_velocity，
        且不受按鍵長短影響，確保每次跳躍最大高度完全固定。
        """
        if self.on_ground:
            self.velocity_y = -self.jump_velocity
            self.on_ground = False
            self.is_jumping = True
            self.animator.play("Jump", force_reset=True)

    def start_block(self):
        """按下防禦鍵瞬間：進入防禦狀態並啟動完美格擋時間窗 (parry_window)"""
        if self.is_attacking:
            # 取消當前攻擊並立即轉入防禦，提升動作遊戲反應手感
            self.is_attacking = False
            self._clear_attack_hitbox()

        if not self.is_blocking:
            self.is_blocking = True
            if self.parry_cooldown <= 0.0:
                self.parry_timer = PARRY_WINDOW
            else:
                self.parry_timer = 0.0

    def stop_block(self):
        """放開防禦鍵：結束防禦狀態"""
        if self.is_blocking:
            self.is_blocking = False
            self.parry_timer = 0.0
            self.parry_cooldown = PARRY_COOLDOWN

    def attack(self):
        """觸發近戰攻擊"""
        if not self.is_attacking and not self.is_blocking:
            self.is_attacking = True
            self.spawned_hitbox_this_swing = False
            self.animator.play("Attack", force_reset=True)

    def _clear_attack_hitbox(self):
        if self.current_attack_hitbox is not None:
            self.current_attack_hitbox.destroy()
            self.current_attack_hitbox = None

    def sync_boxes(self):
        """同步移動框、受擊框、格擋框與繪製框座標"""
        self.collision_rect.midbottom = (int(self.pos_x), int(self.pos_y))
        self.hurtbox.center = self.collision_rect.center

        if self.flip:
            self.parry_box.midright = (
                self.collision_rect.centerx + 4,
                self.collision_rect.centery,
            )
        else:
            self.parry_box.midleft = (
                self.collision_rect.centerx - 4,
                self.collision_rect.centery,
            )

        self.rect = self.image.get_rect(midbottom=self.collision_rect.midbottom)

    def update_attack_hitbox(self, active_hitboxes, vfx_group):
        """
        與攻擊動畫同步的 Hitbox 生命週期：
        - 第 3 ~ 5 幀 (Active Frames)：實例化一次 Hitbox 與刀光特效 SlashVFX
        - 超過第 5 幀或攻擊結束：立即銷毀並移除 Hitbox
        """
        if not self.is_attacking or self.animator.current_state != "Attack":
            self._clear_attack_hitbox()
            return

        frame = self.animator.current_frames
        if 2.5 <= frame <= 5.5:
            if not self.spawned_hitbox_this_swing:
                self.spawned_hitbox_this_swing = True
                offset_x = -42 if self.flip else 42
                hb_rect = pygame.Rect(0, 0, 74, 58)
                hb_rect.center = (
                    self.collision_rect.centerx + offset_x,
                    self.collision_rect.centery - 4,
                )
                kb = -220.0 if self.flip else 220.0
                hb = Hitbox(
                    owner="player",
                    rect=hb_rect,
                    damage=12,
                    knockback_x=kb,
                    lifetime=None,
                    tag="player_slash",
                )
                self.current_attack_hitbox = hb
                active_hitboxes.append(hb)

                slash_vfx = SlashVFX(
                    anchor_entity=self,
                    offset_x=offset_x,
                    offset_y=-4,
                    width=84,
                    height=64,
                    flip=self.flip,
                    duration=0.16,
                    color_outer=(255, 200, 70),
                    color_inner=(255, 255, 220),
                    hitbox=hb,
                )
                vfx_group.add(slash_vfx)
        # 離開 Active Frames (進入後搖 Recovery)，立即停用並銷毀 Hitbox
        else:
            self._clear_attack_hitbox()

    def attack_hitbox(self, enemies_group, screen):
        """相容舊版測試腳本 (a_test.py) 的呼叫介面"""
        if self.is_attacking and 2.5 <= self.animator.current_frames <= 5.5:
            offset_x = -42 if self.flip else 42
            attack_rect = pygame.Rect(0, 0, 74, 58)
            attack_rect.center = (
                self.collision_rect.centerx + offset_x,
                self.collision_rect.centery - 4,
            )
            pygame.draw.rect(screen, (250, 0, 0), attack_rect, 2)
            for enemy in enemies_group:
                if attack_rect.colliderect(enemy.hurtbox):
                    enemy.be_attacked()

    def take_hit(self, hitbox, attacker=None, vfx_group=None):
        """
        當 Boss 的 Active Hitbox 接觸玩家時呼叫：
        1. 先檢查是否處於『完美格擋 (Perfect Parry)』時間窗
        2. 再檢查是否處於『一般格擋 (Normal Block)』狀態
        3. 若未防禦且無無敵幀，扣除血量並啟動無敵幀 (i-frames)
        """
        # 計算特效生成點
        spark_x = (
            self.parry_box.centerx if self.is_blocking else self.hurtbox.centerx
        )
        spark_y = self.hurtbox.centery

        if self.is_blocking:
            # 防禦時自動面向攻擊來源
            if attacker is not None:
                self.flip = attacker.collision_rect.centerx < self.collision_rect.centerx

            if self.is_parrying:
                # ★ 觸發完美格擋 (Perfect Parry)！不扣血、重置防禦冷卻
                self.parry_timer = 0.0
                self.parry_cooldown = 0.0
                self.invincible_timer = 0.35
                self.status_text = "PERFECT PARRY!"
                self.status_timer = 0.90
                if vfx_group is not None:
                    vfx_group.add(ParrySparkVFX(spark_x, spark_y, perfect=True))
                return "parry"
            else:
                # ★ 觸發一般格擋 (Normal Block)：減免 70% 傷害並承受擊退
                reduced_dmg = max(1, int(round(hitbox.damage * BLOCK_DAMAGE_FACTOR)))
                self.player_hp = max(0, self.player_hp - reduced_dmg)
                self.invincible_timer = 0.25
                push_dir = (
                    -1
                    if (
                        attacker
                        and attacker.collision_rect.centerx
                        > self.collision_rect.centerx
                    )
                    else 1
                )
                self.knockback_vel_x = push_dir * BLOCK_KNOCKBACK_SPEED
                self.status_text = f"BLOCKED (-{reduced_dmg})"
                self.status_timer = 0.60
                if vfx_group is not None:
                    vfx_group.add(ParrySparkVFX(spark_x, spark_y, perfect=False))
                return "block"

        # 未防禦：檢查無敵幀 (i-frames)
        if self.invincible_timer > 0.0:
            return "ignored"

        # 正常受擊扣血並啟動無敵幀
        self.player_hp = max(0, self.player_hp - hitbox.damage)
        self.invincible_timer = PLAYER_IFRAME_DURATION
        push_dir = (
            -1
            if (
                attacker
                and attacker.collision_rect.centerx > self.collision_rect.centerx
            )
            else 1
        )
        self.knockback_vel_x = push_dir * (BLOCK_KNOCKBACK_SPEED * 0.85)
        self.status_text = f"-{hitbox.damage} HP"
        self.status_timer = 0.55
        return "hit"

    def update(self, dt=1 / 60, raw_dt=None, active_hitboxes=None, vfx_group=None, map_width=1600):
        if raw_dt is None:
            raw_dt = dt

        # 1. 計時器更新 (完美格擋窗使用真實時間 raw_dt，手感穩定一致)
        if self.parry_timer > 0.0:
            self.parry_timer = max(0.0, self.parry_timer - raw_dt)
        if self.parry_cooldown > 0.0:
            self.parry_cooldown = max(0.0, self.parry_cooldown - raw_dt)
        if self.invincible_timer > 0.0:
            self.invincible_timer = max(0.0, self.invincible_timer - dt)
        if self.status_timer > 0.0:
            self.status_timer = max(0.0, self.status_timer - raw_dt)

        # 2. 處理鍵盤與滑鼠持續按住狀態
        keys = pygame.key.get_pressed()
        mouse_buttons = pygame.mouse.get_pressed()
        holding_block = (
            mouse_buttons[2]
            or keys[pygame.K_j]
            or keys[pygame.K_LSHIFT]
            or keys[pygame.K_k]
        )
        if not holding_block and self.is_blocking:
            self.stop_block()

        # 3. 水平移動 (防禦中移動速度減半)
        is_moving = False
        move_speed = self.player_speed * (0.45 if self.is_blocking else 1.0)

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.pos_x -= move_speed * dt
            is_moving = True
            if not self.is_attacking:
                self.flip = True

        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.pos_x += move_speed * dt
            is_moving = True
            if not self.is_attacking:
                self.flip = False

        # 擊退速度衰減與位移
        if abs(self.knockback_vel_x) > 5.0:
            self.pos_x += self.knockback_vel_x * dt
            self.knockback_vel_x *= max(0.0, 1.0 - 10.0 * dt)
        else:
            self.knockback_vel_x = 0.0

        # 限制地圖左右邊界
        self.pos_x = max(25.0, min(float(map_width - 25), self.pos_x))

        # 4. 固定跳躍高度與一致的重力加速度更新 (絕不隨放開按鍵削減 velocity_y)
        if not self.on_ground or self.velocity_y != 0.0:
            self.velocity_y += self.gravity * dt
            self.pos_y += self.velocity_y * dt

            if self.pos_y >= self.ground_y:
                self.pos_y = float(self.ground_y)
                self.velocity_y = 0.0
                self.on_ground = True
                self.is_jumping = False

        # 5. 狀態與動畫更新
        new_state = "idle"
        loop_anim = True

        if self.is_attacking:
            new_state = "Attack"
            loop_anim = False
        elif not self.on_ground:
            new_state = "Jump"
            loop_anim = False
        elif is_moving:
            new_state = "Run"

        current_fspeed = self.animation_speed[new_state]
        self.animator.play(new_state)
        dt_scale = dt * 60.0
        self.image = self.animator.update_get_image(
            current_fspeed, dt_scale=dt_scale, loop=loop_anim
        )

        # 檢查攻擊動畫結束
        if self.is_attacking and self.animator.finished:
            self.is_attacking = False
            self._clear_attack_hitbox()
            self.animator.play("idle", force_reset=True)
            self.image = self.animator.update_get_image(
                self.animation_speed["idle"], dt_scale=0.0
            )

        # 同步攻擊 Hitbox 與特效
        if active_hitboxes is not None and vfx_group is not None:
            self.update_attack_hitbox(active_hitboxes, vfx_group)

        if self.flip:
            self.image = pygame.transform.flip(self.image, True, False)

        # 視覺效果：完美格擋青色高光 / 一般防禦藍色微光 / 受擊無敵幀閃爍
        if self.is_parrying:
            self.image = self.image.copy()
            self.image.fill((60, 180, 220), special_flags=pygame.BLEND_RGB_ADD)
        elif self.is_blocking:
            self.image = self.image.copy()
            self.image.fill((30, 70, 150), special_flags=pygame.BLEND_RGB_ADD)
        elif self.invincible_timer > 0.0:
            if int(self.invincible_timer * 20) % 2 == 0:
                self.image = self.image.copy()
                self.image.set_alpha(130)

        self.sync_boxes()
