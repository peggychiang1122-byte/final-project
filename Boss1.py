import pygame
from Animator import AnimatedSprite

class Vergil(pygame.sprite.Sprite):
    def __init__(self, target_player):

        super().__init__()

        self.target = target_player
        self.boss_health = 100
        self.boss_speed = 3.5
        self.last_hit_time = 0
        self.last_attack_time = 0 

        self.animation_speed = {
            "Run": 0.165,
            "idle": 0.1,
            "Attack1": 0.1
        }
        
        self.is_attacking = False
        self.flip = False
        self.is_cooldown = False

        self.animator = AnimatedSprite()
        self.animator.load_animation("idle", "asset/Vergil/vergil_idle.png", 4, 0.11)
        self.animator.load_animation("Run", "asset/Vergil/vergil_run.png", 6, 0.12)
        self.animator.load_animation("Attack1", "asset/Vergil/vergil_attack1.png", 4, 0.12)
        
        self.animator.play("idle")
        
        self.image = self.animator.update_get_image(self.animation_speed["idle"])
        self.hitbox = pygame.Rect(320, 240, 85, 110)
        self.rect = self.hitbox.copy()

    def update(self):

        new_state = "idle"  

        self.is_moving = False
  
        boss_x = self.rect.centerx
        player_x = self.target.rect.centerx
        current_time = pygame.time.get_ticks()
        distance = abs(boss_x - player_x)       

        current_fspeed = self.animation_speed[new_state]
        
        if self.is_cooldown:
            if current_time - self.last_attack_time > 450:
                self.is_cooldown = False

        elif self.is_attacking:
            pass

        else:
            if distance > 40:
                if boss_x > player_x:
                    self.hitbox.x -= self.boss_speed
                    self.is_moving = True
                    self.flip = True
                elif boss_x < player_x:
                    self.hitbox.x += self.boss_speed
                    self.is_moving = True
                    self.flip = False
            elif distance <= 40:
                self.is_attacking = True


        if self.is_attacking:
            new_state = "Attack1"
            if self.animator.current_frames + current_fspeed >= 4 and self.animator.current_state == "Attack1":
                self.is_attacking = False
                self.is_cooldown = True
                self.last_attack_time = current_time
                new_state = "idle"
        elif self.is_moving:
            new_state = "Run"

        self.animator.play(new_state)
        self.image = self.animator.update_get_image(current_fspeed)

        if self.flip:
            self.image = pygame.transform.flip(self.image, True, False).convert_alpha()

        if current_time - self.last_hit_time < 300:
            if (current_time // 75) % 2 == 0:
                self.image = self.image.copy()
                self.image.fill((255, 0, 0), special_flags=pygame.BLEND_RGB_ADD)
        
        self.rect = self.image.get_rect()
        self.rect.midbottom = self.hitbox.midbottom

    def be_attacked(self):

        current_time = pygame.time.get_ticks()
        if current_time - self.last_hit_time > 300:
            self.boss_health -= 10
            self.last_hit_time = current_time

            if self.boss_health <= 0:
                self.kill()
