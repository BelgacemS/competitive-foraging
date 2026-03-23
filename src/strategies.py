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

class AleatoireCoordonne(Strategie):
    def __init__(self, types_fioles, allocations=None, meilleure_fixe=None, top_allocs=None):
        super().__init__("coordonne", types_fioles, allocations=allocations, meilleure_fixe=meilleure_fixe, top_allocs=top_allocs)

        if self.top_allocs is None:
            _, self.top_allocs = analyser_allocations(types_fioles, self.allocations)

        self.poids = np.array([max(a) for a in self.top_allocs], dtype=float)
        self.poids /= self.poids.sum()

    def choisir(self, historique, mon_equipe):
        idx = np.random.choice(len(self.top_allocs), p=self.poids)
        return self.top_allocs[idx]

class FictitiousPlay(Strategie):
    def __init__(self, types_fioles, allocations=None, meilleure_fixe=None, top_allocs=None):           
        super().__init__("fictitious", types_fioles, allocations=allocations, meilleure_fixe=meilleure_fixe, top_allocs=top_allocs) 
                                 
        # gains cumules de chaque allocation                              
        self.gains = np.zeros(len(self.allocations))                                                    
                                                                
    def choisir(self, historique, mon_equipe):                                                          
    
        if len(historique) == 0:                                
            # premier tour on a aucune info on joue la meilleure fixe                                
            return self.meilleure_fixe or random.choice(self.allocations)                               
                                                                                                        
        # mise a jour incrementale avec la derniere alloc adverse                                       
        alloc_adv = historique[-1][1]                                                                   
        for i, alloc in enumerate(self.allocations):                                                    
            p0, p1 = calculer_score(alloc, alloc_adv, self.types_fioles)
            self.gains[i] += p0 - p1                                                                    
                                                                                                        
        # jouer l'alloc avec le meilleur gain cumule                                                    
        return self.allocations[np.argmax(self.gains)]                                                  
                                                                                                        
    def reset(self):
        self.gains = np.zeros(len(self.allocations))  


class RegretMatching(Strategie):
      def __init__(self, types_fioles, allocations=None, meilleure_fixe=None, top_allocs=None):
          super().__init__("regret", types_fioles, allocations=allocations, meilleure_fixe=meilleure_fixe, top_allocs=top_allocs)

          self.regrets = np.zeros(len(self.allocations))

      def choisir(self, historique, mon_equipe):
          if len(historique) == 0:
              return self.meilleure_fixe or random.choice(self.allocations)

          # mettre a jour les regrets avec le dernier tour
          _, alloc_adv, (mon_pts, ses_pts) = historique[-1]
          gain_reel = mon_pts - ses_pts

          for i, alloc_alt in enumerate(self.allocations):
              p0, p1 = calculer_score(alloc_alt, alloc_adv, self.types_fioles)
              gain_alt = p0 - p1
              self.regrets[i] += gain_alt - gain_reel

          # jouer proportionnellement aux regrets positifs
          reg_pos = np.maximum(self.regrets, 0)
          total = reg_pos.sum()
          if total <= 0:
              return random.choice(self.allocations)
          
          probas = reg_pos / total
          idx = np.random.choice(len(self.allocations), p=probas)
          return self.allocations[idx]

      def reset(self):
          self.regrets = np.zeros(len(self.allocations))

class MetaStrategie(Strategie):
    def __init__(self, types_fioles, allocations=None, meilleure_fixe=None, top_allocs=None):
        super().__init__("meta", types_fioles, allocations=allocations, meilleure_fixe=meilleure_fixe, top_allocs=top_allocs)

        if self.meilleure_fixe is None:
            self.meilleure_fixe, _ = analyser_allocations(types_fioles, self.allocations)

        # analyse de la composition de la carte si tout est bleu ou pas 
        self.compo = Counter(types_fioles)
        self.all_blue = self.compo.get("bleue", 0) == self.nb_fioles

        # on spread pour les cartes tout-bleue 
        if self.all_blue and self.nb_joueurs >= self.nb_fioles:
            base = [0] * self.nb_fioles

            for i in range(min(self.nb_joueurs, self.nb_fioles)):
                base[i] = 1
            reste = self.nb_joueurs - min(self.nb_joueurs, self.nb_fioles)

            if reste > 0:
                base[0] += reste
            self.spread_blue = tuple(base)
        else:
            self.spread_blue = None

        # indices des fioles par type
        self.idx_bleues = [i for i, t in enumerate(types_fioles) if t == "bleue"]
        self.idx_jaunes = [i for i, t in enumerate(types_fioles) if t == "jaune"]
        self.idx_rouges = [i for i, t in enumerate(types_fioles) if t == "rouge"]
        self.idx_vertes = [i for i, t in enumerate(types_fioles) if t == "verte"]


        self.weighted_gains = np.zeros(len(self.allocations))
        self.decay = 0.85

        # regrets (gardes au cas ou)
        self.regrets = np.zeros(len(self.allocations))

        # suivi de l'adversaire
        self.hist_adv = []
        self.classification = None
        self.dernier_recalcul = 0