import pygame
import sys
import Player
import Boss1

class Game:
    def __init__(self):
        pygame.init()

        pygame.display.set_caption("Final Project")
        self.screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE | pygame.SCALED)

        self.clock = pygame.time.Clock()

        self.background = pygame.image.load("asset/Legacy-Fantasy - High Forest 2.3/Background/Background.png")
        self.background = pygame.transform.scale(self.background, (1280, 720))
        self.all_sprite = pygame.sprite.Group()
        self.enemy_group = pygame.sprite.Group()

        self.player1 = Player.Player()
        self.boss1 = Boss1.Vergil(self.player1)
        
        self.all_sprite.add(self.player1)
        self.all_sprite.add(self.boss1)
        self.enemy_group.add(self.boss1)


    def run(self):
        while True:
            self.screen.fill((0, 0, 0))
            self.screen.blit(self.background, (0, 0))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.player1.attack()

            self.all_sprite.update()
            self.all_sprite.draw(self.screen)
            self.player1.attack_hitbox(self.enemy_group, self.screen)
            pygame.draw.rect(self.screen, (255, 0, 0), self.boss1.hitbox, 2)
            pygame.display.update()

            self.clock.tick(60)
            

Game().run()