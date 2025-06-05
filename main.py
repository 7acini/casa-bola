import pygame as pg
import sys
from ConfiguracoesTela import *


class CasaBola:
     
     def __init__(self):
          pg.init()
        # Tela
        #resolução 
        self.screen = pg.display.set_mode(res)
        # Tempo de tela
        self.clock = pg.time.Clock()
        self.delta_time = 1
        self.new_game()
     
     def new_game(self):
          self.map = Map(self)
          self.player - Player(self)

    def update(self):
        self.player.update()
        pg.display.flip()
        self.delta_time = self.clock.tick(fps)

pg.display.set_caption('Casa bola interna')

loop = True
# definição da tela do game


while loop:
    for events in pg.event.get():
        # verifica qunado fechar
         if events.type == pg.QUIT:
              loop = False
    
    pg.display.update()


