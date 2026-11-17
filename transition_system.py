import pygame
from settings import WIDTH, HEIGHT


class MapTrigger:
    """地圖傳送點 / 門 / 場景切換觸發區"""
    def __init__(
        self,
        rect,
        target_map,
        spawn_pos,
        require_boss_dead=False,
        boss_type=None,
    ):
        """
        :param rect: pygame.Rect 或 (x, y, w, h) 觸發區域
        :param target_map: 目標地圖檔案路徑，例如 "map/boss_arena.tmx"
        :param spawn_pos: 傳送後玩家在新地圖的 (x, y) 座標
        :param require_boss_dead: 是否必須擊敗當前地圖的 Boss 才能傳送
        :param boss_type: 新地圖要生成的 Boss 類型名稱（可選）
        """
        self.rect = rect if isinstance(rect, pygame.Rect) else pygame.Rect(rect)
        self.target_map = target_map
        self.spawn_pos = spawn_pos
        self.require_boss_dead = require_boss_dead
        self.boss_type = boss_type

    def can_trigger(self, player_rect, boss=None):
        """判斷玩家是否碰到觸發區且符合條件"""
        if not self.rect.colliderect(player_rect):
            return False
        if self.require_boss_dead and boss is not None and boss.alive():
            return False
        return True

    def draw_debug(self, screen, camera_x, camera_y, boss=None):
        """在 Debug 模式 (F1) 下畫出傳送門框線，方便調整位置"""
        screen_rect = self.rect.move(-camera_x, -camera_y)
        is_locked = self.require_boss_dead and boss is not None and boss.alive()
        color = (255, 80, 80) if is_locked else (80, 255, 160)
        pygame.draw.rect(screen, color, screen_rect, 2)


def check_map_transitions(player, triggers, boss=None):
    """
    檢查玩家是否觸發任何地圖切換點
    :return: 觸發到的 MapTrigger 物件，若無則回傳 None
    """
    player_rect = getattr(player, "collision_rect", player.rect)
    for trigger in triggers:
        if trigger.can_trigger(player_rect, boss):
            return trigger
    return None


class TransitionManager:
    """處理地圖切換時的淡入淡出過場動畫 (Fade Out -> Switch -> Fade In)"""
    def __init__(self, fade_speed=600.0):
        self.fade_speed = fade_speed
        self.alpha = 0.0
        self.state = "IDLE"  # IDLE, FADING_OUT, FADING_IN
        self.pending_trigger = None
        self.overlay = pygame.Surface((WIDTH, HEIGHT))
        self.overlay.fill((0, 0, 0))

    @property
    def is_transitioning(self):
        return self.state != "IDLE"

    def start(self, trigger):
        """開始轉場"""
        if self.state == "IDLE":
            self.pending_trigger = trigger
            self.state = "FADING_OUT"

    def update(self, raw_dt, on_map_switch):
        """
        更新轉場透明度
        :param raw_dt: 未受子彈時間影響的真實時間差
        :param on_map_switch: 畫面全黑時執行的回呼函式，接收 (trigger) 參數
        """
        if self.state == "FADING_OUT":
            self.alpha += self.fade_speed * raw_dt
            if self.alpha >= 255.0:
                self.alpha = 255.0
                # 畫面全黑的瞬間，執行實際的地圖與物件切換
                if self.pending_trigger is not None:
                    on_map_switch(self.pending_trigger)
                    self.pending_trigger = None
                self.state = "FADING_IN"

        elif self.state == "FADING_IN":
            self.alpha -= self.fade_speed * raw_dt
            if self.alpha <= 0.0:
                self.alpha = 0.0
                self.state = "IDLE"

    def draw(self, screen):
        """在畫面最上層繪製轉場黑幕"""
        if self.alpha > 0:
            self.overlay.set_alpha(int(self.alpha))
            screen.blit(self.overlay, (0, 0))

def change_map(game, trigger, map_class):
    
    #執行實際的地圖切換、清場與玩家重新定位
    #:param game: Game 實例 (self)
    #:param trigger: 觸發的 MapTrigger 物件
    #:param map_class: GameMap 類別

        # 1. 更新當前地圖路徑與載入新地圖
        game.current_map_path = trigger.target_map
        game.game_map = map_class(trigger.target_map)
        game.player.game_map = game.game_map

        # 2. 將玩家移動到新地圖的出生點
        game.player.rect.midbottom = trigger.spawn_pos
        if hasattr(game.player, "pos_x"):
            game.player.pos_x, game.player.pos_y = trigger.spawn_pos
        if hasattr(game.player, "collision_rect"):
            game.player.collision_rect.midbottom = trigger.spawn_pos

        # 3. 清空舊地圖的殘留判定框、特效與舊傳送點
        game.active_hitboxes.clear()
        game.vfx_group.empty()
        game.triggers = []