import pygame


class AnimatedSprite:
    def __init__(self):
        self.animation = {}
        self.current_state = ""
        self.current_frames = 0.0
        self.finished = False

    def load_animation(self, state_name, sheet_path, total_frames, scale_ratio):
        sprite_sheet = pygame.image.load(sheet_path).convert_alpha()
        frames = []

        frame_width = sprite_sheet.get_width() // total_frames
        total_height = sprite_sheet.get_height()

        for i in range(total_frames):
            crop_x = i * frame_width
            crop_y = 0

            rect = pygame.Rect(crop_x, crop_y, frame_width, total_height)
            frame_subsurface = sprite_sheet.subsurface(rect)

            if scale_ratio != 1:
                new_width = int(frame_width * scale_ratio)
                new_height = int(total_height * scale_ratio)
                frame_subsurface = pygame.transform.scale(
                    frame_subsurface, (new_width, new_height)
                ).convert_alpha()

            frames.append(frame_subsurface)

        self.animation[state_name] = frames

    def play(self, state_name, force_reset=False):
        if self.current_state != state_name or force_reset:
            self.current_state = state_name
            self.current_frames = 0.0
            self.finished = False

    def update_get_image(self, speed, dt_scale=1.0, loop=True):
        """
        更新動畫幀並回傳當前 Surface。
        speed: 基準每幀推進量 (以 60 FPS 為基準)
        dt_scale: 時間縮放因子，預設為 (dt * 60)，已包含 time_scale 影響
        loop: 是否循環播放；若為 False 則停在最後一幀並標記 self.finished = True
        """
        current_list = self.animation[self.current_state]
        self.current_frames += speed * dt_scale

        if self.current_frames >= len(current_list):
            if loop:
                self.current_frames %= len(current_list)
                self.finished = False
            else:
                self.current_frames = len(current_list) - 0.001
                self.finished = True

        return current_list[int(self.current_frames)]
