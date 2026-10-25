
import pygame
import sys
import Player
import Boss1
from map import GameMap


class Game:
    def __init__(self):
        pygame.init()

        pygame.display.set_caption("Final Project")
        self.screen = pygame.display.set_mode(
            (1280, 720),
            pygame.RESIZABLE | pygame.SCALED
        )
        self.clock = pygame.time.Clock()

        self.game_map = GameMap("map_learning.tmx")  #載入地圖

         # 建立精靈群組
        self.all_sprite = pygame.sprite.Group()
        self.enemy_group = pygame.sprite.Group()

        self.player1 = Player.Player() #建立玩家
        self.boss1 = Boss1.Vergil(self.player1) #建立BOSS

        # 將玩家和 Boss 加入精靈群組
        self.all_sprite.add(self.player1)
        self.all_sprite.add(self.boss1)

        # 將 Boss 加入敵人群組
        self.enemy_group.add(self.boss1)


        # 把地圖中的碰撞資料交給玩家
        self.player1.collisions = self.game_map.collisions
        self.player1.platforms = self.game_map.platforms

        self.all_sprite.add(self.player1)
        self.all_sprite.add(self.boss1)
        self.enemy_group.add(self.boss1)

        # 攝影機偏移量
        self.camera_x = 0
        self.camera_y = 0

    def draw_sprites(self):
        """以攝影機座標繪製玩家和 Boss。"""

        for sprite in self.all_sprite:
            screen_x = sprite.rect.x - self.camera_x
            screen_y = sprite.rect.y - self.camera_y

            self.screen.blit(
                sprite.image,
                (screen_x, screen_y)
            )

    def run(self):
        running = True

        while running:
            # 1. 處理事件
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_w, pygame.K_SPACE):
                        self.player1.jump()

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.player1.attack()

            # 2. 更新玩家、Boss 與動畫
            self.all_sprite.update()

            # 3. 更新攝影機
            self.camera_x, self.camera_y = (
                self.game_map.get_camera_offset(
                    self.player1.rect,
                    self.screen.get_width(),
                    self.screen.get_height()
                )
            )

            # 4. 繪製地圖（先畫背景與地形）
            self.game_map.draw(
                self.screen,
                self.camera_x,
                self.camera_y
            )

            # 5. 繪製玩家與 Boss
            self.draw_sprites()

            # 6. 攻擊判定
            # 注意：Player.py 的 attack_hitbox
            # 需要接受 camera_x 和 camera_y 參數。
            self.player1.attack_hitbox(
                self.enemy_group,
                self.screen,
                self.camera_x,
                self.camera_y
            )

            # 7. 繪製 Boss 的碰撞框（偵錯用途）
            boss_hitbox = self.boss1.hitbox.copy()
            boss_hitbox.x -= self.camera_x
            boss_hitbox.y -= self.camera_y

            pygame.draw.rect(
                self.screen,
                (255, 0, 0),
                boss_hitbox,
                2
            )

            # 8. 更新畫面
            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()