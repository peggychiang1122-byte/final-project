import pygame
from settings import *
from game_state import State
from map import GameMap
import Player
import Boss1

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE | pygame.SCALED)
pygame.display.set_caption("Final Project")
clock = pygame.time.Clock()

font_big = pygame.font.SysFont(None, 90)
font_small = pygame.font.SysFont(None, 40)

background = pygame.image.load(
    "asset/Legacy-Fantasy - High Forest 2.3/Background/Background.png"
)
background = pygame.transform.scale(background, (WIDTH, HEIGHT))

game_map = GameMap("map_learning.tmx")   # B 的地圖，整個遊戲只建立一次
dummy_surface = pygame.Surface((1, 1))   # 見下方說明


def new_game():
    """建立一局新遊戲（開始 / 重新開始都呼叫它）"""
    player = Player.Player()
    player.game_map = game_map
    boss = Boss1.Vergil(player)
    all_sprites = pygame.sprite.Group(player, boss)
    enemies = pygame.sprite.Group(boss)
    return player, boss, all_sprites, enemies


def draw_text(text, font, color, center):
    img = font.render(text, True, color)
    screen.blit(img, img.get_rect(center=center))


def draw_player_hp(player):
    max_hp = 100
    ratio = max(player.player_hp, 0) / max_hp
    pygame.draw.rect(screen, (60, 60, 60), (20, 20, 300, 24))
    pygame.draw.rect(screen, (200, 40, 40), (20, 20, int(300 * ratio), 24))
    pygame.draw.rect(screen, (255, 255, 255), (20, 20, 300, 24), 2)


def draw_boss_hp(boss):
    max_hp = 100
    bar_w, bar_h = 500, 20
    x = (WIDTH - bar_w) // 2
    y = 30
    ratio = max(boss.boss_health, 0) / max_hp
    pygame.draw.rect(screen, (60, 60, 60), (x, y, bar_w, bar_h))
    pygame.draw.rect(screen, (150, 30, 150), (x, y, int(bar_w * ratio), bar_h))
    pygame.draw.rect(screen, (255, 255, 255), (x, y, bar_w, bar_h), 2)
    draw_text("BOSS", font_small, (0, 0, 0), (WIDTH // 2, y - 14))


player, boss, all_sprites, enemies = new_game()
camera_x, camera_y = 0, 0
state = State.MENU

running = True
while running:
    # ---------- 1. 輸入 ----------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if state == State.MENU and event.key == pygame.K_RETURN:
                player, boss, all_sprites, enemies = new_game()
                state = State.PLAYING
            elif state == State.PLAYING:
                if event.key == pygame.K_ESCAPE:
                    state = State.PAUSED
            elif state == State.PAUSED and event.key == pygame.K_ESCAPE:
                state = State.PLAYING
            elif state == State.GAME_OVER and event.key == pygame.K_RETURN:
                state = State.MENU

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if state == State.PLAYING:
                player.attack()

    # ---------- 2. 更新 ----------
    if state == State.PLAYING:
        all_sprites.update()
        # 攻擊判定用的是世界座標，不需要畫出來，所以丟給假畫布
        player.attack_hitbox(enemies, dummy_surface)
        camera_x, camera_y = game_map.get_camera_offset(player.rect, WIDTH, HEIGHT)

    
        if player.player_hp <= 0:
            state = State.GAME_OVER

    # ---------- 3. 繪製 ----------
    if state == State.MENU:
        screen.fill((20, 20, 60))
        draw_text("MY GAME", font_big, (255, 255, 255), (WIDTH // 2, 250))
        draw_text("Press ENTER to start", font_small, (200, 200, 200), (WIDTH // 2, 400))

    elif state in (State.PLAYING, State.PAUSED):
        screen.blit(background, (0, 0))
        game_map.draw(screen, camera_x, camera_y)
        for sprite in all_sprites:      # 角色、Boss 要扣掉鏡頭偏移才會跟地圖對齊
            screen.blit(sprite.image, sprite.rect.move(-camera_x, -camera_y))
        
        # 【碰撞除錯顯示】
        game_map.draw_collision_debug( screen , camera_x , camera_y)
        


        draw_player_hp(player)          # UI 固定在畫面上，不跟鏡頭動
        draw_boss_hp(boss)              # 繪製 Boss 血條
        if state == State.PAUSED:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))
            draw_text("PAUSED", font_big, (255, 255, 255), (WIDTH // 2, HEIGHT // 2))

    elif state == State.GAME_OVER:
        screen.fill((80, 20, 20))
        draw_text("GAME OVER", font_big, (255, 255, 255), (WIDTH // 2, 280))
        draw_text("Press ENTER to return to menu", font_small, (220, 220, 220), (WIDTH // 2, 420))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()