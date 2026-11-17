import pygame
from settings import WIDTH, HEIGHT


class HUD:
    def __init__(self, player, boss=None, is_tutorial=False):
        self.player = player
        self.boss = boss
        self.is_tutorial = is_tutorial

        self.font_big = pygame.font.SysFont(None, 90)
        self.font_mid = pygame.font.SysFont(None, 52)
        self.font_small = pygame.font.SysFont(None, 36)
        self.font_hud = pygame.font.SysFont(None, 24)

        self.player_display_hp = float(getattr(player, "player_hp", 100))
        self.boss_display_hp = float(getattr(boss, "boss_health", 100)) if boss else 0.0

    def reset(self, player, boss=None, is_tutorial=False):
        """開新局時重置綁定的角色、Boss 與狀態"""
        self.player = player
        self.boss = boss
        self.is_tutorial = is_tutorial
        self.player_display_hp = float(getattr(player, "player_hp", 100))
        self.boss_display_hp = float(getattr(boss, "boss_health", 100)) if boss else 0.0

    def update(self, raw_dt):
        """更新緩衝過渡血條"""
        decay_speed = 38.0 * raw_dt
        self.player_display_hp = self._smooth_hp(
            self.player_display_hp, self.player.player_hp, decay_speed
        )
        if self.boss is not None and hasattr(self.boss, "boss_health"):
            self.boss_display_hp = self._smooth_hp(
                self.boss_display_hp, self.boss.boss_health, decay_speed
            )

    def _smooth_hp(self, current_disp, target_hp, step):
        if current_disp > target_hp:
            return max(float(target_hp), current_disp - step)
        return float(target_hp)

    def draw_text(self, screen, text, font, color, center):
        img = font.render(text, True, color)
        screen.blit(img, img.get_rect(center=center))

    def draw_gameplay_hud(self, screen, camera_x, camera_y):
        """繪製遊戲中 HUD (教學關卡不繪製 Boss 血條)"""
        self._draw_player_hp(screen, camera_x, camera_y)
        if not self.is_tutorial and self.boss is not None and getattr(self.boss, "alive", lambda: False)():
            self._draw_boss_hp(screen)

    def _draw_player_hp(self, screen, camera_x, camera_y):
        """畫面左上角繪製玩家 HUD 血量條"""
        x, y = 24, 24
        bar_w, bar_h = 300, 24
        max_hp = getattr(self.player, "max_hp", 100)
        cur_hp = max(self.player.player_hp, 0)
        disp_hp = max(self.player_display_hp, cur_hp)

        cur_ratio = cur_hp / max_hp
        disp_ratio = disp_hp / max_hp

        pygame.draw.rect(screen, (35, 35, 45), (x, y, bar_w, bar_h), border_radius=4)
        if disp_ratio > 0:
            pygame.draw.rect(
                screen,
                (245, 190, 65),
                (x, y, int(bar_w * disp_ratio), bar_h),
                border_radius=4,
            )
        if cur_ratio > 0:
            pygame.draw.rect(
                screen,
                (215, 45, 55),
                (x, y, int(bar_w * cur_ratio), bar_h),
                border_radius=4,
            )
        pygame.draw.rect(
            screen, (240, 240, 245), (x, y, bar_w, bar_h), 2, border_radius=4
        )

        hp_str = f"PLAYER HP: {cur_hp} / {max_hp} ({int(cur_ratio * 100)}%)"
        txt_surf = self.font_hud.render(hp_str, True, (255, 255, 255))
        screen.blit(txt_surf, (x + 10, y + 4))

        is_parrying = getattr(self.player, "is_parrying", False)
        is_blocking = getattr(self.player, "is_blocking", False)
        if is_parrying:
            badge_text = "★ PERFECT PARRY WINDOW ★"
            badge_color = (80, 245, 255)
        elif is_blocking:
            badge_text = "GUARDING (70% DMG REDUCTION)"
            badge_color = (120, 180, 255)
        else:
            badge_text = "RMB / J / Shift: Parry & Guard | F1: Debug"
            badge_color = (210, 215, 225)

        badge_surf = self.font_hud.render(badge_text, True, badge_color)
        screen.blit(badge_surf, (x, y + bar_h + 6))

        status_timer = getattr(self.player, "status_timer", 0.0)
        status_text = getattr(self.player, "status_text", "")
        if status_timer > 0.0 and status_text:
            ref_rect = getattr(self.player, "collision_rect", self.player.rect)
            sx = ref_rect.centerx - camera_x
            sy = ref_rect.top - 22 - camera_y
            color = (90, 250, 255) if "PERFECT" in status_text else (255, 230, 120)
            self.draw_text(screen, status_text, self.font_hud, color, (sx, sy))

    def _draw_boss_hp(self, screen):
        """畫面頂部中央繪製 Boss 血量條"""
        if self.boss is None:
            return

        max_hp = getattr(self.boss, "max_health", 100)
        cur_hp = max(self.boss.boss_health, 0)
        disp_hp = max(self.boss_display_hp, cur_hp)

        bar_w, bar_h = 540, 22
        x = (WIDTH - bar_w) // 2
        y = 38

        cur_ratio = cur_hp / max_hp
        disp_ratio = disp_hp / max_hp

        boss_state = getattr(self.boss, "state", "BOSS")
        title = f"VERGIL — {boss_state}"
        attack_phase = getattr(self.boss, "attack_phase", "NONE")
        if attack_phase != "NONE":
            title += f" [{attack_phase}]"
        self.draw_text(screen, title, self.font_hud, (20, 20, 30), (WIDTH // 2 + 1, y - 13))
        self.draw_text(screen, title, self.font_hud, (245, 240, 255), (WIDTH // 2, y - 14))

        pygame.draw.rect(screen, (35, 30, 45), (x, y, bar_w, bar_h), border_radius=4)
        if disp_ratio > 0:
            pygame.draw.rect(
                screen,
                (245, 215, 255),
                (x, y, int(bar_w * disp_ratio), bar_h),
                border_radius=4,
            )
        if cur_ratio > 0:
            pygame.draw.rect(
                screen,
                (165, 35, 185),
                (x, y, int(bar_w * cur_ratio), bar_h),
                border_radius=4,
            )
        pygame.draw.rect(
            screen, (245, 245, 250), (x, y, bar_w, bar_h), 2, border_radius=4
        )

        hp_label = f"{cur_hp} / {max_hp} ({int(cur_ratio * 100)}%)"
        self.draw_text(
            screen, hp_label, self.font_hud, (255, 255, 255), (WIDTH // 2, y + bar_h // 2)
        )

    # =========================================================================
    # 新增：新手教學詢問視窗 (TUTORIAL_PROMPT) 與 教學關卡提示 (TUTORIAL_GUIDE)
    # =========================================================================

    def draw_tutorial_prompt(self, screen, selected_option=0):
        """
        繪製詢問是否進入新手教學關卡的互動彈窗
        :param selected_option: 0 代表 YES，1 代表 NO
        :return: 包含按鈕 Rect 的字典 {'YES': Rect, 'NO': Rect}，方便滑鼠事件檢測
        """
        # 1. 半透明黑色底色遮罩
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 20, 180))
        screen.blit(overlay, (0, 0))

        # 2. 中央對話框本體
        box_w, box_h = 720, 400
        box_x = (WIDTH - box_w) // 2
        box_y = (HEIGHT - box_h) // 2
        dialog_rect = pygame.Rect(box_x, box_y, box_w, box_h)

        # 框底與金屬漸層外邊框
        pygame.draw.rect(screen, (22, 26, 38), dialog_rect, border_radius=12)
        pygame.draw.rect(screen, (80, 130, 190), dialog_rect, 3, border_radius=12)

        # 3. 標題與說明文字
        self.draw_text(
            screen,
            "TUTORIAL PROMPT",
            self.font_mid,
            (255, 215, 80),
            (WIDTH // 2, box_y + 55),
        )
        self.draw_text(
            screen,
            "是否進入新手教學關卡？",
            self.font_small,
            (255, 255, 255),
            (WIDTH // 2, box_y + 120),
        )
        self.draw_text(
            screen,
            "Enter Tutorial Stage?",
            self.font_hud,
            (180, 200, 225),
            (WIDTH // 2, box_y + 155),
        )
        self.draw_text(
            screen,
            "建議首次遊玩的玩家先練習：移動、跳躍、揮刀與完美格擋",
            self.font_hud,
            (150, 175, 205),
            (WIDTH // 2, box_y + 195),
        )

        # 4. YES / NO 選項按鈕設定
        btn_w, btn_h = 240, 56
        btn_y = box_y + 250
        gap = 40
        yes_x = WIDTH // 2 - btn_w - gap // 2
        no_x = WIDTH // 2 + gap // 2

        yes_rect = pygame.Rect(yes_x, btn_y, btn_w, btn_h)
        no_rect = pygame.Rect(no_x, btn_y, btn_w, btn_h)

        # 繪製 YES 按鈕
        is_yes = (selected_option == 0)
        yes_bg = (40, 110, 170) if is_yes else (32, 38, 52)
        yes_border = (100, 220, 255) if is_yes else (70, 80, 100)
        yes_text_color = (255, 255, 255) if is_yes else (170, 180, 200)
        pygame.draw.rect(screen, yes_bg, yes_rect, border_radius=8)
        pygame.draw.rect(screen, yes_border, yes_rect, 3 if is_yes else 1, border_radius=8)
        self.draw_text(
            screen,
            "★ YES (進入教學)",
            self.font_small,
            yes_text_color,
            yes_rect.center,
        )

        # 繪製 NO 按鈕
        is_no = (selected_option == 1)
        no_bg = (160, 55, 65) if is_no else (32, 38, 52)
        no_border = (255, 120, 130) if is_no else (70, 80, 100)
        no_text_color = (255, 255, 255) if is_no else (170, 180, 200)
        pygame.draw.rect(screen, no_bg, no_rect, border_radius=8)
        pygame.draw.rect(screen, no_border, no_rect, 3 if is_no else 1, border_radius=8)
        self.draw_text(
            screen,
            "NO (直接開戰)",
            self.font_small,
            no_text_color,
            no_rect.center,
        )

        # 5. 操作提示說明
        self.draw_text(
            screen,
            "按鍵操作：← / → 或 A / D 切換選項 ｜ ENTER 確認 ｜ 支援滑鼠點擊",
            self.font_hud,
            (130, 150, 180),
            (WIDTH // 2, box_y + 355),
        )

        return {"YES": yes_rect, "NO": no_rect}

    def draw_tutorial_guide(self, screen):
        """在教學關卡畫面上方/右上角顯示的操作教學卡片"""
        panel_w, panel_h = 420, 210
        panel_x = WIDTH - panel_w - 24
        panel_y = 24
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((16, 20, 32, 200))
        screen.blit(panel_surf, (panel_x, panel_y))
        pygame.draw.rect(screen, (70, 120, 180), panel_rect, 2, border_radius=8)

        # 標題
        title_surf = self.font_hud.render("【新手操作指南 / TUTORIAL GUIDE】", True, (255, 220, 90))
        screen.blit(title_surf, (panel_x + 16, panel_y + 14))

        # 提示條目
        guides = [
            ("• A / D 或 ← / →", "水平移動 (Move)"),
            ("• W / SPACE", "跳躍 (Jump)"),
            ("• 滑鼠左鍵 (LMB)", "揮刀攻擊 (Attack)"),
            ("• 滑鼠右鍵 / J / Shift", "格擋減免 70% 傷害 (Guard)"),
            ("• 命中間前 0.15 秒防禦", "★ 完美格擋 (Perfect Parry)"),
            ("• 前進至右側傳送門", "通過教學並進入主世界！"),
        ]

        start_y = panel_y + 44
        line_height = 26
        for i, (key_label, desc_label) in enumerate(guides):
            k_surf = self.font_hud.render(key_label, True, (80, 230, 255))
            d_surf = self.font_hud.render(desc_label, True, (230, 235, 245))
            cur_y = start_y + i * line_height
            screen.blit(k_surf, (panel_x + 16, cur_y))
            screen.blit(d_surf, (panel_x + 200, cur_y))


    # =========================================================================
    # 新增：新手教學詢問視窗 (TUTORIAL_PROMPT) 與 教學關卡提示 (TUTORIAL_GUIDE)
    # =========================================================================

    def draw_tutorial_prompt(self, screen, selected_option=0):
        """
        繪製詢問是否進入新手教學關卡的互動彈窗
        :param selected_option: 0 代表 YES，1 代表 NO
        :return: 包含按鈕 Rect 的字典 {'YES': Rect, 'NO': Rect}，方便滑鼠事件檢測
        """
        # 1. 半透明黑色底色遮罩
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 20, 180))
        screen.blit(overlay, (0, 0))

        # 2. 中央對話框本體
        box_w, box_h = 720, 400
        box_x = (WIDTH - box_w) // 2
        box_y = (HEIGHT - box_h) // 2
        dialog_rect = pygame.Rect(box_x, box_y, box_w, box_h)

        # 框底與金屬漸層外邊框
        pygame.draw.rect(screen, (22, 26, 38), dialog_rect, border_radius=12)
        pygame.draw.rect(screen, (80, 130, 190), dialog_rect, 3, border_radius=12)

        # 3. 標題與說明文字
        self.draw_text(
            screen,
            "TUTORIAL PROMPT",
            self.font_mid,
            (255, 215, 80),
            (WIDTH // 2, box_y + 55),
        )
        self.draw_text(
            screen,
            "是否進入新手教學關卡？",
            self.font_small,
            (255, 255, 255),
            (WIDTH // 2, box_y + 120),
        )
        self.draw_text(
            screen,
            "Enter Tutorial Stage?",
            self.font_hud,
            (180, 200, 225),
            (WIDTH // 2, box_y + 155),
        )
        self.draw_text(
            screen,
            "建議首次遊玩的玩家先練習：移動、跳躍、揮刀與完美格擋",
            self.font_hud,
            (150, 175, 205),
            (WIDTH // 2, box_y + 195),
        )

        # 4. YES / NO 選項按鈕設定
        btn_w, btn_h = 240, 56
        btn_y = box_y + 250
        gap = 40
        yes_x = WIDTH // 2 - btn_w - gap // 2
        no_x = WIDTH // 2 + gap // 2

        yes_rect = pygame.Rect(yes_x, btn_y, btn_w, btn_h)
        no_rect = pygame.Rect(no_x, btn_y, btn_w, btn_h)

        # 繪製 YES 按鈕
        is_yes = (selected_option == 0)
        yes_bg = (40, 110, 170) if is_yes else (32, 38, 52)
        yes_border = (100, 220, 255) if is_yes else (70, 80, 100)
        yes_text_color = (255, 255, 255) if is_yes else (170, 180, 200)
        pygame.draw.rect(screen, yes_bg, yes_rect, border_radius=8)
        pygame.draw.rect(screen, yes_border, yes_rect, 3 if is_yes else 1, border_radius=8)
        self.draw_text(
            screen,
            "★ YES (進入教學)",
            self.font_small,
            yes_text_color,
            yes_rect.center,
        )

        # 繪製 NO 按鈕
        is_no = (selected_option == 1)
        no_bg = (160, 55, 65) if is_no else (32, 38, 52)
        no_border = (255, 120, 130) if is_no else (70, 80, 100)
        no_text_color = (255, 255, 255) if is_no else (170, 180, 200)
        pygame.draw.rect(screen, no_bg, no_rect, border_radius=8)
        pygame.draw.rect(screen, no_border, no_rect, 3 if is_no else 1, border_radius=8)
        self.draw_text(
            screen,
            "NO (直接開戰)",
            self.font_small,
            no_text_color,
            no_rect.center,
        )

        # 5. 操作提示說明
        self.draw_text(
            screen,
            "按鍵操作：← / → 或 A / D 切換選項 ｜ ENTER 確認 ｜ 支援滑鼠點擊",
            self.font_hud,
            (130, 150, 180),
            (WIDTH // 2, box_y + 355),
        )

        return {"YES": yes_rect, "NO": no_rect}

    def draw_tutorial_guide(self, screen):
        """在教學關卡畫面上方/右上角顯示的操作教學卡片"""
        panel_w, panel_h = 420, 210
        panel_x = WIDTH - panel_w - 24
        panel_y = 24
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((16, 20, 32, 200))
        screen.blit(panel_surf, (panel_x, panel_y))
        pygame.draw.rect(screen, (70, 120, 180), panel_rect, 2, border_radius=8)

        # 標題
        title_surf = self.font_hud.render("【新手操作指南 / TUTORIAL GUIDE】", True, (255, 220, 90))
        screen.blit(title_surf, (panel_x + 16, panel_y + 14))

        # 提示條目
        guides = [
            ("• A / D 或 ← / →", "水平移動 (Move)"),
            ("• W / SPACE", "跳躍 (Jump)"),
            ("• 滑鼠左鍵 (LMB)", "揮刀攻擊 (Attack)"),
            ("• 滑鼠右鍵 / J / Shift", "格擋減免 70% 傷害 (Guard)"),
            ("• 命中間前 0.15 秒防禦", "★ 完美格擋 (Perfect Parry)"),
            ("• 前進至右側傳送門", "通過教學並進入主世界！"),
        ]

        start_y = panel_y + 44
        line_height = 26
        for i, (key_label, desc_label) in enumerate(guides):
            k_surf = self.font_hud.render(key_label, True, (80, 230, 255))
            d_surf = self.font_hud.render(desc_label, True, (230, 235, 245))
            cur_y = start_y + i * line_height
            screen.blit(k_surf, (panel_x + 16, cur_y))
            screen.blit(d_surf, (panel_x + 200, cur_y))