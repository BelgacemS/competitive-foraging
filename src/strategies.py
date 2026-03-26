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

    def choisir(self, historique, mon_equipe): # histo c'est une liste de tuples
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
        
        self.alloc_fixe = alloc_fixe or self.meilleure_fixe # celle donner par prepare_carte
        
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
                                                                                                        
        # jouer l'alloc avec le meilleur gai cumule                                                    
        return self.allocations[np.argmax(self.gains)]                                                  
                                                                                                        
    def reset(self):
        self.gains = np.zeros(len(self.allocations))  


class RegretMatching(Strategie):
      def __init__(self, types_fioles, allocations=None, meilleure_fixe=None, top_allocs=None, nb_joueurs=8):
          super().__init__("regret", types_fioles, nb_joueurs=nb_joueurs, allocations=allocations, meilleure_fixe=meilleure_fixe, top_allocs=top_allocs)

          if self.top_allocs is None:
              _, self.top_allocs = analyser_allocations(types_fioles, self.allocations)

          self.regrets = np.zeros(len(self.top_allocs))

      def choisir(self, historique, mon_equipe):
          if len(historique) == 0:
              return self.meilleure_fixe or random.choice(self.top_allocs)

          # mettre a jour les regrets avec le dernier tour
          _, alloc_adv, (mon_pts, ses_pts) = historique[-1]
          gain_reel = mon_pts - ses_pts

          for i, alloc_alt in enumerate(self.top_allocs):
              p0, p1 = calculer_score(alloc_alt, alloc_adv, self.types_fioles)
              gain_alt = p0 - p1
              self.regrets[i] += gain_alt - gain_reel

          # jouer proportionnellement aux regrets positifs
          reg_pos = np.maximum(self.regrets, 0)
          total = reg_pos.sum()
          if total <= 0:
              return self.meilleure_fixe or random.choice(self.top_allocs)

          probas = reg_pos / total
          idx = np.random.choice(len(self.top_allocs), p=probas)
          return self.top_allocs[idx]

      def reset(self):
          self.regrets = np.zeros(len(self.top_allocs))

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

        # tour 0 : pas d'historique -> jouer le defaut
        if nb_tours < 1:
            return self._alloc_defaut()

        # carte all-blue : toujours spread (1 spy par fiole, surplus concentre)
        # au pire on fait egalit au mieux nos spies battent les groupes adverses
        if self.all_blue and self.spread_blue:
            return self.spread_blue

        # classifier l'adversaire ou reclassifier tous les 5 tours
        if self.classification is None or nb_tours - self.dernier_recalcul >= 5:
            self.classification = self._classifier()
            self.dernier_recalcul = nb_tours

        # epsilon greedy : 5% exploration
        if random.random() < 0.05 and self.top_allocs:
            alloc = random.choice(self.top_allocs)
        elif self.classification == "fixe":
            alloc = best_response(self.types_fioles, self.hist_adv[-1], self.allocations)
        elif self.classification == "aleatoire":
            alloc = random.choice(self.top_allocs)
        else:
            # adaptatif ou pas encore classifie : weighted best response
            alloc = self.allocations[np.argmax(self.weighted_gains)]

        # post traitement : optimiser les bleues sur cartes mixtes
        alloc = self._optimiser_bleues(alloc)
        return alloc


    def _alloc_defaut(self):
        # tour 0 : sur carte all-blue on spread sinon on prend un top alloc
        if self.all_blue and self.spread_blue:
            return self.spread_blue
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

        # si tout est identique c'est fixe meme avec peu d'observations
        if len(uniques) == 1:
            return "fixe"

        # pour les autres classifications attendre 5 observations
        if len(self.hist_adv) < 5:
            return None

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

    def _top_k_sample(self, values, k=50):
        # sample proportionnellement parmi les k meilleures allocations par valeur positive

        vals_pos = np.maximum(values, 0)
        k = min(k, len(values))
        top_indices = np.argsort(vals_pos)[-k:]
        top_vals = vals_pos[top_indices]
        total = top_vals.sum()
        if total <= 0:
            return self.meilleure_fixe
        probas = top_vals / total
        idx = np.random.choice(top_indices, p=probas)
        return self.allocations[idx]

    def _optimiser_bleues(self, alloc):
        # sur chaque fiole bleue :
        # - si on a 0 et l'adversaire met 2+ : ajouter un joueur spy (voler 1 joueur d'ailleurs)
        # - si on a 2+ : reduire a 1 et redistribuer le surplus

        if not self.idx_bleues:
            return alloc

        alloc = list(alloc)
        for b in self.idx_bleues:
            if alloc[b] == 0:
                # si l'adversaire met 2+ ici on ajoute un spy pour gagner la fiole
                if len(self.hist_adv) >= 3:
                    recents = self.hist_adv[-min(5, len(self.hist_adv)):]
                    if all(a[b] >= 2 for a in recents):
                        # voler 1 joueur de la fiole non-bleue la plus chargee
                        candidats = [i for i in range(len(alloc))
                                     if i != b and i not in self.idx_bleues and alloc[i] > 1]
                        if candidats:
                            max_idx = max(candidats, key=lambda i: alloc[i])
                            alloc[max_idx] -= 1
                            alloc[b] = 1
                continue
            if alloc[b] == 1:
                continue

            # alloc[b] >= 2 : redistribuer le surplus
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