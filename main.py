
import os
import sys
import pygame
from settings import (
    WIDTH,
    HEIGHT,
    FPS,
    GROUND_Y,
    BULLET_TIME_SCALE,
    BULLET_TIME_DURATION,
    BULLET_TIME_RECOVERY_SPEED,
)
from game_state import State
from map import GameMap
from hud import HUD
from transition_system import MapTrigger, check_map_transitions, TransitionManager, change_map
 
import Player
import Boss1
 
try:
    from VFX import draw_debug_boxes
except ImportError:
    draw_debug_boxes = None
 
 
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(
            (WIDTH, HEIGHT), pygame.RESIZABLE | pygame.SCALED
        )
        pygame.display.set_caption("Final Project - Hollow Knight Style Platformer")
        self.clock = pygame.time.Clock()
        self.running = True
 
        # 載入背景圖片 (帶保底處理)
        try:
            bg_img = pygame.image.load("Background/cloud_back .jpg").convert()
            self.background = pygame.transform.scale(bg_img, (WIDTH, HEIGHT))
        except Exception:
            self.background = pygame.Surface((WIDTH, HEIGHT))
            self.background.fill((20, 20, 35))
 
        # 濾鏡與假畫布
        self.dummy_surface = pygame.Surface((1, 1))
        self.pause_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.pause_overlay.fill((0, 0, 0, 150))
        self.bullet_time_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.bullet_time_overlay.fill((20, 90, 160, 48))
 
        # 遊戲狀態初始化為 MENU
        self.state = State.MENU
        self.debug_mode = False
 
        # 教學選擇視窗狀態
        self.prompt_selection = 0  # 0: YES, 1: NO
        self.prompt_buttons = {}   # 保存按鈕 Rect 供滑鼠點擊判定
        self.is_tutorial = False
 
        # 轉場管理器與觸發器
        self.transition = TransitionManager(fade_speed=700.0)
        self.triggers = []
 
        # 轉場冷卻計時器 (防止剛切換地圖瞬間重複觸發)
        self.transition_cooldown = 0.0
 
        # 子彈時間
        self.time_scale = 1.0
        self.bullet_time_timer = 0.0
 
        # 初始化地圖與物件
        self.current_map_path = "map/main_world.tmx"
        self.game_map = self.load_map(self.current_map_path)
        self.camera_x = 0
        self.camera_y = 0
 
        self.boss = None
        self.hud = None
        self.new_game(map_path="map/main_world.tmx", is_tutorial=False)
 
    # ------------------------------------------------------------------
    # 地圖相關
    # ------------------------------------------------------------------
    def resolve_map_path(self, map_filename: str) -> str:
        """尋找地圖路徑 (支援 map/ 資料夾與 boss/bass 拼寫相容)"""
        candidates = [
            map_filename,
            os.path.join("map", map_filename),
            os.path.join("map", os.path.basename(map_filename)),
            map_filename.replace("boss1", "bass1"),
            os.path.join("map", map_filename.replace("boss1", "bass1")),
            os.path.join("map", os.path.basename(map_filename).replace("boss1", "bass1")),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return map_filename
 
    def load_map(self, map_path: str) -> GameMap:
        """載入指定地圖"""
        resolved = self.resolve_map_path(map_path)
        print(f"[地圖系統] 載入地圖: {resolved}")
        return GameMap(resolved)
 
    def get_floor_y(self, default=576):
        """取得目前地圖的地面高度 (第一個碰撞箱頂部)"""
        if self.game_map and getattr(self.game_map, "collisions", None):
            return self.game_map.collisions[0].top
        return default
 
    def spawn_boss(self, floor_y, start_x=680):
        """生成 Boss 並重新建立 sprite 群組"""
        self.boss = Boss1.Vergil(self.player, start_x=start_x, ground_y=floor_y)
        self.enemies = pygame.sprite.Group(self.boss)
        self.all_sprites = pygame.sprite.Group(self.player, self.boss)
 
    def update_camera(self):
        player_rect = getattr(self.player, "collision_rect", self.player.rect)
        self.camera_x, self.camera_y = self.game_map.get_camera_offset(
            player_rect, WIDTH, HEIGHT
        )
 
    def switch_map(self, target_map_name: str, spawn_x=None, spawn_y=None):
        """
        Tiled 傳送門用的地圖切換函式：
        1. 載入目標地圖 (.tmx)
        2. 將玩家傳送至指定重生點 (支援 Tiled 圖塊座標自動換算為像素座標)
        3. 重新同步相機、Boss 與地圖碰撞
        """
        resolved_path = self.resolve_map_path(target_map_name)
        if not os.path.exists(resolved_path):
            print(f"[錯誤] 找不到目標地圖: {target_map_name} (路徑: {resolved_path})")
            return False
 
        self.current_map_path = resolved_path
        self.game_map = self.load_map(resolved_path)
        self.player.game_map = self.game_map
 
        # 計算玩家重生點 (Tiled 屬性中若為小數值通常代表圖塊網格座標)
        tile_w = getattr(self.game_map, "tile_width", 16)
        tile_h = getattr(self.game_map, "tile_height", 16)
        new_floor_y = self.get_floor_y()
 
        if spawn_x is not None and spawn_y is not None:
            px = spawn_x * tile_w if spawn_x <= (self.game_map.width // tile_w) else float(spawn_x)
            py = spawn_y * tile_h if spawn_y <= (self.game_map.height // tile_h) else float(spawn_y)
        else:
            px = 120.0
            py = float(new_floor_y)
 
        # 傳送玩家至新座標
        if hasattr(self.player, "teleport"):
            self.player.teleport(px, py)
        else:
            self.player.pos_x = float(px)
            self.player.pos_y = float(py)
            self.player.velocity_y = 0.0
            self.player.sync_boxes()
 
        is_boss_map = "boss" in resolved_path.lower() or "bass" in resolved_path.lower()
        leaving_tutorial = self.is_tutorial and "main_world" in resolved_path.lower()
 
        # 從教學切到主世界 → 結束教學並生成 Boss
        if leaving_tutorial:
            self.is_tutorial = False
            self.spawn_boss(new_floor_y)
            self.triggers = []
            self.hud.reset(self.player, self.boss, is_tutorial=False)
            print("[教學完成] 已進入主世界，首領 Vergil 現身！")
 
        # 若新地圖是 Boss 關卡，調整 (必要時先生成) Boss 位置
        if is_boss_map:
            if self.boss is None:
                self.is_tutorial = False
                self.spawn_boss(new_floor_y)
                self.hud.reset(self.player, self.boss, is_tutorial=False)
            self.boss.pos_x = min(float(self.game_map.width - 240), px + 450.0)
            self.boss.pos_y = float(new_floor_y)
            self.boss.ground_y = float(new_floor_y)
            if hasattr(self.boss, "sync_boxes"):
                self.boss.sync_boxes()
 
        # 清除舊地圖的判定框與特效
        self.active_hitboxes.clear()
        self.vfx_group.empty()
 
        # 立即更新鏡頭以對齊玩家
        self.update_camera()
 
        self.transition_cooldown = 1.0
        print(f"[地圖切換完成] 當前關卡: {os.path.basename(resolved_path)}，重生座標: ({px}, {py})")
        return True
 
    def new_game(self, map_path="map/main_world.tmx", is_tutorial=False):
        """
        初始化一局新遊戲：
        :param map_path: 地圖路徑 (例如 "map/tutorial.tmx" 或 "map/main_world.tmx")
        :param is_tutorial: 是否為教學模式 (若為 True 則暫不生成 Boss 並顯示操作教學)
        """
        self.is_tutorial = is_tutorial
        self.current_map_path = map_path
        self.game_map = self.load_map(map_path)
 
        # 動態偵測地圖碰撞箱頂部作為初始地面高度
        floor_y = self.get_floor_y()
 
        # 玩家出生點配置
        if is_tutorial:
            spawn_x, spawn_y = 100.0, float(floor_y)
        else:
            spawn_x, spawn_y = 240.0, float(floor_y)
 
        self.player = Player.Player(start_x=spawn_x, ground_y=spawn_y)
        self.player.game_map = self.game_map
        self.player.pos_y = float(spawn_y)
        self.player.sync_boxes()
 
        # 教學關卡不生成 Boss；主世界關卡生成 Boss Vergil
        if is_tutorial:
            self.boss = None
            self.enemies = pygame.sprite.Group()
            self.all_sprites = pygame.sprite.Group(self.player)
            # 教學關卡終點設置傳送門，完成教學後傳送至 main_world
            self.triggers = [
                MapTrigger(
                    rect=(1250, 520, 80, 120),
                    target_map="map/main_world.tmx",
                    spawn_pos=(240, 576),
                    require_boss_dead=False,
                )
            ]
        else:
            self.spawn_boss(floor_y)
            self.triggers = []
 
        self.vfx_group = pygame.sprite.Group()
        self.active_hitboxes = []
        self.time_scale = 1.0
        self.bullet_time_timer = 0.0
        self.transition_cooldown = 0.0
 
        # 初始化或重置 HUD
        if self.hud is None:
            self.hud = HUD(self.player, self.boss, is_tutorial=self.is_tutorial)
        else:
            self.hud.reset(self.player, self.boss, is_tutorial=self.is_tutorial)
 
        # 鏡頭對齊玩家
        self.update_camera()
 
    def handle_map_switch(self, trigger):
        """當淡出黑幕全黑時，執行 MapTrigger 的地圖切換與物件生成"""
        change_map(self, trigger, GameMap)
 
        # 若從教學關卡切換至主世界，進入主世界戰鬥並正式生成 Boss
        if self.is_tutorial and "main_world" in trigger.target_map:
            self.is_tutorial = False
            self.spawn_boss(self.get_floor_y())
            self.hud.reset(self.player, self.boss, is_tutorial=False)
            self.triggers = []
            print("[教學完成] 已通過傳送門進入主世界，首領 Vergil 現身！")
 
        # 鏡頭對齊新位置，並設定冷卻避免立刻再次觸發傳送門
        self.update_camera()
        self.transition_cooldown = 1.0
 
    def trigger_bullet_time(self):
        self.time_scale = BULLET_TIME_SCALE
        self.bullet_time_timer = BULLET_TIME_DURATION
 
    # ------------------------------------------------------------------
    # 事件處理
    # ------------------------------------------------------------------
    def handle_events(self):
        """處理所有輸入事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
 
            # ---------- 1. 主選單事件 (State.MENU) ----------
            if self.state == State.MENU:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    # 按下 ENTER 切換到 TUTORIAL_PROMPT 詢問介面
                    self.state = State.TUTORIAL_PROMPT
                    self.prompt_selection = 0
 
            # ---------- 2. 教學選擇介面 (State.TUTORIAL_PROMPT) ----------
            elif self.state == State.TUTORIAL_PROMPT:
                if event.type == pygame.KEYDOWN:
                    # 支援左/右 或 上/下 (或 A/D, W/S) 切換選項
                    if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w):
                        self.prompt_selection = 0  # YES
                    elif event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s):
                        self.prompt_selection = 1  # NO
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.prompt_selection == 0:
                            self.new_game(map_path="map/tutorial.tmx", is_tutorial=True)
                        else:
                            self.new_game(map_path="map/main_world.tmx", is_tutorial=False)
                        self.state = State.PLAYING
                    elif event.key == pygame.K_ESCAPE:
                        self.state = State.MENU
 
                elif event.type == pygame.MOUSEMOTION:
                    # 滑鼠懸停切換按鈕高亮
                    pos = event.pos
                    if self.prompt_buttons.get("YES") and self.prompt_buttons["YES"].collidepoint(pos):
                        self.prompt_selection = 0
                    elif self.prompt_buttons.get("NO") and self.prompt_buttons["NO"].collidepoint(pos):
                        self.prompt_selection = 1
 
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # 滑鼠左鍵直接點擊按鈕
                    pos = event.pos
                    if self.prompt_buttons.get("YES") and self.prompt_buttons["YES"].collidepoint(pos):
                        self.new_game(map_path="map/tutorial.tmx", is_tutorial=True)
                        self.state = State.PLAYING
                    elif self.prompt_buttons.get("NO") and self.prompt_buttons["NO"].collidepoint(pos):
                        self.new_game(map_path="map/main_world.tmx", is_tutorial=False)
                        self.state = State.PLAYING
 
            # ---------- 3. 遊戲進行中與暫停 ----------
            elif self.state in (State.PLAYING, State.PAUSED):
                if event.type == pygame.KEYDOWN:
                    # F1 或 TAB 切換 Debug 碰撞檢測線框
                    if event.key in (pygame.K_F1, pygame.K_TAB):
                        self.debug_mode = not self.debug_mode
 
                    if event.key == pygame.K_ESCAPE:
                        self.state = State.PAUSED if self.state == State.PLAYING else State.PLAYING
 
                    elif self.state == State.PLAYING:
                        if event.key in (pygame.K_w, pygame.K_SPACE, pygame.K_UP):
                            if hasattr(self.player, "jump"):
                                self.player.jump()
                        elif event.key in (pygame.K_j, pygame.K_LSHIFT, pygame.K_k):
                            if hasattr(self.player, "start_block"):
                                self.player.start_block()
 
                elif event.type == pygame.KEYUP and self.state == State.PLAYING:
                    if event.key in (pygame.K_j, pygame.K_LSHIFT, pygame.K_k):
                        if hasattr(self.player, "stop_block"):
                            self.player.stop_block()
 
                elif event.type == pygame.MOUSEBUTTONDOWN and self.state == State.PLAYING:
                    if event.button == 1:
                        self.player.attack()
                    elif event.button == 3 and hasattr(self.player, "start_block"):
                        self.player.start_block()
 
                elif event.type == pygame.MOUSEBUTTONUP and self.state == State.PLAYING:
                    if event.button == 3 and hasattr(self.player, "stop_block"):
                        self.player.stop_block()
 
            # ---------- 4. 遊戲結束 (State.GAME_OVER) ----------
            elif self.state == State.GAME_OVER:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    self.state = State.MENU
 
    # ------------------------------------------------------------------
    # 戰鬥
    # ------------------------------------------------------------------
    def resolve_combat_collisions(self):
        """處理攻擊判定與碰撞格擋"""
        self.active_hitboxes = [hb for hb in self.active_hitboxes if getattr(hb, "active", False)]
 
        for hb in self.active_hitboxes:
            if not getattr(hb, "active", False):
                continue
 
            if hb.owner == "player":
                for enemy in self.enemies:
                    if (
                        enemy.alive()
                        and hb.can_hit(enemy)
                        and hb.rect.colliderect(getattr(enemy, "hurtbox", enemy.rect))
                    ):
                        hb.register_hit(enemy)
                        enemy.be_attacked(hb.damage)
 
            elif hb.owner == "boss" and self.player.alive():
                if self.boss is None or not hb.can_hit(self.player):
                    continue
 
                is_blocking = getattr(self.player, "is_blocking", False)
                parry_box = getattr(self.player, "parry_box", self.player.rect)
                hurtbox = getattr(self.player, "hurtbox", self.player.rect)
 
                if (is_blocking and hb.rect.colliderect(parry_box)) or hb.rect.colliderect(hurtbox):
                    hb.register_hit(self.player)
                    if hasattr(self.player, "take_hit"):
                        outcome = self.player.take_hit(
                            hb, attacker=self.boss, vfx_group=self.vfx_group
                        )
                        if outcome == "parry":
                            self.trigger_bullet_time()
                            if self.boss.alive() and hasattr(self.boss, "on_parried"):
                                self.boss.on_parried()
 
    # ------------------------------------------------------------------
    # 更新
    # ------------------------------------------------------------------
    def update(self, raw_dt):
        """更新遊戲邏輯"""
        # 1. 優先更新轉場動畫，畫面全黑時呼叫 handle_map_switch
        self.transition.update(
            raw_dt,
            on_map_switch=self.handle_map_switch,
        )
 
        if self.state != State.PLAYING or self.transition.is_transitioning:
            return
 
        # 更新轉場冷卻
        if self.transition_cooldown > 0.0:
            self.transition_cooldown = max(0.0, self.transition_cooldown - raw_dt)
 
        # 2. 更新子彈時間
        if self.bullet_time_timer > 0.0:
            self.bullet_time_timer = max(0.0, self.bullet_time_timer - raw_dt)
            if self.bullet_time_timer <= 0.0:
                self.time_scale = min(1.0, self.time_scale + BULLET_TIME_RECOVERY_SPEED * raw_dt)
        elif self.time_scale < 1.0:
            self.time_scale = min(1.0, self.time_scale + BULLET_TIME_RECOVERY_SPEED * raw_dt)
 
        scaled_dt = raw_dt * self.time_scale
 
        # 3. 更新玩家
        try:
            self.player.update(
                dt=scaled_dt,
                raw_dt=raw_dt,
                active_hitboxes=self.active_hitboxes,
                vfx_group=self.vfx_group,
                map_width=self.game_map.width,
            )
        except TypeError:
            self.all_sprites.update()
 
        # 4. 檢查 Tiled 傳送門 (碰觸地圖中的 target 傳送門)
        if self.transition_cooldown <= 0.0 and hasattr(self.game_map, "check_portal"):
            player_rect = getattr(self.player, "collision_rect", self.player.rect)
            portal = self.game_map.check_portal(player_rect)
            if portal:
                self.switch_map(
                    portal.get("target_map"),
                    spawn_x=portal.get("spawn_x"),
                    spawn_y=portal.get("spawn_y"),
                )
 
        # 5. 舊版攻擊判定相容
        if hasattr(self.player, "attack_hitbox"):
            self.player.attack_hitbox(self.enemies, self.dummy_surface)
 
        # 6. 更新 Boss (若有 Boss 且存活)
        if self.boss is not None and self.boss.alive():
            if hasattr(self.boss, "update") and self.boss.update.__code__.co_argcount > 1:
                self.boss.update(
                    dt=scaled_dt,
                    active_hitboxes=self.active_hitboxes,
                    vfx_group=self.vfx_group,
                    map_width=self.game_map.width,
                )
 
        # 7. 更新特效與 Hitbox
        for vfx in list(self.vfx_group):
            vfx.update(scaled_dt)
        for hb in list(self.active_hitboxes):
            hb.update(scaled_dt)
 
        # 8. 戰鬥碰撞與受擊結算
        self.resolve_combat_collisions()
 
        # 9. 更新 HUD 血條殘影
        self.hud.update(raw_dt)
 
        # 10. 鏡頭平滑追蹤玩家
        self.update_camera()
 
        # 11. 檢查 MapTrigger 傳送點 (包括教學地圖終點傳送門)
        if self.transition_cooldown <= 0.0 and not self.transition.is_transitioning:
            triggered = check_map_transitions(self.player, self.triggers, self.boss)
            if triggered:
                self.transition.start(triggered)
 
        if self.player.player_hp <= 0:
            self.state = State.GAME_OVER
 
    # ------------------------------------------------------------------
    # 繪製
    # ------------------------------------------------------------------
    def draw(self):
        """繪製畫面"""
        if self.state == State.MENU:
            self.screen.fill((20, 20, 50))
            self.hud.draw_text(self.screen, "HOLLOW ACTION", self.hud.font_big, (255, 255, 255), (WIDTH // 2, 230))
            self.hud.draw_text(self.screen, "Press ENTER to Start Game", self.hud.font_small, (200, 200, 200), (WIDTH // 2, 360))
            self.hud.draw_text(
                self.screen,
                "A/D: Move | W/SPACE: Jump | LMB: Attack | RMB/J/Shift: Guard & Parry | F1: Debug",
                self.hud.font_hud,
                (160, 190, 230),
                (WIDTH // 2, 430),
            )
 
        elif self.state == State.TUTORIAL_PROMPT:
            # 繪製選單底色，上方彈出教學詢問對話框
            self.screen.fill((20, 20, 50))
            self.hud.draw_text(self.screen, "HOLLOW ACTION", self.hud.font_big, (80, 80, 120), (WIDTH // 2, 230))
            self.prompt_buttons = self.hud.draw_tutorial_prompt(self.screen, self.prompt_selection)
 
        elif self.state in (State.PLAYING, State.PAUSED):
            # 1. 繪製背景與地圖
            self.screen.blit(self.background, (0, 0))
            self.game_map.draw(self.screen, self.camera_x, self.camera_y)
 
            # 2. 繪製角色與 Boss
            for sprite in self.all_sprites:
                if sprite.alive():
                    self.screen.blit(sprite.image, sprite.rect.move(-self.camera_x, -self.camera_y))
 
            # 3. 繪製 VFX 特效
            for vfx in self.vfx_group:
                vfx.draw(self.screen, self.camera_x, self.camera_y)
 
            # 4. 子彈時間濾鏡
            if self.time_scale < 0.95:
                self.screen.blit(self.bullet_time_overlay, (0, 0))
                self.hud.draw_text(
                    self.screen,
                    f"BULLET TIME ({self.time_scale:.1f}x)",
                    self.hud.font_small,
                    (100, 240, 255),
                    (WIDTH // 2, 85),
                )
 
            # 5. Debug 碰撞框 (按 F1 切換)
            if self.debug_mode:
                if hasattr(self.game_map, "draw_collision_debug"):
                    self.game_map.draw_collision_debug(self.screen, self.camera_x, self.camera_y)
 
                if draw_debug_boxes is not None:
                    draw_debug_boxes(
                        self.screen, self.camera_x, self.camera_y, self.player, self.boss, self.active_hitboxes
                    )
 
                # 繪製 MapTrigger Debug 框線（綠色=可通行，紅色=需先擊敗Boss）
                for trigger in self.triggers:
                    trigger.draw_debug(self.screen, self.camera_x, self.camera_y, self.boss)
 
                # 顯示資訊文字
                is_g = getattr(self.player, "is_grounded", getattr(self.player, "on_ground", False))
                map_name = os.path.basename(self.current_map_path)
                mode_str = "TUTORIAL" if self.is_tutorial else "BOSS BATTLE"
                pos_info = (
                    f"[{mode_str}] Map: {map_name} | "
                    f"Player: ({int(self.player.pos_x)}, {int(self.player.pos_y)}) | Grounded: {is_g}"
                )
                info_surf = self.hud.font_hud.render(pos_info, True, (0, 255, 120))
                self.screen.blit(info_surf, (24, HEIGHT - 36))
 
            # 6. HUD 最上層血條與提示
            self.hud.draw_gameplay_hud(self.screen, self.camera_x, self.camera_y)
 
            # 7. 若處於教學關卡，顯示操作指引卡片
            if self.is_tutorial:
                self.hud.draw_tutorial_guide(self.screen)
 
            # 8. Boss 擊敗文字 (主世界)
            if not self.is_tutorial and self.boss is not None and not self.boss.alive():
                self.hud.draw_text(
                    self.screen, "VICTORY! BOSS DEFEATED", self.hud.font_big, (255, 215, 80), (WIDTH // 2, HEIGHT // 2 - 40)
                )
 
            if self.state == State.PAUSED:
                self.screen.blit(self.pause_overlay, (0, 0))
                self.hud.draw_text(self.screen, "PAUSED", self.hud.font_big, (255, 255, 255), (WIDTH // 2, HEIGHT // 2))
 
        elif self.state == State.GAME_OVER:
            self.screen.fill((80, 20, 20))
            self.hud.draw_text(self.screen, "GAME OVER", self.hud.font_big, (255, 255, 255), (WIDTH // 2, 280))
            self.hud.draw_text(
                self.screen, "Press ENTER to return to menu", self.hud.font_small, (220, 220, 220), (WIDTH // 2, 420)
            )
 
        # 9. 繪製地圖轉場淡入淡出黑幕 (必須在 flip 之前)
        self.transition.draw(self.screen)
 
        pygame.display.flip()
 
    def run(self):
        while self.running:
            raw_dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.handle_events()
            self.update(raw_dt)
            self.draw()
        pygame.quit()
 
 
if __name__ == "__main__":
    Game().run()
