import pygame
from Animator import AnimatedSprite

class Player(pygame.sprite.Sprite):
    def __init__(self):

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


    def attack_hitbox(self, enemies_group, screen):
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

        keys = pygame.key.get_pressed()

        is_moving = False

        new_state = "idle"

        if keys[pygame.K_w]:
            self.velocity_y = - self.player_jump_power
            is_moving = True
            self.is_jumping = True

        if keys[pygame.K_s]:
            self.rect.y += self.player_speed
            is_moving = True

        if keys[pygame.K_a]:
            self.rect.x -= self.player_speed
            is_moving = True
            self.flip = True

        if keys[pygame.K_d]:
            self.rect.x += self.player_speed
            is_moving = True
            self.flip = False

        if self.is_jumping:
            self.rect.y += self.velocity_y
            self.velocity_y += self.gravity / 60
        
        
        if self.is_attacking:
            new_state = "Attack"
            if self.animator.current_frames == 0 and self.animator.current_state == "Attack":
                self.is_attacking = False
        elif is_moving:
            new_state = "Run"

        current_fspeed = self.animation_speed[new_state]
        self.animator.play(new_state)
        self.image = self.animator.update_get_image(current_fspeed)

        if self.flip:
            self.image = pygame.transform.flip(self.image, True, False)

                