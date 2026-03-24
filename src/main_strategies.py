# -*- coding: utf-8 -*-

# Nicolas, 2026-02-09
from __future__ import absolute_import, print_function, unicode_literals

import random 
import numpy as np
import sys
from itertools import chain


import pygame

from pySpriteWorld.gameclass import Game,check_init_game_done
from pySpriteWorld.spritebuilder import SpriteBuilder
from pySpriteWorld.players import Player
from pySpriteWorld.sprite import MovingSprite
from pySpriteWorld.ontology import Ontology
import pySpriteWorld.glo

from search.grid2D import ProblemeGrid2D
from search import probleme








# ---- ---- ---- ---- ---- ----
# ---- Main                ----
# ---- ---- ---- ---- ---- ----

game = Game()

def init(_boardname=None):
    global player,game
    name = _boardname if _boardname is not None else 'mixed-map'
    #game = Game('./Cartes/' + name + '.json', SpriteBuilder)
    game = Game('Cartes/' + name + '.json', SpriteBuilder)
    game.O = Ontology(True, 'SpriteSheet-32x32/tiny_spritesheet_ontology.csv')
    game.populate_sprite_names(game.O)
    game.fps = 60  # frames per second
    game.mainiteration()
    player = game.player
    
def main():

    #for arg in sys.argv:
    #iterations = 40 # nb de pas max par episode
    #if len(sys.argv) == 2:
    #    iterations = int(sys.argv[1])
    #print ("Iterations: ")
    #print (iterations)

    init()
    

    
    #-------------------------------
    # Initialisation
    #-------------------------------
    
    nb_lignes = game.spriteBuilder.rowsize
    nb_cols = game.spriteBuilder.colsize
    assert nb_lignes == nb_cols # a priori on souhaite un plateau carre
    lMin=2  # les limites du plateau de jeu (2 premieres lignes utilisees pour stocker le contour)
    lMax=nb_lignes-2
    cMin=2
    cMax=nb_cols-2
   
    
    players = [o for o in game.layers['joueur']]
    nb_players = len(players)


    items = [o for o in game.layers["ramassable"]]  #
    nb_fioles = len(items)

    nb_episodes = 2


    #-------------------------------
    # Fonctions permettant de récupérer les listes des coordonnées
    # d'un ensemble d'objets ou de joueurs
    #-------------------------------

    def item_states(items):
        # donne la liste des coordonnees des items
        return [o.get_rowcol() for o in items]
    
    def player_states(players):
        # donne la liste des coordonnees des joueurs
        return [p.get_rowcol() for p in players]
    


    #-------------------------------
    # Rapport de ce qui est trouve sut la carte
    #-------------------------------
    print("lecture carte")
    print("-------------------------------------------")
    print('joueurs:', nb_players)
    print("fioles:",nb_fioles)
    print("lignes:", nb_lignes)
    print("colonnes:", nb_cols)
    print("-------------------------------------------")

    #-------------------------------
    # Carte demo yellow
    # 2 x 8 joueurs
    # 5 fioles jaunes
    #-------------------------------

    team = [[], []]  # 2 équipes
    for o in players:
        (x, y) = o.get_rowcol()
        if x == 2:  # les joueurs de team0 sur la ligne du haut
            team[0].append(o)
        elif x == 18:  # les joueurs de team1 sur la ligne du bas
            team[1].append(o)

    assert len(team[0]) == len(team[1])  # on veut un match équilibré donc équipe de même taille
    nb_players_team = int(nb_players / 2)

    init_states = [[],[]]
    # print(teamA)
    init_states[0] = player_states(team[0])

    # print(teamB)
    init_states[1] = player_states(team[1])


    #-------------------------------

    #-------------------------------
    # Fonctions definissant les positions legales et placement aléatoire
    #-------------------------------

    def around_pos(pos):
        # donne la liste des positions autour d'une pos (x,y) donnee
        x,y=pos
        return [(x-1,y-1),(x-1,y),(x-1,y+1),(x,y-1),(x,y+1),(x+1,y-1),(x+1,y),(x+1,y+1)]

    def around_pos_free(pos):
        return [pos for pos in around_pos(pos) if legal_position(pos)]

    def busy(pos):
        return around_pos_free(pos) == []

    def legal_position(pos):
        row,col = pos
        # une position legale est dans la carte et pas sur une fiole ni sur un joueur
        return ((pos not in item_states(items)) and (pos not in player_states(players)) and row>lMin and row<lMax-1 and col>=cMin and col<cMax)


    def players_around_item(f):
        """
        :param f: objet fiole
        :return: nombre d'objet de chaque team
        """
        are_here = [0,0]
        pos = f.get_rowcol()
        for i in [0,1]:
            for j in team[i]:
                if j.get_rowcol() in around_pos(pos):
                    are_here[i]+=1
        return are_here


    def get_fiole_type(fiole):

        tid = fiole.tileid
        valeur = tid[0] * 16 + tid[1] + 1
        types = {306: "jaune", 277: "rouge", 293: "bleue", 338: "verte", 324: "verte"}
        
        return types.get(valeur, "inconnu")


    def score_fiole(type_fiole, nb_j0, nb_j1):
        # 0 team 0 gagne, 1 team 1 gagne, ou -1 personne

        if type_fiole == "jaune":

            ok0 = nb_j0 >= 1
            ok1 = nb_j1 >= 1

        elif type_fiole == "rouge":

            ok0 = nb_j0 >= 2
            ok1 = nb_j1 >= 2

        elif type_fiole == "verte":

            if nb_j0 + nb_j1 >= 3:
                if nb_j0 > nb_j1: return 0
                elif nb_j1 > nb_j0: return 1
            return -1

        elif type_fiole == "bleue":

            if nb_j0 == 1 and nb_j1 >= 2:
                return 0
            if nb_j1 == 1 and nb_j0 >= 2:
                return 1
 
            ok0 = nb_j0 >= 2
            ok1 = nb_j1 >= 2

        else:
            return -1

        # regle pour jaune/rouge/bleue
        if ok0 and ok1:
            if nb_j0 > nb_j1: 
                return 0
            elif nb_j1 > nb_j0:
                return 1
            else: 
                return -1
        elif ok0: 
            return 0
        elif ok1: 
            return 1
        return -1



    # -------------------------------
    # Strategie aleatoire
    # -------------------------------

    score = [0,0]

    for e in range(nb_episodes):
        priority= [0, 1] if e % 2 == 0 else [1, 0]
        for t in priority:
            print("Team ",t)
            path = []
            choix_fiole = []
            choix_pos = []
            for p in range(0,nb_players_team):
                f = random.choice(items)
                while busy(f.get_rowcol()): # si plus de place on choisit une autre fiole
                    f = random.choice(items)
                choix_fiole.append(f)
                # choisir une position libre autour de la fiole choisie
                chosen_pos = random.choice(around_pos_free(f.get_rowcol()))
                choix_pos.append(chosen_pos)

                pos_player = team[t][p].get_rowcol()
                print("Player ", p, " starting from ", pos_player, " going to potion ", choix_fiole[p].get_rowcol(), " at ", choix_pos[p])

                # -------------------------------
                # calcul A* pour le joueur
                # -------------------------------

                g = np.ones((nb_lignes, nb_cols), dtype=bool)  # une matrice remplie par defaut a True

                for i in range(nb_lignes):  # on exclut aussi les bordures du plateau
                    g[0][i] = False
                    g[1][i] = False
                    g[nb_lignes - 1][i] = False
                    g[nb_lignes - 2][i] = False
                    g[i][0] = False
                    g[i][1] = False
                    g[i][nb_lignes - 1] = False
                    g[i][nb_lignes - 2] = False
                prob = ProblemeGrid2D(pos_player, choix_pos[p], g, 'manhattan')
                path.append(probleme.astar(prob, verbose=False))
                print("Chemin trouvé:", path[p])


                #-------------------------------
                # Boucle principale de déplacements
                #-------------------------------

                # on fait bouger le joueur jusqu'à son but
                # en suivant le chemin trouve avec A*

                for i in range(len(path[p])):  # si le joueur n'est pas deja arrive
                    (row, col) = path[p][i]
                    team[t][p].set_rowcol(row, col)
                    print("pos joueur:",  row, col)

                    # mise à jour du pleateau de jeu
                    game.mainiteration()








        # -------------------------------
        # Calcul des scores
        # -------------------------------

        print(f"Episode {e+1}/{nb_episodes} (priorite: {priority})")

        for o in items:

            type_f = get_fiole_type(o)
            nb_j0, nb_j1 = players_around_item(o)
            resultat = score_fiole(type_f, nb_j0, nb_j1)

            if resultat == 0:
                score[0] += 1
                print(f"Fiole {type_f} : {nb_j0} vs {nb_j1} -> equipe 1 gagne")

            elif resultat == 1:
                score[1] += 1
                print(f"Fiole {type_f} : {nb_j0} vs {nb_j1} -> equipe 2 gagne")

            else:
                print(f"Fiole {type_f} : {nb_j0} vs {nb_j1} -> personne")

        print(f"Score cumule: {score[0]}-{score[1]}")


        # remettre les joueurs à leur pos initiale a la fin de l'episode

        for i in [0,1]:
            j=0
            for p in team[i]:
                x,y = init_states[i][j]
                p.set_rowcol(x,y)
                j+=1


    print("\nResultat final")
    print(f"Score: {score[0]}-{score[1]}")
    

    if score[0] > score[1]:
        print("Equipe 1 gagne")
    elif score[1] > score[0]:
        print("Equipe 2 gagne")
    else:
        print("Egalite")

    pygame.quit()

    
    #-------------------------------


if __name__ == '__main__':
    main()
