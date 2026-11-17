import pygame
from Animator import AnimatedSprite

class Player(pygame.sprite.Sprite):
    def __init__(self):
        self.on_ground = False
        self.game_map = None

        super().__init__()

        self.player_speed = 5
        self.player_hp = 100
        self.player_stamina = 100
        self.player_jump_power = 4
        self.velocity_y = 0
        self.gravity = 4

        self.animation_speed = {
            "Run": 0.2,
            "idle": 0.1,
            "Attack": 0.4
        }

        self.is_attacking = False
        self.flip = False
        self.is_jumping = False

        self.animator = AnimatedSprite()
        self.animator.load_animation("idle", "asset/Legacy-Fantasy - High Forest 2.3/Character/Idle/Idle-Sheet.png", 4, 1.0)
        self.animator.load_animation("Run", "asset/Legacy-Fantasy - High Forest 2.3/Character/Run/Run-Sheet.png", 8, 1.0)
        self.animator.load_animation("Attack", "asset/Legacy-Fantasy - High Forest 2.3/Character/Attack-01/Attack-01-Sheet.png", 8, 1.0)

        self.animator.play("idle")

        self.image = self.animator.update_get_image(self.animation_speed["idle"])
        self.rect = self.image.get_rect(center = (320, 240))


    def attack(self):

        if not self.is_attacking:
            self.is_attacking = True


    def attack_hitbox(self, enemies_group, screen,
    camera_x=0, camera_y=0):
        if self.is_attacking and 3 <= self.animator.current_frames <= 5:
            hitbox_width, hitbox_height = 22, 40
            if self.flip:
                hitbox_x = self.rect.left - hitbox_width + 25
            else:
                hitbox_x = self.rect.right

            attack_rect = pygame.Rect(hitbox_x, self.rect.y + 20, hitbox_width, hitbox_height)
            pygame.draw.rect(screen, (250, 0, 0), attack_rect)

            for enemy in enemies_group:
                if attack_rect.colliderect(enemy.hitbox):
                    enemy.be_attacked()
            

    def update(self):
    def update(self):

    keys = pygame.key.get_pressed()

    is_moving = False
    new_state = "idle"

    # =================================
    # 1. 計算水平移動
    # =================================

    dx = 0

    if keys[pygame.K_a]:
        dx -= self.player_speed
        is_moving = True
        self.flip = True

    if keys[pygame.K_d]:
        dx += self.player_speed
        is_moving = True
        self.flip = False

    # =================================
    # 2. 跳躍
    # =================================

    if keys[pygame.K_w] and self.on_ground:
        self.velocity_y = -self.player_jump_power
        self.on_ground = False
        self.is_jumping = True

    # =================================
    # 3. 重力
    # =================================

    self.velocity_y += self.gravity / 60

    dy = round(self.velocity_y)

    # =================================
    # 4. 地圖碰撞判定
    # =================================

    if self.game_map is not None:

        self.on_ground, hit_ceiling = (
            self.game_map.move_with_collisions(
                self.rect,
                dx,
                dy
            )
        )

        # 落地：停止向下移動
        if self.on_ground and self.velocity_y > 0:
            self.velocity_y = 0
            self.is_jumping = False

        # 撞到天花板：停止向上移動
        if hit_ceiling and self.velocity_y < 0:
            self.velocity_y = 0

    else:

        # 尚未設定地圖時，維持一般移動
        self.rect.x += dx
        self.rect.y += dy

    # =================================
    # 5. 動畫狀態
    # =================================

    if self.is_attacking:

        new_state = "Attack"

        if (
            self.animator.current_frames == 0
            and self.animator.current_state == "Attack"
        ):
            self.is_attacking = False

    elif is_moving:

        new_state = "Run"

    current_fspeed = self.animation_speed[new_state]

    self.animator.play(new_state)

    self.image = self.animator.update_get_image(
        current_fspeed
    )

    if self.flip:
        self.image = pygame.transform.flip(
            self.image,
            True,
            False
        )
 

  