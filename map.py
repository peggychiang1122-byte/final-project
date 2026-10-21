
import pygame
import pytmx


class GameMap:
    def __init__(self, map_path):
        # 讀取 Tiled 匯出的 .tmx 地圖檔
        self.tmx_data = pytmx.load_pygame(map_path)

        # 取得地圖每個圖塊的寬度與高度
        self.tile_width = self.tmx_data.tilewidth
        self.tile_height = self.tmx_data.tileheight

        # 計算整張地圖的像素尺寸
        self.width = self.tmx_data.width * self.tile_width
        self.height = self.tmx_data.height * self.tile_height

    
    def draw(self, screen, camera_x=0, camera_y=0):
    # 逐一讀取地圖中可見的圖層
        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):

            # 逐一取得圖塊的位置與圖片
                for x, y, image in layer.tiles():

                # 將圖塊座標換算成像素座標
                    pixel_x = x * self.tile_width
                    pixel_y = y * self.tile_height

                # 減去鏡頭偏移，決定圖塊在畫面上的位置
                    screen_x = pixel_x - camera_x
                    screen_y = pixel_y - camera_y

                # 繪製圖塊
                    screen.blit(image, (screen_x, screen_y))
    
    def get_camera_offset(self, target_rect, screen_width, screen_height):
        # 讓攝影機盡量將玩家放在畫面中央
        camera_x = target_rect.centerx - screen_width // 2
        camera_y = target_rect.centery - screen_height // 2

        # 限制攝影機不能看到地圖左側以外的區域
        camera_x = max(0, camera_x)
        camera_y = max(0, camera_y)

        # 限制攝影機不能超出地圖右側與底部
        max_camera_x = max(0, self.width - screen_width)
        max_camera_y = max(0, self.height - screen_height)

        camera_x = min(camera_x, max_camera_x)
        camera_y = min(camera_y, max_camera_y)

        return camera_x, camera_y
    
        """
        這段程式會：
        1. 先計算讓玩家位於畫面中央附近的攝影機位置。
        2. 限制攝影機不要移出地圖範圍。
        3. 回傳攝影機的水平、垂直偏移量。
        這裡的 target_rect 是玩家的碰撞矩形，所以我們需要知道組員的玩家程式是否使用 pygame.Rect。
        """
    
