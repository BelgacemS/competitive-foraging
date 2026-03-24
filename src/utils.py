import numpy as np
import random
import json
import os

def generer_allocations(nb_joueurs, nb_fioles, max_allocs = 15000):
    # etoiles et barres : C(n+k-1, k-1) nb combinaisons possible
    # on genere tout puis on echantillonne pour eviter le biais

    allocs = []

    def rec(restant, nb_f, courant):
        if nb_f == 1:
            allocs.append(tuple(courant + [restant]))
            return
        for i in range(restant + 1):
            rec(restant - i, nb_f - 1, courant + [i])
    rec(nb_joueurs, nb_fioles, [])

    if len(allocs) > max_allocs:
        allocs = random.sample(allocs, max_allocs)

    return allocs

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


def calculer_score(alloc0, alloc1, types_fioles, priorite=0):
    # alloc0 et alloc1 = tuples (nb joueurs par fiole pour chaque equipe)

    pts = [0, 0]

    for i, type_f in enumerate(types_fioles):
        n0, n1 = alloc0[i], alloc1[i]

        if n0 + n1 > 8:
            if priorite == 0: # l'equipe 0 se place avant
                n0 = min(n0, 8) 
                n1 = min(n1, 8 - n0)
            else:
                n1 = min(n1, 8)
                n0 = min(n0, 8 - n1)

        res = score_fiole(type_f, n0, n1)

        if res == 0: 
            pts[0] += 1
        elif res == 1: 
            pts[1] += 1

    return pts[0], pts[1]

def charger_types_fioles(nom_carte):
    # charge les types de fioles depuis le JSON de la carte
    # pas besoin de pygame on lit le fichier directement

    chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)),'pySpriteWorld', 'Cartes', nom_carte + '.json')
    
    with open(chemin) as f:
        carte = json.load(f)

    # mapping des tile ID vers les couleurs
    tile_types = {306: "jaune", 277: "rouge", 293: "bleue", 338: "verte", 324: "verte"}

    types = []
    for layer in carte['layers']:
        if layer['name'] == 'ramassables':
            for val in layer['data']:
                if val > 0 and val in tile_types:
                    types.append(tile_types[val])
            break
    return types
    

def best_response(types_fioles, alloc_adv, allocations):
    # trouve la meilleure allocation contre une allocation adverse fixe on teste toutes les allocs possibles et on garde la meilleure
    
    best, best_gain = allocations[0], -100
    
    for alloc in allocations:
        p0, p1 = calculer_score(alloc, alloc_adv, types_fioles)
        gain = p0 - p1

        if gain > best_gain:
            best_gain = gain
            best = alloc

    return best


def charger_nb_joueurs(nom_carte):
    # compte le nombre de joueurs par equipe depuis le JSON
    chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'pySpriteWorld', 'Cartes', nom_carte + '.json')
    with open(chemin) as f:
        carte = json.load(f)

    nb_joueurs = 0
    for layer in carte['layers']:
        if layer['name'] == 'joueur':
            nb_joueurs = sum(1 for val in layer['data'] if val > 0)
            break
    # total des 2 equipes, on divise par 2
    return nb_joueurs // 2


def analyser_allocations(types_fioles, allocations, k=10, nb_sample=1000):
    # trouve la meilleure alloc fixe et le top-k en 

    if len(allocations) <= nb_sample:
        sample = allocations
    else:
        sample = random.sample(allocations, nb_sample)

    scores = []

    for alloc in allocations:
        wins = 0
        for adv in sample:
            p0, p1 = calculer_score(alloc, adv, types_fioles)
            if p0 > p1: wins += 1
        scores.append((wins, alloc))
    scores.sort(reverse=True)

    meilleure = scores[0][1]
    top = [alloc for _, alloc in scores[:k]]

    return meilleure, top


def preparer_carte(nom_carte, nb_joueurs=None):
    # prepare toutes les donnees pour une carte : types, allocations, meilleures allocs
    # on fait ca une fois par carte et on reutilise partout pour eviter de recalculer
    # si nb_joueurs est pas donne, on le lit depuis le JSON de la carte

    print(f"Preparation de {nom_carte}")
    types = charger_types_fioles(nom_carte)
    if nb_joueurs is None:
        nb_joueurs = charger_nb_joueurs(nom_carte)
    allocs = generer_allocations(nb_joueurs, len(types))
    
    print(f"{len(types)} fioles ({', '.join(types)})")
    print(f"{len(allocs)} allocations possibles")

    meilleure, top = analyser_allocations(types, allocs, k=10)
    print(f" Meilleure alloc fixe: {meilleure}")

    return {'nom': nom_carte,'types': types,'allocations': allocs,'meilleure_fixe': meilleure,'top_allocs': top,'nb_joueurs': nb_joueurs,}