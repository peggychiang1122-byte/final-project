import xml.etree.ElementTree as ET
import pygame

# 若在 Tiled 使用「點」工具，則自動展開成此大小的觸發區 (底部中央 = 點的位置)
DEFAULT_ZONE_W = 64
DEFAULT_ZONE_H = 128


class Checkpoint:
    """存檔點：玩家碰到後啟動，死亡時於底部中央重生"""

    def __init__(self, order, rect, name=""):
        self.order = order
        self.rect = pygame.Rect(rect)
        self.name = name or f"Checkpoint {order}"

    @property
    def spawn_pos(self):
        """重生座標 (腳底中央)"""
        return self.rect.midbottom

    def draw_debug(self, screen, camera_x, camera_y, font=None, active=False):
        r = self.rect.move(-camera_x, -camera_y)
        color = (255, 220, 60) if active else (80, 200, 255)
        pygame.draw.rect(screen, color, r, 2)
        if font is not None:
            label = font.render(str(self.order), True, color)
            screen.blit(label, (r.x + 4, r.y + 4))


def load_checkpoints(tmx_path, layer_name="checkpoints"):
    """
    直接解析 .tmx (XML)，讀取名為 layer_name 的物件圖層。
    不依賴 GameMap / pytmx，所以不需要修改 map.py。
    :return: 依 order 排序的 Checkpoint 清單
    """
    try:
        root = ET.parse(tmx_path).getroot()
    except (OSError, ET.ParseError) as e:
        print(f"[檢查點] 無法讀取 {tmx_path}: {e}")
        return []

    found = []
    for group in root.iter("objectgroup"):
        if (group.get("name") or "").strip().lower() != layer_name.lower():
            continue

        off_x = float(group.get("offsetx", 0))
        off_y = float(group.get("offsety", 0))

        for obj in group.findall("object"):
            props = {
                p.get("name"): p.get("value")
                for p in obj.findall("properties/property")
            }
            obj_id = int(obj.get("id", 0))
            x = float(obj.get("x", 0)) + off_x
            y = float(obj.get("y", 0)) + off_y
            w = float(obj.get("width", 0))
            h = float(obj.get("height", 0))

            if w <= 0 or h <= 0:
                # 點物件：以點作為腳底中央
                rect = pygame.Rect(0, 0, DEFAULT_ZONE_W, DEFAULT_ZONE_H)
                rect.midbottom = (round(x), round(y))
            else:
                rect = pygame.Rect(round(x), round(y), round(w), round(h))

            try:
                order = int(float(props.get("order")))
            except (TypeError, ValueError):
                order = obj_id  # 沒設定 order 時以物件 id 當順序

            name = obj.get("name") or props.get("name") or ""
            found.append(Checkpoint(order, rect, name))

    found.sort(key=lambda c: c.order)
    print(f"[檢查點] 從 {tmx_path} 載入 {len(found)} 個檢查點")
    return found