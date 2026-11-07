
import pygame


class CollisionSystem:

    def __init__(self, game_map):
        # 取得 GameMap 中的碰撞資料
        self.game_map = game_map

    # ==========================================
    # 1. SAT：計算矩形與 Polygon 的最小分離向量
    # ==========================================
    def polygon_mtv(self, rect, polygon):

        rect_points = [
            (rect.left, rect.top),
            (rect.right, rect.top),
            (rect.right, rect.bottom),
            (rect.left, rect.bottom)
        ]

        axes = [
            (1, 0),
            (0, 1)
        ]

        for i in range(len(polygon)):

            p1 = polygon[i]
            p2 = polygon[(i + 1) % len(polygon)]

            edge_x = p2[0] - p1[0]
            edge_y = p2[1] - p1[1]

            axis = (-edge_y, edge_x)

            length = (axis[0] ** 2 + axis[1] ** 2) ** 0.5

            if length == 0:
                continue

            axis = (
                axis[0] / length,
                axis[1] / length
            )

            axes.append(axis)

        min_overlap = float("inf")
        smallest_axis = None

        polygon_center = (
            sum(p[0] for p in polygon) / len(polygon),
            sum(p[1] for p in polygon) / len(polygon)
        )

        rect_center = (
            rect.centerx,
            rect.centery
        )

        for axis_x, axis_y in axes:

            rect_projection = [
                p[0] * axis_x + p[1] * axis_y
                for p in rect_points
            ]

            polygon_projection = [
                p[0] * axis_x + p[1] * axis_y
                for p in polygon
            ]

            rect_min = min(rect_projection)
            rect_max = max(rect_projection)

            polygon_min = min(polygon_projection)
            polygon_max = max(polygon_projection)

            overlap = min(rect_max, polygon_max) - max(
                rect_min, polygon_min
            )

            if overlap <= 0:
                return None

            if overlap < min_overlap:

                min_overlap = overlap
                smallest_axis = (axis_x, axis_y)

        if smallest_axis is None:
            return None

        direction_x = rect_center[0] - polygon_center[0]
        direction_y = rect_center[1] - polygon_center[1]

        axis_x, axis_y = smallest_axis

        if direction_x * axis_x + direction_y * axis_y < 0:
            axis_x = -axis_x
            axis_y = -axis_y

        return (
            axis_x * min_overlap,
            axis_y * min_overlap
        )

    # ==========================================
    # 2. 判斷矩形與 Polygon 是否碰撞
    # ==========================================
    def polygon_collide(self, rect, polygon):

        return self.polygon_mtv(rect, polygon) is not None

    # ==========================================
    # 3. 玩家移動與地圖碰撞
    # ==========================================
    def move_with_collisions(self, player_rect, dx, dy):

        # 取得 GameMap 的碰撞資料
        collisions = self.game_map.collisions
        polygons = self.game_map.polygons
        platforms = self.game_map.platforms

        on_ground = False
        hit_ceiling = False

        dx = round(dx)
        dy = round(dy)

        # 水平方向：矩形碰撞
        player_rect.x += dx

        for wall in collisions:

            if player_rect.colliderect(wall):

                if dx > 0:
                    player_rect.right = wall.left

                elif dx < 0:
                    player_rect.left = wall.right

        # 水平方向：Polygon 碰撞
        for polygon in polygons:

            mtv = self.polygon_mtv(player_rect, polygon)

            if mtv is not None:

                player_rect.x += round(mtv[0])
                player_rect.y += round(mtv[1])

                if mtv[1] < 0:
                    on_ground = True

                elif mtv[1] > 0:
                    hit_ceiling = True

        # 垂直方向：矩形碰撞
        old_bottom = player_rect.bottom
        player_rect.y += dy

        for wall in collisions:

            if player_rect.colliderect(wall):

                if dy > 0:
                    player_rect.bottom = wall.top
                    on_ground = True

                elif dy < 0:
                    player_rect.top = wall.bottom
                    hit_ceiling = True

        # 垂直方向：Polygon 碰撞
        for polygon in polygons:

            mtv = self.polygon_mtv(player_rect, polygon)

            if mtv is not None:

                player_rect.x += round(mtv[0])
                player_rect.y += round(mtv[1])

                if mtv[1] < 0:
                    on_ground = True

                elif mtv[1] > 0:
                    hit_ceiling = True

        # 單向平台碰撞
        if dy > 0:

            for platform in platforms:

                crossed = (
                    old_bottom <= platform.top
                    and player_rect.bottom >= platform.top
                )

                overlap = (
                    player_rect.right > platform.left
                    and player_rect.left < platform.right
                )

                if crossed and overlap:

                    player_rect.bottom = platform.top
                    on_ground = True

        # 地面接觸檢查
        ground_probe = player_rect.move(0, 1)

        for wall in collisions:

            if ground_probe.colliderect(wall):
                on_ground = True
                break

        if not on_ground:

            for platform in platforms:

                if ground_probe.colliderect(platform):
                    on_ground = True
                    break

        # Polygon 地面接觸檢查
        if not on_ground:

            for polygon in polygons:

                if self.polygon_collide(ground_probe, polygon):
                    on_ground = True
                    break

        return on_ground, hit_ceiling
