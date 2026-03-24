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

    def choisir(self, historique, mon_equipe): # histo c'est une 
        raise NotImplementedError

    def reset(self):
        pass


class AleatoireUniforme(Strategie):
    def __init__(self, types_fioles, allocations=None, meilleure_fixe=None, top_allocs=None, nb_joueurs=8):
        super().__init__("aleatoire", types_fioles, nb_joueurs=nb_joueurs, allocations=allocations, meilleure_fixe=meilleure_fixe, top_allocs=top_allocs)

    def choisir(self, historique, mon_equipe):
        return random.choice(self.allocations)


class Tetu(Strategie):
    def __init__(self, types_fioles, alloc_fixe=None, allocations=None, meilleure_fixe=None, top_allocs=None, nb_joueurs=8):
        super().__init__("tetu", types_fioles, nb_joueurs=nb_joueurs, allocations=allocations, meilleure_fixe=meilleure_fixe, top_allocs=top_allocs)
        
        self.alloc_fixe = alloc_fixe or self.meilleure_fixe #celle donner par prepare_carte
        
        if self.alloc_fixe is None:
            self.alloc_fixe, _ = analyser_allocations(types_fioles, self.allocations)

    def choisir(self, historique, mon_equipe):
        return self.alloc_fixe
    
class AleatoireExpert(Strategie):
    def __init__(self, types_fioles, allocations=None, meilleure_fixe=None, top_allocs=None, nb_joueurs=8):
        super().__init__("expert", types_fioles, nb_joueurs=nb_joueurs, allocations=allocations,
                        meilleure_fixe=meilleure_fixe, top_allocs=top_allocs)
        
        # pareil si on a pas les top allocs on les calcule
        if self.top_allocs is None:
            _, self.top_allocs = analyser_allocations(types_fioles, self.allocations)

    def choisir(self, historique, mon_equipe):
        return random.choice(self.top_allocs)

class AleatoireCoordonne(Strategie):
    def __init__(self, types_fioles, allocations=None, meilleure_fixe=None, top_allocs=None, nb_joueurs=8):
        super().__init__("coordonne", types_fioles, nb_joueurs=nb_joueurs, allocations=allocations, meilleure_fixe=meilleure_fixe, top_allocs=top_allocs)

        if self.top_allocs is None:
            _, self.top_allocs = analyser_allocations(types_fioles, self.allocations)

        self.poids = np.array([max(a) for a in self.top_allocs], dtype=float)
        self.poids /= self.poids.sum()

    def choisir(self, historique, mon_equipe):
        idx = np.random.choice(len(self.top_allocs), p=self.poids)
        return self.top_allocs[idx]

class FictitiousPlay(Strategie):
    def __init__(self, types_fioles, allocations=None, meilleure_fixe=None, top_allocs=None, nb_joueurs=8):
        super().__init__("fictitious", types_fioles, nb_joueurs=nb_joueurs, allocations=allocations, meilleure_fixe=meilleure_fixe, top_allocs=top_allocs) 
                                 
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
      def __init__(self, types_fioles, allocations=None, meilleure_fixe=None, top_allocs=None, nb_joueurs=8):
          super().__init__("regret", types_fioles, nb_joueurs=nb_joueurs, allocations=allocations, meilleure_fixe=meilleure_fixe, top_allocs=top_allocs)

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
    def __init__(self, types_fioles, allocations=None, meilleure_fixe=None, top_allocs=None, nb_joueurs=8):
        super().__init__("meta", types_fioles, nb_joueurs=nb_joueurs, allocations=allocations, meilleure_fixe=meilleure_fixe, top_allocs=top_allocs)

        if self.meilleure_fixe is None:
            self.meilleure_fixe, _ = analyser_allocations(types_fioles, self.allocations)

        # analyse de la composition de la carte si tout est bleu ou pas 
        self.compo = Counter(types_fioles)
        self.all_blue = self.compo.get("bleue", 0) == self.nb_fioles

        # on spread pour les cartes toute bleue
        # chaque fiole a 8 cases autour donc max 8 joueurs par fiole
        max_par_fiole = 8
        if self.all_blue and self.nb_joueurs >= self.nb_fioles:
            base = [1] * self.nb_fioles
            reste = self.nb_joueurs - self.nb_fioles

            # on repartit le surplus en remplissant fiole par fiole sans depasser le max
            i = 0
            while reste > 0 and i < self.nb_fioles:
                ajout = min(reste, max_par_fiole - base[i])
                base[i] += ajout
                reste -= ajout
                i += 1
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

    def choisir(self, historique, mon_equipe):
        nb_tours = len(historique)

        # mettre a jour nos donnees internes avec le dernier tour joue
        if nb_tours > 0:
            mon_alloc, alloc_adv, (mon_pts, ses_pts) = historique[-1]
            self.hist_adv.append(alloc_adv)
            gain_reel = mon_pts - ses_pts

            # decay puis update des weighted gains + regrets
            self.weighted_gains *= self.decay
            for i, alt in enumerate(self.allocations):
                p0, p1 = calculer_score(alt, alloc_adv, self.types_fioles)
                gain_alt = p0 - p1
                self.weighted_gains[i] += gain_alt
                self.regrets[i] += gain_alt - gain_reel

        # cas special : carte toute bleue => spread pas de besoin de classzr l'adv
        if self.all_blue and self.spread_blue:
            return self.spread_blue

        # exploration : 1 seul tour suffit, on prend au hasard
        if nb_tours < 1:
            return self._alloc_defaut()

        # classifier l'adversaire ou reclassifier tous les 8 tours
        if self.classification is None or nb_tours - self.dernier_recalcul >= 8:
            self.classification = self._classifier()
            self.dernier_recalcul = nb_tours

        # exploitation avec epsilon greedy (le cours de stats/proba qui carry) : 10% du temps on joue une top alloc au hasard
        if random.random() < 0.1 and self.top_allocs:
            alloc = random.choice(self.top_allocs)

        elif self.classification == "fixe":
            # on sait ce qu'il joue -< on fait la best response 
            alloc = best_response(self.types_fioles, self.hist_adv[-1], self.allocations)
        else:
            # aleatoire ou adaptatif : weighted best response ca permet de s'adapter si il change de strat au fur des episodes
            alloc = self.allocations[np.argmax(self.weighted_gains)]

        # post traitement : optimiser l'alloc en forcant 1 joueur sur les bleues si ca a pas ete fait avant
        alloc = self._optimiser_bleues(alloc)
        return alloc
    

    def _alloc_defaut(self):
        # allocation par defaut : on tire au hasard parmi les top allocs
        if self.top_allocs:
            alloc = random.choice(self.top_allocs)
        else:
            alloc = self.meilleure_fixe
        return self._optimiser_bleues(alloc)

    def _classifier(self):
        if len(self.hist_adv) < 2:
            return None

        recents = self.hist_adv[-min(10, len(self.hist_adv)):]
        uniques = set(recents)
        
        if len(uniques) <= 2:
            return "fixe"

        # entropie de Shannon
        counts = Counter(recents)
        n = len(recents)
        ent = -sum((c / n) * np.log2(c / n) for c in counts.values())
        max_ent = np.log2(n) if n > 1 else 1

        ratio = ent / max_ent if max_ent > 0 else 0

        if ratio < 0.3:
            return "fixe"
        elif ratio > 0.7:
            return "aleatoire"
        return "adaptatif"

    def _optimiser_bleues(self, alloc):
        # sur chaque fiole bleue : forcer exactement 1 joueur sauf si l'adversaire envoie systematiquement 0 dans ce cas on gaspille pas

        if not self.idx_bleues:
            return alloc

        alloc = list(alloc)
        for b in self.idx_bleues:
            # si on a assez d'historique, verifier que l'adversaire met pas toujours 0
            if len(self.hist_adv) >= 3:
                recents = self.hist_adv[-min(5, len(self.hist_adv)):]
                nb_zero = sum(1 for a in recents if a[b] == 0)
                # si l'adversaire met 0 tout le temps c pas la peine
                if nb_zero == len(recents):
                    continue

            # forcer 1 joueur sur cette bleue
            if alloc[b] == 1:
                continue
            if alloc[b] == 0:
                # si la strategie a mis 0 ici, c'est que les joueurs sont mieux ailleurs
                # on touche pas ca vaut pas le coup de sacrifier une autre fiole
                continue

            # alloc[b] >= 2 on redistribue le surplus
            surplus = alloc[b] - 1
            alloc[b] = 1
            self._redistribuer(alloc, surplus, b)

        return tuple(alloc)

    def _redistribuer(self, alloc, surplus, exclude):
        # redistribue les joueurs en surplus sur les autres fioles
        # priorite : jaunes (1 joueur suffit), rouges (besoin de 2), vertes 3 je crois
        if surplus <= 0:
            return
        
        for idx_list in [self.idx_jaunes, self.idx_rouges, self.idx_vertes]:
            for i in idx_list:
                if i != exclude:
                    alloc[i] += surplus
                    return
                
        # dans le pire des cas : n'importe quelle fiole
        for i in range(len(alloc)):
            if i != exclude:
                alloc[i] += surplus
                return

    def reset(self):
        self.weighted_gains = np.zeros(len(self.allocations))
        self.regrets = np.zeros(len(self.allocations))
        self.hist_adv = []
        self.classification = None
        self.dernier_recalcul = 0

def creer_strategie(nom, types_fioles, carte_data=None):
    params = {}
    if carte_data:
        params = {
            'allocations': carte_data['allocations'],
            'meilleure_fixe': carte_data['meilleure_fixe'],
            'top_allocs': carte_data['top_allocs'],
            'nb_joueurs': carte_data.get('nb_joueurs', 8), 
        }

    strats = {
        "aleatoire": AleatoireUniforme,
        "tetu": Tetu,
        "expert": AleatoireExpert,
        "coordonne": AleatoireCoordonne,
        "fictitious": FictitiousPlay,
        "regret": RegretMatching,
        "meta": MetaStrategie,
    }
    if nom not in strats:
        print(f"Strategie inconnue: {nom}")
        return None
    return strats[nom](types_fioles, **params)