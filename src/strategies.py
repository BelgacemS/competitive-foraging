import numpy as np                                                                                                           
import random                                                   
from collections import Counter                                                                                              
from utils import (generer_allocations, calculer_score,best_response, analyser_allocations)

class Strategie:

    def __init__(self, nom, types_fioles, nb_joueurs=8, allocations=None, meilleure_fixe=None, top_allocs=None):
        
        self.nom = nom
        self.types_fioles = types_fioles
        self.nb_joueurs = nb_joueurs
        self.nb_fioles = len(types_fioles)
        self.allocations = allocations or generer_allocations(nb_joueurs, self.nb_fioles) 
        self.meilleure_fixe = meilleure_fixe
        self.top_allocs = top_allocs

    def choisir(self, historique, mon_equipe): # histo c'est une liste
        raise NotImplementedError

    def reset(self):
        pass


class AleatoireUniforme(Strategie):
    def __init__(self, types_fioles, allocations=None, meilleure_fixe=None, top_allocs=None):
        super().__init__("aleatoire", types_fioles, allocations=allocations, meilleure_fixe=meilleure_fixe, top_allocs=top_allocs)

    def choisir(self, historique, mon_equipe):
        return random.choice(self.allocations)


class Fixe(Strategie):
    def __init__(self, types_fioles, alloc_fixe=None, allocations=None, meilleure_fixe=None, top_allocs=None):
        super().__init__("tetu", types_fioles, allocations=allocations, meilleure_fixe=meilleure_fixe, top_allocs=top_allocs)
        
        self.alloc_fixe = alloc_fixe or self.meilleure_fixe #celle donner par prepare carte
        
        if self.alloc_fixe is None:
            self.alloc_fixe, _ = analyser_allocations(types_fioles, self.allocations)

    def choisir(self, historique, mon_equipe):
        return self.alloc_fixe
    
class AleatoireExpert(Strategie):
    def __init__(self, types_fioles, allocations=None, meilleure_fixe=None, top_allocs=None):
        super().__init__("expert", types_fioles, allocations=allocations,
                        meilleure_fixe=meilleure_fixe, top_allocs=top_allocs)
        
        # pareil si on a pas les top allocs on les calcule
        if self.top_allocs is None:
            _, self.top_allocs = analyser_allocations(types_fioles, self.allocations)

    def choisir(self, historique, mon_equipe):
        return random.choice(self.top_allocs)


class FictitiousPlay(Strategie):
    def __init__(self, types_fioles, allocations=None, meilleure_fixe=None, top_allocs=None):           
        super().__init__("fictitious", types_fioles, allocations=allocations, meilleure_fixe=meilleure_fixe, top_allocs=top_allocs) 
                                 
        # gains cumules de chaque allocation                              
        self.gains = np.zeros(len(self.allocations))                                                    
                                                                
    def choisir(self, historique, mon_equipe):                                                          
    
        if len(historique) == 0:                                
            # premier tour on a aucune info on joue la meilleure fixe                                
            return self.meilleure_fixe or random.choice(self.allocations)                               
                                                                                                        
        # mise a jour incrementale avec la derniere allo adverse                                       
        alloc_adv = historique[-1][1]                                                                   
        for i, alloc in enumerate(self.allocations):                                                    
            p0, p1 = calculer_score(alloc, alloc_adv, self.types_fioles)
            self.gains[i] += p0 - p1                                                                    
                                                                                                        
        # jouer l'alloc avec le meilleur gain cumule                                                    
        return self.allocations[np.argmax(self.gains)]                                                  
                                                                                                        
    def reset(self):
        self.gains = np.zeros(len(self.allocations))  
