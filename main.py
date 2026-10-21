
import pygame
from map import GameMap

pygame.init()

# 建立遊戲視窗
screen = pygame.display.set_mode((1280, 720))
pygame.display.set_caption("Map Test")

# 載入 Tiled 地圖
game_map = GameMap("map_learning.tmx")
# 設定遊戲一開始的鏡頭位置
camera_x = 0
camera_y = 250

running = True
clock = pygame.time.Clock()

while running:
    # 處理關閉視窗的事件
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 填滿背景色
    screen.fill((30, 30, 40))

    # 繪製地圖
    game_map.draw(screen, camera_x, camera_y)

    # 更新畫面
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
