import pygame

class Player(pygame.sprite.Sprite):
    def __init__(self, x: float, y: float):
        super().__init__()
        # 尺寸與碰撞矩形 (以 Hollow Knight 為例，建議碰撞框比貼圖稍微窄一點，提升操作手感)
        self.width = 32
        self.height = 52
        self.collision_rect = pygame.Rect(int(x), int(y), self.width, self.height)
        
        # 浮點數座標：避免每幀微小位移被 int 截斷造成抖動
        self.pos_x = float(x)
        self.pos_y = float(y)
        
        # 速度與物理參數
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.move_speed = 280.0       # 水平移動速度 (像素/秒)
        self.gravity = 980.0          # 重力加速度
        self.jump_velocity = -480.0   # 初始起跳速度 (向上為負)
        self.terminal_velocity = 800.0# 最大下落終端速度 (防止高速穿透)
        
        # 狀態標記
        self.is_grounded = False
        self.facing_right = True

    def handle_input(self):
        """讀取鍵盤輸入控制移動與跳躍"""
        keys = pygame.key.get_pressed()
        
        # 水平移動
        self.velocity_x = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.velocity_x = -self.move_speed
            self.facing_right = False
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.velocity_x = self.move_speed
            self.facing_right = True

        # 跳躍判定：僅在站在地面上 (is_grounded) 時允許跳躍
        if keys[pygame.K_w] or keys[pygame.K_SPACE] or keys[pygame.K_UP]:
            if self.is_grounded:
                self.velocity_y = self.jump_velocity
                self.is_grounded = False

    def update_physics(self, dt: float, obstacles: list[pygame.Rect]):
        """
        核心物理更新邏輯：分開處理 X 軸與 Y 軸碰撞
        :param dt: 幀時間間隔 (delta time，秒)
        :param obstacles: 地圖中的障礙物矩形清單 (List of pygame.Rect)
        """
        # ==========================================
        # 1. X 軸移動與碰撞判定
        # ==========================================
        dx = self.velocity_x * dt
        self.pos_x += dx
        self.collision_rect.x = round(self.pos_x)

        for wall in obstacles:
            if self.collision_rect.colliderect(wall):
                if dx > 0:  # 向右移動撞牆：貼齊牆壁左緣
                    self.collision_rect.right = wall.left
                elif dx < 0:  # 向左移動撞牆：貼齊牆壁右緣
                    self.collision_rect.left = wall.right
                # 同步回浮點數座標，避免下一次運算回彈
                self.pos_x = float(self.collision_rect.x)

        # ==========================================
        # 2. Y 軸重力套用、移動與碰撞判定
        # ==========================================
        # 套用重力，並限制最大下落速度 (防止穿地 / Tunneling)
        self.velocity_y = min(self.velocity_y + self.gravity * dt, self.terminal_velocity)
        dy = self.velocity_y * dt
        self.pos_y += dy
        self.collision_rect.y = round(self.pos_y)

        # 預設先設為不在地面，若碰撞到地板頂部再確認著地
        self.is_grounded = False

        for platform in obstacles:
            if self.collision_rect.colliderect(platform):
                if dy > 0:  # 正在向下落下：踩到碰撞箱頂部 (站立成功)
                    self.collision_rect.bottom = platform.top
                    self.velocity_y = 0.0
                    self.is_grounded = True
                elif dy < 0:  # 正在向上跳躍：頭部撞擊障礙物底部
                    self.collision_rect.top = platform.bottom
                    self.velocity_y = 0.0  # 頂頭後立即失去向上衝力
                
                # 同步回浮點數座標
                self.pos_y = float(self.collision_rect.y)

        # ==========================================
        # 3. 邊緣探測器 (Ground Probe)
        # ==========================================
        # 如果玩家站在平台邊緣走出去，下方沒有障礙物時需將 is_grounded 轉為 False
        if self.is_grounded:
            probe_rect = self.collision_rect.move(0, 1)  # 往下探測 1 像素
            standing_on_something = any(probe_rect.colliderect(obj) for obj in obstacles)
            if not standing_on_something:
                self.is_grounded = False

    def teleport(self, x: float, y: float):
        """地圖切換時的安全傳送方法"""
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.collision_rect.x = round(self.pos_x)
        self.collision_rect.y = round(self.pos_y)
        self.velocity_y = 0.0
        self.velocity_x = 0.0
        self.is_grounded = False