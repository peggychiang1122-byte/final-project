
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
from checkpoint import load_checkpoints
 
import Player
import Boss1
 
try:
    from VFX import draw_debug_boxes
except ImportError:
    draw_debug_boxes = None
 
 
MAIN_WORLD_PATH = "map/main_world.tmx"
TUTORIAL_PATH = "map/tutorial.tmx"
 
# 檔名 (小寫) 含有這些關鍵字的地圖視為 Boss 競技場：固定鏡頭、生成 Boss
BOSS_ARENA_KEYWORDS = ("boss1arena", "boss1_arena", "boss1", "bass1")
 
# 打贏 Boss 後，等幾秒再傳回主世界
VICTORY_RETURN_DELAY = 3.0
 
# 各地圖的傳送點 (key = 檔名小寫)。請填入你自己的座標，例如：
#   "main_world.tmx": [
#       MapTrigger(rect=(2400, 480, 80, 160),
#                  target_map="map/boss1arena.tmx",
#                  spawn_pos=(120, 576)),
#   ],
MAP_TRIGGERS = {}
 
 
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
 
        # 遊戲狀態
        self.state = State.MENU
        self.debug_mode = False
 
        # 教學選擇視窗狀態
        self.prompt_selection = 0  # 0: YES, 1: NO
        self.prompt_buttons = {}
        self.is_tutorial = False
 
        # 轉場管理器與觸發器
        self.transition = TransitionManager(fade_speed=700.0)
        self.triggers = []
        self.transition_cooldown = 0.0
 
        # 檢查點
        self.checkpoints = []
        self.active_checkpoint = None
        self.checkpoint_msg_timer = 0.0
 
        # Boss 戰勝利計時
        self.victory_timer = 0.0
 
        # 主世界的 Boss 是否已被擊敗 (擊敗後從競技場回來就不會再生成)
        self.main_boss_defeated = False
 
        # 子彈時間
        self.time_scale = 1.0
        self.bullet_time_timer = 0.0
 
        self.camera_x = 0
        self.camera_y = 0
        self.current_map_path = MAIN_WORLD_PATH
        self.game_map = None
        self.boss = None
        self.hud = None
        self.new_game(map_path=MAIN_WORLD_PATH, is_tutorial=False)
 
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
 
    def map_name(self):
        return os.path.basename(self.current_map_path).lower()
 
    def is_boss_arena(self):
        name = self.map_name()
        return any(k in name for k in BOSS_ARENA_KEYWORDS)
 
    def is_main_world(self):
        return "main_world" in self.map_name()
 
    def get_floor_y(self, default=576):
        """取得目前地圖的地面高度 (第一個碰撞箱頂部)"""
        if self.game_map and getattr(self.game_map, "collisions", None):
            return self.game_map.collisions[0].top
        return default
 
    def build_triggers(self):
        return list(MAP_TRIGGERS.get(self.map_name(), []))
 
    def spawn_boss(self, floor_y, start_x=680):
        """生成 Boss 並重新建立 sprite 群組"""
        self.boss = Boss1.Vergil(self.player, start_x=start_x, ground_y=floor_y)
        self.enemies = pygame.sprite.Group(self.boss)
        self.all_sprites = pygame.sprite.Group(self.player, self.boss)
 
    def update_camera(self):
        if self.is_boss_arena():
            # Boss 競技場：鏡頭固定在地圖正中央
            self.camera_x = (self.game_map.width - WIDTH) // 2
            self.camera_y = (self.game_map.height - HEIGHT) // 2
        else:
            player_rect = getattr(self.player, "collision_rect", self.player.rect)
            self.camera_x, self.camera_y = self.game_map.get_camera_offset(
                player_rect, WIDTH, HEIGHT
            )
 
    def setup_map_state(self):
        """
        地圖載入、玩家定位完成後呼叫，依地圖類型整理遊戲物件：
        - Boss 競技場：生成全新的 Boss
        - 其他地圖：沒有 Boss
        - 主世界：載入檢查點
        - 設定傳送點與 HUD
        """
        self.is_tutorial = "tutorial" in self.map_name()
        self.victory_timer = 0.0
        floor_y = self.get_floor_y()
 
        if self.is_boss_arena():
            px = getattr(self.player, "pos_x", 120.0)
            boss_x = min(float(self.game_map.width - 240), px + 450.0)
            self.spawn_boss(floor_y, start_x=boss_x)
        elif self.is_main_world() and not self.main_boss_defeated:
            # 主世界的 Boss：尚未擊敗時才生成
            self.spawn_boss(floor_y, start_x=680)
        else:
            self.boss = None
            self.enemies = pygame.sprite.Group()
            self.all_sprites = pygame.sprite.Group(self.player)
 
        if self.is_main_world() and not self.checkpoints:
            self.checkpoints = load_checkpoints(self.resolve_map_path(self.current_map_path))
 
        if self.is_tutorial:
            # 教學關終點傳送門，完成後前往主世界
            self.triggers = [
                MapTrigger(
                    rect=(1250, 520, 80, 120),
                    target_map=MAIN_WORLD_PATH,
                    spawn_pos=(240, 576),
                    require_boss_dead=False,
                )
            ]
        else:
            self.triggers = self.build_triggers()
 
        if self.hud is not None:
            self.hud.reset(self.player, self.boss, is_tutorial=self.is_tutorial)
 
    def switch_map(self, target_map_name: str, spawn_x=None, spawn_y=None):
        """Tiled 傳送門用的地圖切換函式 (無淡入淡出)"""
        resolved_path = self.resolve_map_path(target_map_name)
        if not os.path.exists(resolved_path):
            print(f"[錯誤] 找不到目標地圖: {target_map_name} (路徑: {resolved_path})")
            return False
 
        self.current_map_path = resolved_path
        self.game_map = self.load_map(resolved_path)
        self.player.game_map = self.game_map
 
        tile_w = getattr(self.game_map, "tile_width", 16)
        tile_h = getattr(self.game_map, "tile_height", 16)
        new_floor_y = self.get_floor_y()
 
        if spawn_x is not None and spawn_y is not None:
            px = spawn_x * tile_w if spawn_x <= (self.game_map.width // tile_w) else float(spawn_x)
            py = spawn_y * tile_h if spawn_y <= (self.game_map.height // tile_h) else float(spawn_y)
        else:
            px = 120.0
            py = float(new_floor_y)
 
        if hasattr(self.player, "teleport"):
            self.player.teleport(px, py)
        else:
            self.player.pos_x = float(px)
            self.player.pos_y = float(py)
            self.player.velocity_y = 0.0
            self.player.sync_boxes()
 
        self.active_hitboxes.clear()
        self.vfx_group.empty()
 
        self.setup_map_state()
        self.update_camera()
 
        self.transition_cooldown = 1.0
        print(f"[地圖切換完成] 當前關卡: {os.path.basename(resolved_path)}，重生座標: ({px}, {py})")
        return True
 
    def new_game(self, map_path=MAIN_WORLD_PATH, is_tutorial=False, spawn_pos=None, keep_progress=False):
        """
        初始化一局遊戲 (會重新建立玩家，血量等狀態全部重置)
        :param spawn_pos: 指定玩家出生點 (腳底中央)，例如從檢查點重生
        :param keep_progress: True 時保留已啟動的檢查點
        """
        self.is_tutorial = is_tutorial
        self.current_map_path = map_path
        self.game_map = self.load_map(map_path)
 
        if not keep_progress:
            self.checkpoints = []
            self.active_checkpoint = None
            self.main_boss_defeated = False
        self.checkpoint_msg_timer = 0.0
 
        floor_y = self.get_floor_y()
        if spawn_pos is not None:
            spawn_x, spawn_y = float(spawn_pos[0]), float(spawn_pos[1])
        elif is_tutorial:
            spawn_x, spawn_y = 100.0, float(floor_y)
        else:
            spawn_x, spawn_y = 240.0, float(floor_y)
 
        self.player = Player.Player(start_x=spawn_x, ground_y=spawn_y)
        self.player.game_map = self.game_map
        self.player.pos_y = float(spawn_y)
        self.player.sync_boxes()
 
        self.boss = None
        self.enemies = pygame.sprite.Group()
        self.all_sprites = pygame.sprite.Group(self.player)
        self.vfx_group = pygame.sprite.Group()
        self.active_hitboxes = []
        self.time_scale = 1.0
        self.bullet_time_timer = 0.0
        self.transition_cooldown = 0.0
 
        if self.hud is None:
            self.hud = HUD(self.player, self.boss, is_tutorial=self.is_tutorial)
 
        # 依地圖類型生成 Boss / 傳送點 / 檢查點，並重置 HUD
        self.setup_map_state()
        self.update_camera()
 
    def handle_map_switch(self, trigger):
        """當淡出黑幕全黑時，執行地圖切換"""
        if getattr(trigger, "reset_player", False):
            # 死亡重生：重建玩家 (血量回滿)，保留檢查點進度
            self.new_game(
                map_path=trigger.target_map,
                is_tutorial=False,
                spawn_pos=trigger.spawn_pos,
                keep_progress=True,
            )
        else:
            change_map(self, trigger, GameMap)
            self.setup_map_state()
            self.update_camera()
 
        self.transition_cooldown = 1.0
 
    # ------------------------------------------------------------------
    # 檢查點
    # ------------------------------------------------------------------
    def update_checkpoints(self, raw_dt):
        """主世界中碰到檢查點就啟動 (只會往後推進，不會退回較早的)"""
        if self.checkpoint_msg_timer > 0.0:
            self.checkpoint_msg_timer = max(0.0, self.checkpoint_msg_timer - raw_dt)
 
        if not self.is_main_world() or not self.checkpoints:
            return
 
        player_rect = getattr(self.player, "collision_rect", self.player.rect)
        for cp in self.checkpoints:
            if not cp.rect.colliderect(player_rect):
                continue
            if self.active_checkpoint is None or cp.order > self.active_checkpoint.order:
                self.active_checkpoint = cp
                self.checkpoint_msg_timer = 2.0
                print(f"[檢查點] 已啟動: {cp.name} (order={cp.order})")
 
    def get_respawn_checkpoint(self):
        """死亡時的重生點：目前啟動的檢查點，若尚未啟動任何一個則用第一個"""
        if self.active_checkpoint is not None:
            return self.active_checkpoint
        return self.checkpoints[0] if self.checkpoints else None
 
    def get_next_checkpoint(self):
        """打贏 Boss 後前往的下一個檢查點 (order 比目前大的第一個)"""
        current = self.active_checkpoint.order if self.active_checkpoint else -10**9
        for cp in self.checkpoints:  # 已依 order 排序
            if cp.order > current:
                return cp
        return self.active_checkpoint  # 沒有下一個就留在目前這個
 
    def make_return_trigger(self, spawn_pos, reset_player):
        """建立一個「回主世界」的臨時傳送，交給 TransitionManager 執行"""
        trigger = MapTrigger(
            rect=(0, 0, 0, 0),
            target_map=MAIN_WORLD_PATH,
            spawn_pos=spawn_pos,
        )
        trigger.reset_player = reset_player
        return trigger
 
    def handle_boss_arena_outcome(self, raw_dt):
        """Boss 競技場內：玩家死亡→回檢查點；打贏 Boss→下一個檢查點。回傳 True 表示已處理"""
        # 玩家死亡
        if self.player.player_hp <= 0:
            cp = self.get_respawn_checkpoint()
            if cp is None:
                self.state = State.GAME_OVER
            else:
                print(f"[死亡] 傳回檢查點: {cp.name}")
                self.transition.start(self.make_return_trigger(cp.spawn_pos, reset_player=True))
            return True
 
        # 打贏 Boss
        if self.boss is not None and not self.boss.alive():
            self.victory_timer += raw_dt
            if self.victory_timer >= VICTORY_RETURN_DELAY:
                self.victory_timer = 0.0
                cp = self.get_next_checkpoint()
                if cp is not None:
                    self.active_checkpoint = cp
                    spawn = cp.spawn_pos
                    print(f"[勝利] 前往下一個檢查點: {cp.name}")
                else:
                    spawn = (240, 576)
                    print("[勝利] 主世界沒有檢查點，傳回預設出生點")
                self.transition.start(self.make_return_trigger(spawn, reset_player=False))
            return True
 
        self.victory_timer = 0.0
        return False
 
    # ------------------------------------------------------------------
    # 其他
    # ------------------------------------------------------------------
    def trigger_bullet_time(self):
        self.time_scale = BULLET_TIME_SCALE
        self.bullet_time_timer = BULLET_TIME_DURATION
 
    def handle_events(self):
        """處理所有輸入事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
 
            # ---------- 1. 主選單 ----------
            if self.state == State.MENU:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    self.state = State.TUTORIAL_PROMPT
                    self.prompt_selection = 0
 
            # ---------- 2. 教學選擇介面 ----------
            elif self.state == State.TUTORIAL_PROMPT:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w):
                        self.prompt_selection = 0  # YES
                    elif event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s):
                        self.prompt_selection = 1  # NO
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.prompt_selection == 0:
                            self.new_game(map_path=TUTORIAL_PATH, is_tutorial=True)
                        else:
                            self.new_game(map_path=MAIN_WORLD_PATH, is_tutorial=False)
                        self.state = State.PLAYING
                    elif event.key == pygame.K_ESCAPE:
                        self.state = State.MENU
 
                elif event.type == pygame.MOUSEMOTION:
                    pos = event.pos
                    if self.prompt_buttons.get("YES") and self.prompt_buttons["YES"].collidepoint(pos):
                        self.prompt_selection = 0
                    elif self.prompt_buttons.get("NO") and self.prompt_buttons["NO"].collidepoint(pos):
                        self.prompt_selection = 1
 
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = event.pos
                    if self.prompt_buttons.get("YES") and self.prompt_buttons["YES"].collidepoint(pos):
                        self.new_game(map_path=TUTORIAL_PATH, is_tutorial=True)
                        self.state = State.PLAYING
                    elif self.prompt_buttons.get("NO") and self.prompt_buttons["NO"].collidepoint(pos):
                        self.new_game(map_path=MAIN_WORLD_PATH, is_tutorial=False)
                        self.state = State.PLAYING
 
            # ---------- 3. 遊戲進行中與暫停 ----------
            elif self.state in (State.PLAYING, State.PAUSED):
                if event.type == pygame.KEYDOWN:
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
 
            # ---------- 4. 遊戲結束 ----------
            elif self.state == State.GAME_OVER:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    self.state = State.MENU
 
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
        # 1. 轉場動畫 (畫面全黑時呼叫 handle_map_switch)
        self.transition.update(raw_dt, on_map_switch=self.handle_map_switch)
 
        if self.state != State.PLAYING or self.transition.is_transitioning:
            return
 
        # 轉場冷卻
        if self.transition_cooldown > 0.0:
            self.transition_cooldown = max(0.0, self.transition_cooldown - raw_dt)
 
        # 2. 子彈時間
        if self.bullet_time_timer > 0.0:
            self.bullet_time_timer = max(0.0, self.bullet_time_timer - raw_dt)
            if self.bullet_time_timer <= 0.0:
                self.time_scale = min(1.0, self.time_scale + BULLET_TIME_RECOVERY_SPEED * raw_dt)
        elif self.time_scale < 1.0:
            self.time_scale = min(1.0, self.time_scale + BULLET_TIME_RECOVERY_SPEED * raw_dt)
 
        scaled_dt = raw_dt * self.time_scale
 
        # 3. 玩家
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
 
        # 4. Tiled 傳送門
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
 
        # 6. Boss
        if self.boss is not None and self.boss.alive():
            if hasattr(self.boss, "update") and self.boss.update.__code__.co_argcount > 1:
                self.boss.update(
                    dt=scaled_dt,
                    active_hitboxes=self.active_hitboxes,
                    vfx_group=self.vfx_group,
                    map_width=self.game_map.width,
                )
 
        # 記錄主世界 Boss 已被擊敗
        if self.is_main_world() and self.boss is not None and not self.boss.alive():
            self.main_boss_defeated = True
 
        # 7. 特效與 Hitbox
        for vfx in list(self.vfx_group):
            vfx.update(scaled_dt)
        for hb in list(self.active_hitboxes):
            hb.update(scaled_dt)
 
        # 8. 戰鬥結算
        self.resolve_combat_collisions()
 
        # 9. HUD
        self.hud.update(raw_dt)
 
        # 10. 鏡頭
        self.update_camera()
 
        # 11. 檢查點
        self.update_checkpoints(raw_dt)
 
        # 12. MapTrigger 傳送點
        if self.transition_cooldown <= 0.0 and not self.transition.is_transitioning:
            triggered = check_map_transitions(self.player, self.triggers, self.boss)
            if triggered:
                self.transition.start(triggered)
                return
 
        # 13. Boss 競技場的勝負處理 / 其他地圖的死亡
        if self.is_boss_arena():
            self.handle_boss_arena_outcome(raw_dt)
        elif self.player.player_hp <= 0:
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
            self.screen.fill((20, 20, 50))
            self.hud.draw_text(self.screen, "HOLLOW ACTION", self.hud.font_big, (80, 80, 120), (WIDTH // 2, 230))
            self.prompt_buttons = self.hud.draw_tutorial_prompt(self.screen, self.prompt_selection)
 
        elif self.state in (State.PLAYING, State.PAUSED):
            # 1. 背景與地圖
            self.screen.blit(self.background, (0, 0))
            self.game_map.draw(self.screen, self.camera_x, self.camera_y)
 
            # 2. 角色與 Boss
            for sprite in self.all_sprites:
                if sprite.alive():
                    self.screen.blit(sprite.image, sprite.rect.move(-self.camera_x, -self.camera_y))
 
            # 3. VFX
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
 
            # 5. Debug
            if self.debug_mode:
                if hasattr(self.game_map, "draw_collision_debug"):
                    self.game_map.draw_collision_debug(self.screen, self.camera_x, self.camera_y)
 
                if draw_debug_boxes is not None:
                    draw_debug_boxes(
                        self.screen, self.camera_x, self.camera_y, self.player, self.boss, self.active_hitboxes
                    )
 
                for trigger in self.triggers:
                    trigger.draw_debug(self.screen, self.camera_x, self.camera_y, self.boss)
 
                # 檢查點 (黃色=已啟動，藍色=未啟動)
                if self.is_main_world():
                    for cp in self.checkpoints:
                        cp.draw_debug(
                            self.screen, self.camera_x, self.camera_y,
                            self.hud.font_hud, cp is self.active_checkpoint,
                        )
 
                is_g = getattr(self.player, "is_grounded", getattr(self.player, "on_ground", False))
                map_name = os.path.basename(self.current_map_path)
                if self.is_tutorial:
                    mode_str = "TUTORIAL"
                elif self.is_boss_arena():
                    mode_str = "BOSS ARENA"
                else:
                    mode_str = "WORLD"
                cp_str = self.active_checkpoint.order if self.active_checkpoint else "-"
                pos_info = (
                    f"[{mode_str}] Map: {map_name} | "
                    f"Player: ({int(self.player.pos_x)}, {int(self.player.pos_y)}) | "
                    f"Grounded: {is_g} | Checkpoint: {cp_str}"
                )
                info_surf = self.hud.font_hud.render(pos_info, True, (0, 255, 120))
                self.screen.blit(info_surf, (24, HEIGHT - 36))
 
            # 6. HUD
            self.hud.draw_gameplay_hud(self.screen, self.camera_x, self.camera_y)
 
            # 7. 教學指引
            if self.is_tutorial:
                self.hud.draw_tutorial_guide(self.screen)
 
            # 8. 檢查點提示
            if self.checkpoint_msg_timer > 0.0:
                self.hud.draw_text(
                    self.screen, "CHECKPOINT SAVED", self.hud.font_small, (255, 220, 60), (WIDTH // 2, 130)
                )
 
            # 9. Boss 擊敗文字
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
 
        # 轉場黑幕 (必須在 flip 之前)
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