# Rapport de projet

## Groupe

* Belgacem Smaali
* Khaled Bouhabel


## Description des choix importants d'implémentation

### Architecture générale

On a séparé le code en trois modules principaux :
- `utils.py` : toutes les fonctions de base (scoring, génération d'allocations, analyse)
- `strategies.py` : les 7 stratégies d'allocation, de la plus simple à la plus avancée
- `tournoi.py` : le système de round-robin pour évaluer les stratégies sans pygame

L'idée c'est de pouvoir tester les stratégies rapidement sans lancer le jeu graphique. Le tournoi simule des matchs en utilisant directement la fonction de scoring, sans A*, sans sprites, sans affichage. Ca permet de faire tourner 1050 matchs en ~40 minutes au lieu de plusieurs heures.

### Fonctions principales de `utils.py`

#### `generer_allocations(nb_joueurs, nb_fioles, max_allocs=15000)`

Génère toutes les façons de répartir les joueurs sur les fioles. Une allocation c'est un tuple qui dit combien de joueurs on envoie sur chaque fiole. Par exemple avec 8 joueurs et 5 fioles, `(3, 2, 1, 1, 1)` veut dire 3 joueurs sur la fiole 0, 2 sur la fiole 1, etc.

On utilise l'algorithme étoiles et barres via une récursion : Ca donne C(n+k-1, k-1) allocations au total.

Sur les petites cartes (8 joueurs, 5 fioles), il y a 495 allocations, c'est gérable. Mais sur les grandes cartes (17 joueurs, 8 fioles), on atteint 346 104 allocations. C'est trop lent pour les algorithmes qui itèrent dessus à chaque tour. Notre solution : on génère tout puis on échantillonne aléatoirement 15 000 avec `random.sample`.

#### `score_fiole(type_fiole, nb_j0, nb_j1)`

Calcule qui gagne une fiole en fonction de son type et du nombre de joueurs de chaque équipe. Les règles varient selon le type :

#### `calculer_score(alloc0, alloc1, types_fioles, priorite=0)`

Calcule le score d'un épisode en appelant `score_fiole` sur chaque fiole. Gère aussi le cas où les deux équipes mettent plus de 8 joueurs combinés sur une fiole : l'équipe prioritaire (qui alterne à chaque épisode) se place en premier, l'autre occupe les places restantes.

#### `analyser_allocations(types_fioles, allocations, k=10, nb_sample=1000)`

Evalue toutes les allocations pour trouver les meilleures. Pour chaque allocation, on simule des matchs contre un échantillon de 1000 adversaires aléatoires et on compte les victoires. On retourne la `meilleure_fixe` (celle qui gagne le plus souvent) et les `top_allocs` (les k=10 meilleures). Ces résultats sont pré-calculés une fois par carte et réutilisés par toutes les stratégies.

#### `preparer_carte(nom_carte)`

Point d'entrée qui orchestre tout : charge les types de fioles depuis le JSON, détecte le nombre de joueurs, génère les allocations et lance `analyser_allocations`. Retourne un dictionnaire avec tout ce qu'il faut pour créer les stratégies.

#### `best_response(types_fioles, alloc_adv, allocations)`

Teste toutes les allocations contre une allocation adverse fixe et retourne celle qui maximise le gain (notre score - score adverse). C'est utilisé par meta quand elle détecte un adversaire fixe.

### Contrainte physique (max 8 par fiole)

Sur le plateau de jeu, chaque fiole a 8 cases adjacentes. On ne peut pas placer plus de 8 joueurs autour d'une fiole. Dans le tournoi, on simule cette contrainte avec `appliquer_contrainte_physique` : si une allocation met plus de 8 joueurs sur une fiole, le surplus est redistribué sur les fioles les moins chargées. La fonction `calculer_score` gère aussi le cas où les deux équipes combinées dépassent 8 sur une même fiole, avec le système de priorité alternée.

### Choix de 50 épisodes par match

On joue 50 épisodes par match avec 10 runs par matchup. C'est un compromis entre significativité statistique et temps de calcul. Avec 7 stratégies, 5 cartes et 10 runs, ça fait 1050 matchs. Chaque match implique des itérations sur 15 000 allocations pour les stratégies adaptatives (fictitious, meta), donc le temps total est d'environ 40 minutes. Plus d'épisodes permettrait une meilleure convergence des stratégies adaptatives mais rendrait le tournoi trop long.

## Description des stratégies proposées

On a implémenté 7 stratégies, classées de la plus simple à la plus complexe. Chaque stratégie hérite de la classe `Strategie` qui définit l'interface commune : une méthode `choisir(historique, mon_equipe)` qui retourne une allocation.

### 1. Aléatoire Uniforme (`aleatoire`)

La stratégie de base : elle tire une allocation au hasard parmi toutes les allocations possibles. C'est notre référence pour évaluer les autres, une stratégie qui ne bat même pas l'aléatoire n'a pas d'intérêt. En pratique, avec 15 000 allocations, la probabilité de tomber sur une bonne est très faible, donc elle perd contre tout le monde.

Chemin d'appel :
1. `creer_strategie("aleatoire", types, carte_data)` crée une instance avec les allocations pré-générées
2. A chaque tour, `choisir()` appelle `random.choice(self.allocations)` sur les 15 000 allocations
3. L'allocation retournée est passée à `appliquer_contrainte_physique()` puis à `calculer_score()` dans le tournoi

### 2. Têtu (`tetu`)

Joue toujours la même allocation : la `meilleure_fixe`, calculée par `analyser_allocations`. Cette fonction évalue chaque allocation contre un échantillon d'adversaires aléatoires et garde celle qui gagne le plus souvent. C'est la meilleure stratégie si l'adversaire est aléatoire, mais elle est prédictible, un adversaire adaptatif peut la contrer facilement.

Chemin d'appel :
1. A l'initialisation, récupère `meilleure_fixe` depuis `carte_data` (pré-calculée par `preparer_carte` → `analyser_allocations`)
2. A chaque tour, `choisir()` retourne toujours `self.alloc_fixe` (= `meilleure_fixe`)
3. Aucun appel à des fonctions de utils pendant le jeu, tout est décidé à l'init

### 3. Aléatoire Expert (`expert`)

Tire au hasard parmi les 10 meilleures allocations (top_allocs) au lieu de toutes. Ces top allocations sont pré-calculées par `analyser_allocations` qui classe les allocations par win rate contre des adversaires aléatoires. C'est mieux que l'aléatoire pur car les options sont filtrées, mais ça reste non-adaptatif.

Chemin d'appel :
1. A l'initialisation, récupère `top_allocs` depuis `carte_data` (les 10 meilleures de `analyser_allocations`)
2. A chaque tour, `choisir()` appelle `random.choice(self.top_allocs)` sur les 10 meilleures
3. Comme têtu, pas d'appel à utils pendant le jeu

### 4. Aléatoire Coordonné (`coordonne`)

Comme expert mais avec des poids : les allocations les plus concentrées (celles avec un max plus élevé) sont jouées plus souvent. L'intuition c'est que concentrer ses joueurs est souvent plus efficace que les disperser (surtout sur les fioles vertes et rouges qui nécessitent un seuil minimum). Les poids sont calculés comme `max(allocation)` normalisé.

Chemin d'appel :
1. A l'initialisation, calcule les poids `max(alloc)` pour chaque top_alloc et normalise
2. A chaque tour, `choisir()` fait un `np.random.choice` pondéré sur les top_allocs
3. Les allocations concentrées (ex: `(5, 3, 0, 0, 0)` avec max=5) sont tirées plus souvent que les étalées (ex: `(2, 2, 2, 1, 1)` avec max=2)

### 5. Fictitious Play (`fictitious`)

Premier algorithme adaptatif. On joue la meilleure réponse à la distribution empirique des coups adverses.

Concrètement, pour chaque allocation possible, on accumule le gain (notre score - score adversaire) qu'elle aurait donné contre chaque coup adverse passé. Puis on joue l'allocation avec le gain cumulé le plus élevé (`argmax`).

Chemin d'appel :
1. Tour 0 : joue `meilleure_fixe` (pas d'historique)
2. Tour t > 0 :
   - Récupère `alloc_adv = historique[-1][1]` (le dernier coup adverse)
   - Pour chaque allocation i parmi les 15 000 : appelle `calculer_score(alloc_i, alloc_adv, types)` pour obtenir le gain hypothétique
   - Accumule dans `gains[i] += p0 - p1`
   - Joue `allocations[np.argmax(gains)]`

C'est la stratégie qui fait le plus d'appels à `calculer_score` par tour (15 000 appels). Robinsonje c a prouvé que fictitious play converge vers un équilibre de Nash dans les jeux à deux joueurs à somme nulle. Contre un adversaire fixe, il trouve le meilleur counter en 1 tour. Contre un adversaire adaptatif, les deux finissent par converger vers l'équilibre.

### 6. Regret Matching (`regret`)

Le principe : en jouant proportionnellement aux regrets positifs, le regret moyen converge vers 0, ce qui signifie qu'on approche un équilibre corrélé.

Le regret d'une action c'est "combien j'aurais gagné de plus si j'avais joué cette action au lieu de ce que j'ai réellement joué". On accumule les regrets de chaque allocation, on garde les positifs et on sample proportionnellement.

Notre implémentation utilise les `top_allocs` (10 meilleures allocations) comme espace d'actions au lieu des 15 000. C'est un compromis : plus d'allocations donnerait une meilleure exploration de l'espace de jeu, mais la convergence serait plus lente. La borne théorique de convergence est O(√(ln(N)/T)) où N est le nombre d'actions et T le nombre de tours : avec N=15 000 et T=50, le regret moyen est encore ~0.44 (trop bruité pour converger). Avec N=10, on obtient ~0.21, suffisant pour une convergence raisonnable en 50 épisodes. On a testé avec N=20 et N=50 : augmenter N améliore l'exploration mais rend regret trop fort (il converge vers des counters que les autres stratégies ne trouvent pas), au prix d'une plus grande variance entre les runs.

Chemin d'appel :
1. Tour 0 : joue `meilleure_fixe`
2. Tour t > 0 :
   - Récupère `alloc_adv` et `gain_reel = mon_pts - ses_pts` depuis l'historique
   - Pour chaque top_alloc i (10 seulement) : appelle `calculer_score(top_alloc_i, alloc_adv, types)` pour obtenir `gain_alt`
   - Met à jour `regrets[i] += gain_alt - gain_reel`
   - Calcule `reg_pos = max(regrets, 0)`, normalise en probabilités
   - Sample une allocation avec `np.random.choice(top_allocs, p=probas)`
   - Si tous les regrets sont négatifs (on a joué le mieux possible), joue `meilleure_fixe`

La différence clé avec fictitious : fictitious itère sur 15 000 allocations et prend le meilleur (déterministe). Regret itère sur 10 et sample (stochastique). Fictitious est plus précis, regret a de meilleures garanties théoriques mais converge plus lentement.

### 7. Méta Stratégie (`meta`)

Notre stratégie qui combine plusieurs techniques pour s'adapter à n'importe quel adversaire. L'idée : au lieu d'utiliser un seul algorithme, on classifie l'adversaire et on adapte notre réponse.

#### Classification de l'adversaire

Après 5 observations de l'adversaire, on calcule l'entropie de Shannon de ses derniers coups :
- Entropie basse (ratio < 0.3) ou 1 seule valeur unique -> adversaire fixe (type têtu)
- Entropie haute (ratio > 0.7) → adversaire aléatoire (type expert/coordonné)
- Entropie moyenne → adversaire adaptatif* (type fictitious/regret)

La détection d'un adversaire fixe est rapide : dès qu'on voit 2 coups identiques consécutifs, on classifie comme "fixe" sans attendre les 5 observations.

#### Réponse adaptée

- Contre un adversaire fixe : `best_response`  : on teste toutes les 15 000 allocations contre son dernier coup et on prend la meilleure. C'est le counter parfait, il donne le gain maximal possible.

- Contre un adversaire aléatoire : on joue au hasard parmi les `top_allocs`. Contre un adversaire imprévisible, diversifier nos coups est la meilleure défense  : ça évite d'être exploité par un pattern détectable.

- Contre un adversaire adaptatif : comme fictitious play mais avec un decay de 0.85. Le decay donne plus de poids aux observations récentes, ce qui permet de réagir plus vite quand l'adversaire change de stratégie.

#### Exploration epsilon-greedy

5% du temps, on joue une top_alloc au hasard au lieu de suivre la stratégie. C'est le principe de l'epsilon-greedy (vu en cours de stats/proba) : un petit taux d'exploration pour ne pas rester bloqué dans un pattern prédictible.

#### Optimisation pour les cartes bleues

Les fioles bleues ont une mécanique spéciale : un joueur seul (spy) bat un groupe de 2+. C'est un mécanisme de sabotage qui change la dynamique du jeu.

Sur les cartes entièrement bleues (blue-map), on pré-calcule un `spread_blue` au tour 0 : 1 joueur sur chaque fiole, surplus sur une seule fiole (cappé à 8 joueurs max par contrainte physique). Dès le tour 1, on adapte normalement.

Sur les cartes mixtes, `_optimiser_bleues` fait deux choses après chaque choix d'allocation :
1. Spy-in : si l'adversaire met régulièrement 2+ joueurs sur une fiole bleue où on a 0, on vole 1 joueur d'une autre fiole pour placer un spy et gagner cette fiole gratuitement.
2. Réduction : si on a 2+ joueurs sur une fiole bleue, on réduit à 1 (un spy suffit) et on redistribue le surplus sur les fioles non-bleues.

#### Reclassification

L'adversaire peut changer de comportement au cours du match. On reclassifie tous les 5 tours pour s'adapter. Par exemple, un adversaire qui commence aléatoire puis converge vers une stratégie fixe sera détecté et contré.

Chemin d'appel complet :
1. A l'initialisation : `preparer_carte` fournit allocations, top_allocs, meilleure_fixe. Meta pré-calcule `spread_blue` et les indices de fioles par type.
2. Tour 0 : `_alloc_defaut()` retourne `spread_blue` sur blue-map, sinon `random.choice(top_allocs)` passé dans `_optimiser_bleues`
3. Tour t > 0 :
   - Récupère `alloc_adv` et `gain_reel` depuis l'historique
   - Pour chaque allocation i (15 000) : appelle `calculer_score(alloc_i, alloc_adv, types)`, met à jour `weighted_gains[i]` (avec decay ×0.85) et `regrets[i]` (sans decay)
   - Si t est multiple de 5 : `_classifier()` reclassifie l'adversaire
   - 5% chance : exploration (random top_alloc)
   - Sinon : réponse adaptée selon la classification
   - Post-traitement : `_optimiser_bleues` sur cartes mixtes

## Description des résultats

### Protocole expérimental

Le tournoi est un round-robin : chaque paire de stratégies s'affronte sur chaque carte. Pour la significativité statistique, chaque matchup est répété 10 fois (10 runs de 50 épisodes). Le classement compte les victoires totales (un match gagné = 1 victoire, un draw = 0 pour les deux).

Cartes utilisées :
- yellow-map : 5 fioles jaunes, 8 joueurs/équipe (495 allocations)
- red-map : 5 fioles rouges, 8 joueurs/équipe (495 allocations)
- green-map : 8 fioles vertes, 17 joueurs/équipe (15 000 allocations échantillonnées)
- blue-map : 8 fioles bleues, 17 joueurs/équipe (15 000 allocations échantillonnées)
- mixed-map : 9 fioles mixtes, 17 joueurs/équipe (15 000 allocations échantillonnées)

### Classement global

| Rang | Stratégie | Victoires (/300) |
|------|-----------|-------------------|
| 1 | meta | 255 |
| 2 | fictitious | 240 |
| 3 | regret | 165 |
| 4 | coordonne | 118 |
| 5 | expert | 108 |
| 6 | tetu | 80 |
| 7 | aleatoire | 0 |

Meta termine première avec 255 victoires, 15 points devant fictitious (240). On observe une hiérarchie claire en trois paliers : les stratégies adaptatives (meta, fictitious, regret) dominent les stratégies statiques (coordonne, expert, tetu), qui elles-mêmes écrasent l'aléatoire.

### Analyse par carte

#### Yellow-map et Red-map (petites cartes, 495 allocations)

Ces cartes sont les plus "propres" car toutes les allocations sont énumérées (pas d'échantillonnage). Les résultats sont très nets :

- Meta domine tout le monde (10-0 contre chaque adversaire sur yellow, quasi-parfait sur red)
- Fictitious est second, avec 10-0 contre regret grâce à son approche déterministe (argmax sur 15 000 allocations) vs le sampling bruité de regret (sur 10 top_allocs)
- Tetu, expert, coordonné et regret font de nombreux draws entre eux sur yellow-map

#### Le phénomène des draws sur yellow-map

C'est un des résultats les plus marquants du tournoi. Sur yellow-map, on observe un nombre anormalement élevé de draws entre les stratégies statiques :

- `tetu vs expert : 0W-10D-0L` (score 59.8 vs 59.8)
- `tetu vs coordonne : 0W-10D-0L` (score 58.8 vs 58.8)
- `tetu vs regret : 0W-10D-0L` (score 0.0 vs 0.0 !)
- `expert vs coordonne : 0W-10D-0L`
- `expert vs regret : 0W-10D-0L`
- `coordonne vs regret : 0W-10D-0L`

Le cas le plus frappant c'est `tetu vs regret : score 0.0 vs 0.0`. Zéro point pour les deux équipes sur 50 épisodes, à chaque run. Comment c'est possible ?

L'explication est liée à l'équilibre de Nash : sur yellow-map, la `meilleure_fixe` est `(2, 2, 2, 1, 1)`. Tetu la joue à chaque tour par définition. Regret matching, en accumulant ses regrets, converge aussi vers cette allocation car c'est objectivement la meilleure réponse à elle-même. Les deux finissent par jouer exactement la même chose.

Or sur les fioles jaunes, si les deux équipes envoient le même nombre de joueurs (2 vs 2 ou 1 vs 1), c'est une égalité : personne ne marque. Toutes les fioles sont en égalité à chaque épisode, d'où le score 0-0 systématique.

C'est un résultat théoriquement cohérent : quand deux stratégies convergent vers le même équilibre de Nash, le jeu se stabilise dans un état où aucun des deux ne peut améliorer sa situation unilatéralement. Les scores 59.8 vs 59.8 pour tetu vs expert s'expliquent de la même façon : expert joue aléatoirement parmi les top_allocs qui sont toutes proches de meilleure_fixe, donc les écarts sont minimes et les scores s'équilibrent.

Seules les stratégies adaptatives (fictitious et meta) cassent cet équilibre en trouvant des counters spécifiques grâce à leur capacité d'adaptation en temps réel.

#### Green-map (tout vert)

C'est la carte la plus intéressante théoriquement. Les fioles vertes fonctionnent par majorité : il faut un total ≥ 3 joueurs sur la fiole et la majorité gagne. Cela crée un jeu de type matching pennies où aucune stratégie pure ne domine.

Les résultats le confirment :
- expert vs meta : 5W-2D-3L → expert bat meta
- coordonne vs meta : 7W-1D-2L → coordonné aussi
- regret vs meta : 7W-1D-2L → regret domine meta

Green-map est la carte où meta montre ses limites. Meta classifie expert, coordonné et regret comme "aleatoire" (haute entropie) et joue des top_allocs au hasard. Mais sur une carte où la mécanique de majorité crée un jeu de type matching pennies, la classification n'apporte aucun avantage. Pire, les stratégies adverses (même simples comme expert) arrivent à accumuler plus de victoires grâce à la nature symétrique du jeu.

C'est cohérent avec le théorème du minimax de von Neumann : sur cette carte, la stratégie optimale est mixte (probabiliste). Aucune stratégie déterministe ou adaptative ne peut dominer. Meta, malgré sa complexité, ne fait pas mieux qu'un simple tirage pondéré parmi les meilleures allocations.

#### Blue-map (tout bleu)

La mécanique spy des fioles bleues (1 joueur bat 2+) crée une dynamique unique. Meta y joue son `spread_blue` à chaque tour : 1 joueur (spy) sur chaque fiole, le surplus concentré sur une seule fiole. Par exemple `(8, 3, 1, 1, 1, 1, 1, 1)`.

- Meta 10-0 contre expert, coordonne, regret : ces stratégies jouent depuis les top_allocs sans chercher le counter spécifique au spread. Les spies de meta captent les fioles où l'adversaire concentre 2+ joueurs, et l'adversaire ne parvient pas à exploiter les fioles où meta a son surplus.

- Fictitious 10-0 contre meta : c'est le résultat le plus intéressant. Meta joue toujours le même spread_blue (allocation fixe). Fictitious, avec ses 15 000 allocations et son argmax, trouve le counter optimal en 1 tour : il place 1 spy sur chaque fiole où meta a du surplus (8 et 3), et concentre le reste sur une seule fiole. Résultat par épisode : fictitious gagne 2 fioles (spy sur le surplus de meta), meta gagne 1 fiole (spy sur la concentration de fictitious), 5 fioles à personne. Score : 2-1 par épisode, soit ~100-50 sur 50 épisodes.

#### Le dilemme du surplus sur blue-map

C'est un résultat fondamental de cette carte. Avec 17 joueurs et 8 fioles, chaque équipe doit placer un surplus de 9 joueurs quelque part (17 - 8 = 9 joueurs en plus du minimum de 1 par fiole). Or la mécanique spy fait que tout groupe de 2+ joueurs est vulnérable à un spy adverse.

C'est un vrai dilemme :
- Si on concentre le surplus sur 1 fiole (spread_blue) : on minimise le nombre de fioles vulnérables (2 fioles avec 2+), mais l'adversaire peut cibler précisément ces 2 fioles avec des spies.
- Si on répartit le surplus sur plusieurs fioles : on crée plus de fioles vulnérables, ce qui donne plus de cibles aux spies adverses.

Dans les deux cas, l'adversaire peut exploiter le surplus avec des spies. C'est un jeu qui n'a pas d'équilibre de Nash en stratégie pure : toute allocation fixe a un counter qui la bat. La stratégie optimale serait mixte (varier aléatoirement le placement du surplus), mais ça nécessiterait de sacrifier la stabilité du spread.

Meta fait le choix de jouer spread_blue à chaque tour : c'est la stratégie la plus robuste contre les stratégies simples (0 défaite, que des victoires ou draws), au prix d'une vulnérabilité face à fictitious qui exploite la prédictibilité du spread fixe.

#### Mixed-map (carte mixte)

La carte la plus complexe avec 4 types de fioles (jaune, verte, jaune, rouge, bleue, rouge, jaune, verte, jaune). Meta excelle ici grâce à ses optimisations spécifiques :

- Meta 10-0 contre tetu, coordonne, regret : le classifier détecte tetu comme "fixe" et joue `best_response`. Contre coordonne et regret, le weighted_gains avec decay et l'optimisation `_optimiser_bleues` donnent l'avantage.
- Meta 9-0 contre expert : quasi-parfait grâce au classifier
- Fictitious vs meta : 4W-0D-6L : match serré. Fictitious (argmax déterministe sur 15 000 allocations) est parfois plus précis, mais meta garde un léger avantage grâce à ses optimisations spécifiques sur la fiole bleue de la carte

L'optimisation `_optimiser_bleues` (spy-in) aide meta sur cette carte : quand l'adversaire met régulièrement 2+ joueurs sur la fiole bleue, meta vole un joueur d'une autre fiole pour placer un spy et gagner ce point gratuitement.

### Analyse transversale

#### Pourquoi meta est première

Meta combine trois avantages que les autres stratégies n'ont pas simultanément :
1. Counter immédiat des adversaires fixes (best_response, meilleur que la convergence graduelle de fictitious/regret)
2. Robustesse contre les adversaires aléatoires (diversification via top_allocs)
3. Optimisations spécifiques (spy-in bleue, spread_blue au tour 0)

#### Pourquoi fictitious bat regret

Fictitious utilise les 15 000 allocations avec `argmax` (déterministe). Regret utilise seulement 10 top_allocs avec sampling proportionnel (stochastique). Le ratio taille d'espace × qualité de sélection favorise largement fictitious :
- Fictitious explore tout l'espace et choisit le meilleur
- Regret explore un petit sous-ensemble et ajoute du bruit avec le sampling

La convergence de regret matching nécessite O(√(ln(N)/T)) tours, soit ~15 tours avec N=10 et T=50. C'est suffisant pour converger sur les petites cartes (yellow, red), mais sur les grandes cartes l'espace restreint de 10 allocations limite sa capacité à trouver les bons counters.

#### Convergence et équilibres

Nos résultats illustrent plusieurs concepts de théorie des jeux :

- Équilibre de Nash : sur les cartes simples (yellow, red), fictitious play converge vers l'équilibre. C'est visible par ses victoires 10-0 contre la plupart des adversaires. Les draws systématiques sur yellow-map (score 0-0 entre tetu et regret) sont une manifestation directe de cet équilibre : les deux jouent la même allocation optimale, aucun ne peut améliorer unilatéralement.

- Équilibre corrélé : regret matching converge vers un équilibre corrélé, un concept plus général que Nash. En pratique, avec notre implémentation restreinte à 10 allocations, la convergence est partielle mais suffisante pour battre les stratégies statiques.

- Théorème d'approchabilité de Blackwell : c'est le résultat théorique sous-jacent qui garantit la convergence de regret matching. Il assure que le regret moyen converge vers 0 quand T tend vers l'infini. En pratique avec T=50, la convergence est partielle, ce qui explique les performances moyennes de regret par rapport à fictitious.

- aucune stratégie ne domine toutes les autres sur toutes les cartes. Meta perd contre regret sur green-map. C'est un résultat fondamental : dans un jeu compétitif, toute stratégie a des faiblesses exploitables.

#### Impact du nombre d'épisodes

Le choix de 50 épisodes par match est un compromis. Avec moins d'épisodes (20), les stratégies adaptatives (fictitious, meta) n'ont pas le temps de converger et les stratégies statiques (tetu) deviennent plus compétitives. Avec plus d'épisodes (100+), les stratégies adaptatives dominent encore plus car elles ont le temps de classifier l'adversaire et d'affiner leur réponse. Le seuil de 50 est le point où les stratégies adaptatives commencent à avoir un avantage clair sans rendre le tournoi trop long.
