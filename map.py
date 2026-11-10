

import pygame
import pytmx
from collision import CollisionSystem


class GameMap:
    def __init__(self, map_path):
        # 讀取 Tiled 匯出的 .tmx 地圖
        self.tmx_data = pytmx.load_pygame(map_path)

        # 地圖尺寸
        self.tile_width = self.tmx_data.tilewidth
        self.tile_height = self.tmx_data.tileheight

        self.width = self.tmx_data.width * self.tile_width
        self.height = self.tmx_data.height * self.tile_height

        # 碰撞資料
        self.collisions = []
        self.platforms = []
        self.polygons = []    # 多邊形碰撞

        # 建立碰撞系統
        self.collision_system = CollisionSystem(self)

        # 顯示碰撞偵錯框的開關
        self.show_collision_debug = True

        # 讀取碰撞物件圖層
        layer_names = [ layer.name for layer in self.tmx_data.layers ]

        print("地圖圖層：", layer_names)

        if "Collisions" not in layer_names:
            raise ValueError(
                "找不到 Collisions 物件圖層。"
                "請確認 Tiled 的圖層名稱。"
            )

        collision_layer = self.tmx_data.get_layer_by_name( "Collisions" )



        # ==========================================
        # 讀取 Tiled 碰撞物件
        # ==========================================
        for obj in collision_layer:
            # 判斷是否為 Polygon
            points = getattr(obj, "points", None)
            if points:# 檢查第一個點是否已經在 obj.x, obj.y 附近 (判斷是相對座標還是絕對座標)
                first_pt_x, first_pt_y = points[0]
                is_absolute = (abs(first_pt_x - obj.x) < 2 and abs(first_pt_y - obj.y) < 2)

                if is_absolute:# 如果已經是絕對座標，直接取用 pt
                    polygon = [ (round(pt[0]), round(pt[1]))for pt in points ]
                else:# 如果是相對座標，才加上 obj.x 與 obj.y
                    polygon = [ (round(obj.x + pt[0]), round(obj.y + pt[1]))  for pt in points ]

                if len(polygon) >= 3:
                    self.polygons.append(polygon)
                    #print("修復後 Polygon 世界座標：", polygon)

            else:# Rectangle 碰撞
                if obj.width <= 0 or obj.height <= 0:
                    continue
                rect = pygame.Rect(
                    round(obj.x),
                    round(obj.y),
                    round(obj.width),
                    round(obj.height)
                )
                if obj.properties.get("one_way", False):
                    self.platforms.append(rect)
                else:
                    self.collisions.append(rect)



        print("矩形碰撞數量：", len(self.collisions))
        print("Polygon 碰撞數量：", len(self.polygons))
        print("單向平台數量：", len(self.platforms))

    
            

    def draw(self, screen, camera_x=0, camera_y=0):
        # 依照 Tiled 的圖層順序繪製地圖
        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, image in layer.tiles():
                    pixel_x = x * self.tile_width
                    pixel_y = y * self.tile_height

                    screen_x = pixel_x - camera_x
                    screen_y = pixel_y - camera_y

                    # 略過完全位於畫面外的圖塊
                    if (
                        screen_x + self.tile_width < 0
                        or screen_x > screen.get_width()
                        or screen_y + self.tile_height < 0
                        or screen_y > screen.get_height()
                    ):
                        continue

                    screen.blit(image, (screen_x, screen_y))

    # 將碰撞處理交給 collision.py
    def move_with_collisions(self, player_rect, dx, dy):
        return self.collision_system.move_with_collisions( player_rect, dx, dy)
    
    def get_camera_offset( self, target_rect, screen_width, screen_height):
        # 讓目標盡量位於畫面中央
        camera_x = target_rect.centerx - screen_width // 2
        camera_y = target_rect.centery - screen_height // 2

        # 限制攝影機不超出地圖
        max_camera_x = max(0, self.width - screen_width)
        max_camera_y = max(0, self.height - screen_height)

        camera_x = max(0, min(camera_x, max_camera_x))
        camera_y = max(0, min(camera_y, max_camera_y))

        return camera_x, camera_y

    def draw_collision_debug( self, screen, camera_x=0, camera_y=0):
        if not self.show_collision_debug:
            return

        # 綠色：實體碰撞區
        for rect in self.collisions:
            screen_rect = rect.move(-camera_x, -camera_y)
            pygame.draw.rect(
                screen, (0, 255, 0), screen_rect, 1
            )

        # 藍色：單向平台
        for rect in self.platforms:
            screen_rect = rect.move(-camera_x, -camera_y)
            pygame.draw.rect(
                screen, (0, 150, 255), screen_rect, 1
            )

        # 橘色多邊形碰撞區
        
        
        for polygon in self.polygons:
            if len(polygon) < 3:
                continue
            screen_points = [ (round(x - camera_x), round(y - camera_y)) for x, y in polygon  ]
            pygame.draw.polygon(screen, (255, 140, 0), screen_points, 2)