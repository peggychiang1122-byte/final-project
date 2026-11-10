import math
import random
import pygame
from settings import (
    COLOR_DEBUG_HITBOX,
    COLOR_DEBUG_HURTBOX,
    COLOR_DEBUG_PARRY,
    COLOR_DEBUG_BLOCK,
    COLOR_DEBUG_COLLISION,
)


class Hitbox:
    """
    獨立的攻擊判定框物件（不常駐於角色身上）。
    僅在攻擊動畫 Active Frames 或攻擊 VFX 存在期間啟用，結束時立即銷毀。
    內建 hit_targets 集合，確保單次攻擊對同一目標只造成一次傷害/格擋判定。
    """

    def __init__(
        self,
        owner,
        rect,
        damage=15,
        knockback_x=180.0,
        lifetime=None,
        tag="melee",
    ):
        self.owner = owner  # "player" 或 "boss"
        self.rect = pygame.Rect(rect)
        self.damage = damage
        self.knockback_x = knockback_x
        self.lifetime = lifetime  # 若為 float 則自動倒數銷毀；若由 VFX/動畫控制則隨宿主銷毀
        self.elapsed = 0.0
        self.active = True
        self.tag = tag
        self.hit_targets = set()

    def can_hit(self, target):
        return self.active and (target not in self.hit_targets)

    def register_hit(self, target):
        self.hit_targets.add(target)

    def update(self, dt):
        if not self.active:
            return
        self.elapsed += dt
        if self.lifetime is not None and self.elapsed >= self.lifetime:
            self.destroy()

    def destroy(self):
        self.active = False


class BaseVFX(pygame.sprite.Sprite):
    """
    視覺特效基底類別：
    具備獨立的 update(dt) 與 draw(screen, camera_x, camera_y) 生命週期，
    並可綁定一個 Hitbox，於特效結束時自動銷毀該 Hitbox。
    """

    def __init__(self, x, y, duration=0.25, hitbox=None):
        super().__init__()
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.duration = max(duration, 0.01)
        self.elapsed = 0.0
        self.hitbox = hitbox
        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect = pygame.Rect(int(x), int(y), 1, 1)

    @property
    def progress(self):
        return min(max(self.elapsed / self.duration, 0.0), 1.0)

    def bind_hitbox(self, hitbox):
        self.hitbox = hitbox
        return hitbox

    def update(self, dt=1 / 60):
        self.elapsed += dt
        if self.hitbox and self.hitbox.active:
            self.hitbox.update(dt)
        if self.elapsed >= self.duration:
            self.destroy()

    def destroy(self):
        if self.hitbox:
            self.hitbox.destroy()
        self.kill()

    def draw(self, screen, camera_x=0, camera_y=0):
        if self.image.get_width() > 1:
            screen.blit(self.image, self.rect.move(-camera_x, -camera_y))


class SlashVFX(BaseVFX):
    """
    近戰斬擊刀光特效（支援玩家揮砍與 Boss 近距連擊）：
    生成時同步掛載對應大小的 Hitbox，隨出招者位置更新，播放完畢時自動移除 Hitbox。
    """

    def __init__(
        self,
        anchor_entity,
        offset_x,
        offset_y,
        width=90,
        height=74,
        flip=False,
        duration=0.18,
        color_outer=(60, 170, 255),
        color_inner=(220, 245, 255),
        tilt_angle=0.0,
        hitbox=None,
    ):
        cx = anchor_entity.collision_rect.centerx + offset_x
        cy = anchor_entity.collision_rect.centery + offset_y
        super().__init__(cx, cy, duration=duration, hitbox=hitbox)
        self.anchor = anchor_entity
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.width = width
        self.height = height
        self.flip = flip
        self.color_outer = color_outer
        self.color_inner = color_inner
        self.tilt_angle = tilt_angle

        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = (int(cx), int(cy))
        if self.hitbox:
            self.hitbox.rect = self.rect.copy()

    def update(self, dt=1 / 60):
        if self.anchor and self.anchor.alive():
            self.pos_x = self.anchor.collision_rect.centerx + self.offset_x
            self.pos_y = self.anchor.collision_rect.centery + self.offset_y
            self.rect.center = (int(self.pos_x), int(self.pos_y))
            if self.hitbox and self.hitbox.active:
                self.hitbox.rect = self.rect.copy()

        super().update(dt)

    def draw(self, screen, camera_x=0, camera_y=0):
        p = self.progress
        alpha = int(255 * math.sin(p * math.pi))
        if alpha <= 5:
            return

        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        w, h = self.width, self.height

        # 動態繪製弧形刀光 (外層能量光暈 + 內層高光刀鋒)
        points_outer = []
        points_inner = []
        steps = 14
        start_t = max(0.0, p - 0.55)
        end_t = min(1.0, p + 0.35)

        for i in range(steps + 1):
            t = start_t + (end_t - start_t) * (i / steps)
            angle = -0.45 * math.pi + t * 0.9 * math.pi
            rx_out = w * 0.46
            ry_out = h * 0.46
            thickness = math.sin((i / steps) * math.pi) * (w * 0.24)
            x_out = w * 0.15 + math.cos(angle) * rx_out
            y_out = h * 0.5 + math.sin(angle) * ry_out
            x_in = w * 0.15 + math.cos(angle) * max(4.0, rx_out - thickness)
            y_in = h * 0.5 + math.sin(angle) * (ry_out * 0.82)
            points_outer.append((x_out, y_out))
            points_inner.append((x_in, y_in))

        polygon_pts = points_outer + list(reversed(points_inner))
        if len(polygon_pts) >= 3:
            pygame.draw.polygon(
                surf, (*self.color_outer, alpha), polygon_pts
            )
            pygame.draw.lines(
                surf, (*self.color_inner, min(255, alpha + 30)), False, points_outer, 3
            )

        if self.tilt_angle != 0:
            surf = pygame.transform.rotate(surf, self.tilt_angle)

        if self.flip:
            surf = pygame.transform.flip(surf, True, False)

        draw_rect = surf.get_rect(
            center=(self.rect.centerx - camera_x, self.rect.centery - camera_y)
        )
        screen.blit(surf, draw_rect)


class DashSlashVFX(BaseVFX):
    """
    Boss 突進斬擊 (ATTACK_2) 專用視覺特效：
    在突進路徑上繪製高速殘影刀芒與橫貫光束，並同步掛載突進斬擊 Hitbox。
    """

    def __init__(
        self,
        anchor_entity,
        start_x,
        y,
        width=180,
        height=76,
        flip=False,
        duration=0.26,
        hitbox=None,
    ):
        super().__init__(start_x, y, duration=duration, hitbox=hitbox)
        self.anchor = anchor_entity
        self.start_x = float(start_x)
        self.width = width
        self.height = height
        self.flip = flip
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = (int(start_x), int(y))

    def update(self, dt=1 / 60):
        if self.anchor and self.anchor.alive():
            cur_x = self.anchor.collision_rect.centerx
            cur_y = self.anchor.collision_rect.centery
            mid_x = (self.start_x + cur_x) * 0.5
            span_w = max(self.width, int(abs(cur_x - self.start_x) + 90))
            self.rect = pygame.Rect(0, 0, span_w, self.height)
            self.rect.center = (int(mid_x), int(cur_y))
            if self.hitbox and self.hitbox.active:
                # 突進判定框跟隨 Boss 當前身位與前方刀鋒
                hb_w = 130
                hb_x = (
                    self.anchor.collision_rect.centerx - hb_w + 20
                    if self.flip
                    else self.anchor.collision_rect.centerx - 20
                )
                self.hitbox.rect = pygame.Rect(
                    int(hb_x),
                    int(cur_y - self.height // 2),
                    hb_w,
                    self.height,
                )
        super().update(dt)

    def draw(self, screen, camera_x=0, camera_y=0):
        p = self.progress
        alpha = int(240 * (1.0 - p * 0.75))
        if alpha <= 5:
            return

        w, h = self.rect.width, self.rect.height
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        # 高速橫向斬擊光束與次元裂痕線條
        beam_h = max(4, int(h * 0.28 * (1.0 - p * 0.5)))
        cy = h // 2
        pygame.draw.ellipse(
            surf, (40, 140, 255, int(alpha * 0.65)), (0, cy - beam_h, w, beam_h * 2)
        )
        pygame.draw.line(
            surf, (220, 250, 255, alpha), (4, cy), (w - 4, cy), max(2, beam_h // 2)
        )
        pygame.draw.line(
            surf,
            (100, 210, 255, int(alpha * 0.8)),
            (15, cy - 14),
            (w - 15, cy + 10),
            2,
        )
        pygame.draw.line(
            surf,
            (100, 210, 255, int(alpha * 0.8)),
            (15, cy + 14),
            (w - 15, cy - 10),
            2,
        )

        screen.blit(surf, (self.rect.x - camera_x, self.rect.y - camera_y))


class ProjectileWaveVFX(BaseVFX):
    """
    Boss 遠程劍氣波 (ATTACK_3) 特效：
    具備獨立飛行速度與生命週期，Hitbox 與劍氣位置即時綁定，結束或超時時一併移除。
    """

    def __init__(
        self,
        x,
        y,
        direction,
        speed=560.0,
        width=56,
        height=96,
        duration=1.35,
        hitbox=None,
    ):
        super().__init__(x, y, duration=duration, hitbox=hitbox)
        self.direction = -1 if direction < 0 else 1
        self.speed = speed
        self.width = width
        self.height = height
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = (int(x), int(y))
        if self.hitbox:
            self.hitbox.rect = self.rect.inflate(-10, -12)

    def update(self, dt=1 / 60):
        self.pos_x += self.direction * self.speed * dt
        self.rect.center = (int(self.pos_x), int(self.pos_y))
        if self.hitbox and self.hitbox.active:
            self.hitbox.rect = self.rect.inflate(-10, -12)
        super().update(dt)

    def draw(self, screen, camera_x=0, camera_y=0):
        p = self.progress
        fade = 1.0 if p < 0.8 else (1.0 - (p - 0.8) / 0.2)
        alpha = max(0, min(255, int(245 * fade)))
        if alpha <= 5:
            return

        w, h = self.width, self.height
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        # 繪製新月形劍氣波
        pts_outer = []
        pts_inner = []
        steps = 14
        for i in range(steps + 1):
            t = i / steps
            ang = -0.46 * math.pi + t * 0.92 * math.pi
            xo = w * 0.18 + math.cos(ang) * (w * 0.72)
            yo = h * 0.5 + math.sin(ang) * (h * 0.48)
            xi = w * 0.18 + math.cos(ang) * (w * 0.36)
            yi = h * 0.5 + math.sin(ang) * (h * 0.40)
            pts_outer.append((xo, yo))
            pts_inner.append((xi, yi))

        poly = pts_outer + list(reversed(pts_inner))
        pygame.draw.polygon(surf, (70, 150, 255, int(alpha * 0.8)), poly)
        pygame.draw.lines(surf, (230, 250, 255, alpha), False, pts_outer, 3)

        if self.direction < 0:
            surf = pygame.transform.flip(surf, True, False)

        screen.blit(surf, (self.rect.x - camera_x, self.rect.y - camera_y))


class GroundShockwaveVFX(BaseVFX):
    """
    Boss 次元斬領域 / 範圍衝擊波特效 (ATTACK_3 第二段)：
    具備『前搖預警階段（無 Hitbox）』与『爆發階段（動態生成 Hitbox）』，爆發結束立即移除 Hitbox。
    """

    def __init__(
        self,
        target_x,
        ground_y,
        radius=68,
        windup_time=0.42,
        active_time=0.28,
        recovery_time=0.18,
        damage=22,
        hitbox_list=None,
    ):
        total_duration = windup_time + active_time + recovery_time
        super().__init__(target_x, ground_y - radius, duration=total_duration, hitbox=None)
        self.windup_time = windup_time
        self.active_time = active_time
        self.recovery_time = recovery_time
        self.radius = radius
        self.ground_y = ground_y
        self.damage = damage
        self.hitbox_list = hitbox_list  # 用於在進入 ACTIVE 瞬間將 Hitbox 註冊到場景中
        self.spawned_active_hitbox = False

        self.rect = pygame.Rect(
            int(target_x - radius),
            int(ground_y - radius * 1.8),
            int(radius * 2),
            int(radius * 1.8),
        )
        # 預先產生次元斬交錯線條角度
        self.slash_lines = [
            random.uniform(0, math.pi) for _ in range(7)
        ]

    def update(self, dt=1 / 60):
        # 進入爆發階段瞬間才實例化並啟用 Hitbox
        if (
            not self.spawned_active_hitbox
            and self.elapsed >= self.windup_time
            and self.elapsed < self.windup_time + self.active_time
        ):
            self.spawned_active_hitbox = True
            hb = Hitbox(
                owner="boss",
                rect=self.rect.inflate(-16, -16),
                damage=self.damage,
                knockback_x=240.0,
                lifetime=self.active_time,
                tag="aoe",
            )
            self.bind_hitbox(hb)
            if self.hitbox_list is not None:
                self.hitbox_list.append(hb)

        # 超過爆發階段進入殘影消散時，立即銷毀 Hitbox
        if (
            self.hitbox
            and self.hitbox.active
            and self.elapsed >= self.windup_time + self.active_time
        ):
            self.hitbox.destroy()

        super().update(dt)

    def draw(self, screen, camera_x=0, camera_y=0):
        sx = int(self.pos_x - camera_x)
        sy = int(self.rect.centery - camera_y)
        gy = int(self.ground_y - camera_y)

        if self.elapsed < self.windup_time:
            # 前搖預警：地面收縮光圈與次元鎖定框 (此時無傷害判定)
            wp = self.elapsed / max(self.windup_time, 0.01)
            r = int(self.radius * (1.25 - 0.35 * wp))
            alpha = int(80 + 140 * wp)
            warn_surf = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(
                warn_surf, (130, 80, 255, int(alpha * 0.35)), (r + 4, r + 4), r
            )
            pygame.draw.circle(
                warn_surf, (180, 220, 255, alpha), (r + 4, r + 4), r, 2
            )
            screen.blit(warn_surf, (sx - r - 4, sy - r - 4))
            # 地面預警線
            pygame.draw.line(
                screen,
                (120, 220, 255),
                (sx - self.radius, gy),
                (sx + self.radius, gy),
                3,
            )
        else:
            # 爆發與消散階段：次元球體與高速交錯刀網
            act_elapsed = self.elapsed - self.windup_time
            act_total = self.active_time + self.recovery_time
            ap = min(1.0, act_elapsed / max(act_total, 0.01))
            alpha = int(245 * (1.0 - ap * 0.85))
            r = self.radius
            surf = pygame.Surface((r * 2 + 20, r * 2 + 20), pygame.SRCALPHA)
            cx, cy = r + 10, r + 10

            pygame.draw.circle(surf, (45, 25, 110, int(alpha * 0.75)), (cx, cy), r)
            pygame.draw.circle(surf, (130, 220, 255, alpha), (cx, cy), r, 3)

            for ang in self.slash_lines:
                dx = math.cos(ang + ap * 1.8) * (r * 1.05)
                dy = math.sin(ang + ap * 1.8) * (r * 1.05)
                pygame.draw.line(
                    surf,
                    (235, 250, 255, alpha),
                    (cx - dx, cy - dy),
                    (cx + dx, cy + dy),
                    2,
                )

            screen.blit(surf, (sx - cx, sy - cy))


class ParrySparkVFX(BaseVFX):
    """
    格擋與完美格擋視覺回饋特效：
    - 完美格擋 (perfect=True)：亮青色/金色擴散衝擊環 + 放射狀火花
    - 一般格擋 (perfect=False)：藍色護盾波紋
    """

    def __init__(self, x, y, perfect=True):
        duration = 0.35 if perfect else 0.20
        super().__init__(x, y, duration=duration, hitbox=None)
        self.perfect = perfect
        self.sparks = [
            (
                random.uniform(0, math.tau),
                random.uniform(90, 220) if perfect else random.uniform(50, 120),
            )
            for _ in range(14 if perfect else 7)
        ]

    def draw(self, screen, camera_x=0, camera_y=0):
        p = self.progress
        sx = int(self.pos_x - camera_x)
        sy = int(self.pos_y - camera_y)
        alpha = max(0, int(255 * (1.0 - p)))

        max_r = 68 if self.perfect else 38
        r = max(4, int(max_r * (0.25 + 0.75 * p)))
        surf = pygame.Surface((max_r * 2 + 20, max_r * 2 + 20), pygame.SRCALPHA)
        cx, cy = max_r + 10, max_r + 10

        ring_color = (120, 245, 255, alpha) if self.perfect else (80, 160, 255, alpha)
        core_color = (255, 245, 160, alpha) if self.perfect else (180, 220, 255, alpha)

        pygame.draw.circle(surf, ring_color, (cx, cy), r, 4 if self.perfect else 2)
        if p < 0.45:
            pygame.draw.circle(surf, core_color, (cx, cy), int(r * 0.45))

        for ang, spd in self.sparks:
            dist1 = spd * p * 0.45
            dist2 = spd * p * 0.85
            x1 = cx + math.cos(ang) * dist1
            y1 = cy + math.sin(ang) * dist1
            x2 = cx + math.cos(ang) * dist2
            y2 = cy + math.sin(ang) * dist2
            pygame.draw.line(surf, core_color, (x1, y1), (x2, y2), 2)

        screen.blit(surf, (sx - cx, sy - cy))


def draw_debug_boxes(screen, camera_x, camera_y, player, boss, active_hitboxes):
    """
    在開啟 Debug 模式時，以不同顏色的線框繪製：
    - 綠色：Hurtbox (受擊框)
    - 紅色：Active Hitbox (啟用中的攻擊判定框)
    - 藍色/青色：玩家格擋/完美格擋判定框 (Parry/Block Box)
    - 黃色：移動物理碰撞框 (Collision Box)
    """
    # 1. 繪製 Player 碰撞框與受擊框
    if player and player.alive():
        pygame.draw.rect(
            screen,
            COLOR_DEBUG_COLLISION,
            player.collision_rect.move(-camera_x, -camera_y),
            1,
        )
        pygame.draw.rect(
            screen,
            COLOR_DEBUG_HURTBOX,
            player.hurtbox.move(-camera_x, -camera_y),
            2,
        )
        # 若處於防禦或完美格擋狀態，繪製藍色/青色格擋框
        if player.is_blocking and player.parry_box:
            p_color = COLOR_DEBUG_PARRY if player.is_parrying else COLOR_DEBUG_BLOCK
            pygame.draw.rect(
                screen,
                p_color,
                player.parry_box.move(-camera_x, -camera_y),
                2,
            )

    # 2. 繪製 Boss 碰撞框與受擊框
    if boss and boss.alive():
        pygame.draw.rect(
            screen,
            COLOR_DEBUG_COLLISION,
            boss.collision_rect.move(-camera_x, -camera_y),
            1,
        )
        pygame.draw.rect(
            screen,
            COLOR_DEBUG_HURTBOX,
            boss.hurtbox.move(-camera_x, -camera_y),
            2,
        )

    # 3. 繪製所有啟用中的攻擊 Hitbox (紅色)
    for hb in active_hitboxes:
        if hb.active:
            pygame.draw.rect(
                screen,
                COLOR_DEBUG_HITBOX,
                hb.rect.move(-camera_x, -camera_y),
                2,
            )
