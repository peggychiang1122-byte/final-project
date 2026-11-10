
import pygame
from settings import *
from game_state import State
from map import GameMap
import Player
import Boss1


# ==========================================
# 1. Pygame 初始化
# ==========================================

pygame.init()

screen = pygame.display.set_mode(
    (WIDTH, HEIGHT),
    pygame.RESIZABLE | pygame.SCALED
)

pygame.display.set_caption("Final Project")

clock = pygame.time.Clock()

font_big = pygame.font.SysFont(None, 90)
font_small = pygame.font.SysFont(None, 40)


# ==========================================
# 2. 載入背景與地圖
# ==========================================

background = pygame.image.load(
    "asset/Legacy-Fantasy - High Forest 2.3/Background/Background.png"
)

background = pygame.transform.scale(
    background,
    (WIDTH, HEIGHT)
)

# 地圖只需要建立一次，不要在遊戲迴圈中重複載入
game_map = GameMap("map_learning.tmx")

# 攻擊判定使用的空白畫布
dummy_surface = pygame.Surface((1, 1))


# ==========================================
# 3. 建立遊戲角色
# ==========================================

def new_game():

    # 建立玩家
    player = Player.Player()

    # 將地圖傳給玩家，讓玩家可以使用地圖碰撞功能
    player.game_map = game_map

    # 建立 Boss
    boss = Boss1.Vergil(player)

    # 建立 Sprite Group
    all_sprites = pygame.sprite.Group(
        player,
        boss
    )

    # 敵人群組，供玩家攻擊判定使用
    enemies = pygame.sprite.Group(boss)

    return player, boss, all_sprites, enemies


# ==========================================
# 4. UI 繪製函式
# ==========================================

def draw_text(text, font, color, center):

    img = font.render(text, True, color)

    screen.blit(
        img,
        img.get_rect(center=center)
    )


def draw_player_hp(player):

    max_hp = 100

    ratio = max(player.player_hp, 0) / max_hp

    pygame.draw.rect(
        screen,
        (60, 60, 60),
        (20, 20, 300, 24)
    )

    pygame.draw.rect(
        screen,
        (200, 40, 40),
        (20, 20, int(300 * ratio), 24)
    )

    pygame.draw.rect(
        screen,
        (255, 255, 255),
        (20, 20, 300, 24),
        2
    )


def draw_boss_hp(boss):

    max_hp = 100

    bar_w = 500
    bar_h = 20

    x = (WIDTH - bar_w) // 2
    y = 30

    ratio = max(boss.boss_health, 0) / max_hp

    pygame.draw.rect(
        screen,
        (60, 60, 60),
        (x, y, bar_w, bar_h)
    )

    pygame.draw.rect(
        screen,
        (150, 30, 150),
        (x, y, int(bar_w * ratio), bar_h)
    )

    pygame.draw.rect(
        screen,
        (255, 255, 255),
        (x, y, bar_w, bar_h),
        2
    )

    draw_text(
        "BOSS",
        font_small,
        (0, 0, 0),
        (WIDTH // 2, y - 14)
    )


# ==========================================
# 5. 遊戲初始狀態
# ==========================================

player, boss, all_sprites, enemies = new_game()

camera_x = 0
camera_y = 0

state = State.MENU


# ==========================================
# 6. 主遊戲迴圈
# ==========================================

running = True

while running:

    # --------------------------------------
    # A. 處理玩家輸入
    # --------------------------------------

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:

            # 主選單：按 Enter 開始遊戲
            if state == State.MENU:

                if event.key == pygame.K_RETURN:

                    player, boss, all_sprites, enemies = new_game()

                    camera_x = 0
                    camera_y = 0

                    state = State.PLAYING

            # 遊戲中：按 ESC 暫停
            elif state == State.PLAYING:

                if event.key == pygame.K_ESCAPE:
                    state = State.PAUSED

            # 暫停中：按 ESC 繼續
            elif state == State.PAUSED:

                if event.key == pygame.K_ESCAPE:
                    state = State.PLAYING

            # 遊戲結束：按 Enter 回到主選單
            elif state == State.GAME_OVER:

                if event.key == pygame.K_RETURN:
                    state = State.MENU

        # 滑鼠左鍵：攻擊
        if event.type == pygame.MOUSEBUTTONDOWN:

            if event.button == 1 and state == State.PLAYING:
                player.attack()


    # --------------------------------------
    # B. 更新遊戲資料
    # --------------------------------------

    if state == State.PLAYING:

        # 更新所有 Sprite
        all_sprites.update()

        # 玩家攻擊判定
        player.attack_hitbox(
            enemies,
            dummy_surface
        )

        # 更新攝影機位置
        camera_x, camera_y = game_map.get_camera_offset(
            player.rect,
            WIDTH,
            HEIGHT
        )

        # 檢查玩家是否死亡
        if player.player_hp <= 0:
            state = State.GAME_OVER


    # --------------------------------------
    # C. 繪製畫面
    # --------------------------------------

    if state == State.MENU:

        screen.fill((20, 20, 60))

        draw_text(
            "MY GAME",
            font_big,
            (255, 255, 255),
            (WIDTH // 2, 250)
        )

        draw_text(
            "Press ENTER to start",
            font_small,
            (200, 200, 200),
            (WIDTH // 2, 400)
        )


    elif state in (State.PLAYING, State.PAUSED):

        # 背景
        screen.blit(background, (0, 0))

        # 地圖（套用攝影機偏移）
        game_map.draw(
            screen,
            camera_x,
            camera_y
        )

        # 玩家與 Boss（套用攝影機偏移）
        for sprite in all_sprites:

            screen.blit(
                sprite.image,
                sprite.rect.move(-camera_x, -camera_y)
            )

        # 碰撞區域偵錯框
        game_map.draw_collision_debug(
            screen,
            camera_x,
            camera_y
        )

        # UI 不受攝影機影響
        draw_player_hp(player)
        draw_boss_hp(boss)

        # 暫停畫面
        if state == State.PAUSED:

            overlay = pygame.Surface(
                (WIDTH, HEIGHT),
                pygame.SRCALPHA
            )

            overlay.fill((0, 0, 0, 150))

            screen.blit(overlay, (0, 0))

            draw_text(
                "PAUSED",
                font_big,
                (255, 255, 255),
                (WIDTH // 2, HEIGHT // 2)
            )


    elif state == State.GAME_OVER:

        screen.fill((20, 20, 20))

        draw_text(
            "GAME OVER",
            font_big,
            (255, 50, 50),
            (WIDTH // 2, 250)
        )

        draw_text(
            "Press ENTER to return to menu",
            font_small,
            (255, 255, 255),
            (WIDTH // 2, 400)
        )


    # --------------------------------------
    # D. 更新畫面
    # --------------------------------------

    pygame.display.flip()

    clock.tick(FPS)


# ==========================================
# 7. 結束遊戲
# ==========================================

pygame.quit()
