WIDTH = 1280
HEIGHT = 720
FPS = 60

# ---------- 物理與地面設定 ----------
GROUND_Y = 770          # 地圖主要地面基準高度 (對應 map_learning.tmx 的地面層)
GRAVITY = 1500.0        # 重力加速度 (px / s^2)
PLAYER_JUMP_VELOCITY = 620.0  # 固定跳躍初速度 (px / s)，每次起跳高度完全固定
PLAYER_SPEED = 280.0    # 玩家水平移動速度 (px / s)

# ---------- 完美格擋與子彈時間設定 ----------
PARRY_WINDOW = 0.15           # 完美格擋判定時間窗 (秒)
PARRY_COOLDOWN = 0.20         # 防禦冷卻時間 (秒)
BLOCK_DAMAGE_FACTOR = 0.30    # 一般格擋承受傷害比例 (減免 70% 傷害)
BLOCK_KNOCKBACK_SPEED = 260.0 # 一般格擋擊退初速度 (px / s)
PLAYER_IFRAME_DURATION = 0.60 # 玩家受擊後的無敵幀時間 (秒)

BULLET_TIME_SCALE = 0.20      # 完美格擋觸發時的慢動作時間倍率
BULLET_TIME_DURATION = 0.80   # 子彈時間持續真實秒數 (Unscaled Time)
BULLET_TIME_RECOVERY_SPEED = 2.5  # 子彈時間結束後平滑恢復至 1.0 的速率

# ---------- Debug 視覺化顏色設定 ----------
COLOR_DEBUG_HURTBOX = (0, 230, 60)      # 綠色：受擊框 (Hurtbox)
COLOR_DEBUG_HITBOX = (255, 40, 40)      # 紅色：攻擊判定框 (Active Hitbox)
COLOR_DEBUG_PARRY = (0, 220, 255)       # 亮藍/青色：完美格擋判定框
COLOR_DEBUG_BLOCK = (40, 120, 255)      # 深藍色：一般防禦判定框
COLOR_DEBUG_COLLISION = (255, 220, 0)   # 黃色：物理移動碰撞框 (Collision Box)
