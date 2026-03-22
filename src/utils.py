import numpy as np


def generer_allocations(nb_joueurs, nb_fioles):
    # etoiles et barres : C(n+k-1, k-1) nb combinaisons possible

    allocs = []
    def rec(restant, nb_f, courant):
        if nb_f == 1:
            allocs.append(tuple(courant + [restant]))
            return
        for i in range(restant + 1):
            rec(restant - i, nb_f - 1, courant + [i])
    rec(nb_joueurs, nb_fioles, [])

    return allocs