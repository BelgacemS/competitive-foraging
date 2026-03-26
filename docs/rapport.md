# Rapport de projet

## Groupe

* Belgacem Smaali
* Khaled Bouhabel


## Description des choix importants d'implémentation

### Architecture

On a découpé le code en trois fichiers :
- `utils.py` pour les fonctions de base (scoring, allocations, analyse)
- `strategies.py` pour les 7 stratégies
- `tournoi.py` pour le round-robin automatique

On s'est vite rendu compte qu'il fallait un moyen de tester les stratégies sans lancer pygame a chaque fois. Du coup on a codé un tournoi qui simule les matchs directement avec la fonction de scoring sans passer par le A* et les sprites. Ca nous permet de lancer 1050 matchs en environ 40 min ce qui aurait pris des heures avec l'affichage.

### Fonctions principales de `utils.py`

**`generer_allocations(nb_joueurs, nb_fioles, max_allocs=15000)`** : génère toutes les répartitions possibles de joueurs sur les fioles. Par exemple avec 8 joueurs et 5 fioles, `(3, 2, 1, 1, 1)` veut dire 3 joueurs sur la fiole 0, 2 sur la 1, etc. On utilise l'algorithme étoiles et barres, ca donne C(n+k-1, k-1) allocations. Sur les petites cartes (8 joueurs, 5 fioles) y a 495 allocations, c'est correct. Mais sur les grandes (17 joueurs, 8 fioles) ca monte a 346 104 et la c'est trop lent. Du coup on genere tout et on sample 15 000 avec `random.sample`. Au debut on tronquait la récursion a 15 000 mais ca créait un biais : les premieres fioles avaient toujours 0 joueurs parce que la récursion explore dans l'ordre (0, 0, ..., n). Le random sample règle ce problème.

**`score_fiole(type_fiole, nb_j0, nb_j1)`** : détermine qui gagne une fiole selon son type et le nombre de joueurs de chaque équipe. Jaune = seuil 1 puis majorité, rouge = seuil 2 puis majorité, verte = total >= 3 puis majorité, bleue = mécanique spy (1 seul joueur bat un groupe de 2+) sinon seuil 2 puis majorité.

**`calculer_score(alloc0, alloc1, types_fioles, priorite=0)`** : calcule le score total d'un épisode en appelant `score_fiole` sur chaque fiole. Gère aussi le cas ou les deux équipes mettent plus de 8 joueurs combinés sur une fiole (l'équipe prioritaire se place en premier, l'autre prend les places restantes, la priorité alterne a chaque épisode).

**`analyser_allocations(types_fioles, allocations, k=10, nb_sample=1000)`** : pour trouver les meilleures allocations, on teste chacune contre 1000 adversaires aléatoires et on garde les 10 qui gagnent le plus (top_allocs) + la meilleure (meilleure_fixe). C'est calculé une seule fois par carte au début.

**`best_response(types_fioles, alloc_adv, allocations)`** : teste les 15 000 allocations contre un coup adverse donné et retourne la meilleure. Utilisé par meta quand elle détecte un adversaire fixe.

**`preparer_carte(nom_carte)`** : charge la carte (types de fioles, nombre de joueurs depuis le JSON), génère les allocations, lance l'analyse. Retourne un dico avec tout ce qu'il faut.

### Contrainte physique

Chaque fiole a 8 cases autour donc max 8 joueurs dessus. Dans le tournoi, `appliquer_contrainte_physique` cap a 8 et redistribue le surplus sur les fioles les moins chargées. `calculer_score` gère aussi le cas ou les deux équipes combinées dépassent 8 sur une fiole (priorité alternée).

### Pourquoi 50 épisodes

On joue 50 épisodes par match, 10 runs par matchup. C'est un compromis : avec 7 strats, 5 cartes et 10 runs ca fait 1050 matchs. Chaque match itère sur 15 000 allocations pour les strats adaptatives du coup le total tourne autour de 40 min. On aurait aimé plus d'épisodes (meilleure convergence par exemple pour regret matching) mais le temps de calcul explosait.

## Description des stratégies proposées

On a 7 stratégies qui héritent toutes de `Strategie`. L'interface est simple : `choisir(historique, mon_equipe)` retourne une allocation.

### 1. Aléatoire Uniforme

La baseline. Elle tire au hasard parmi les 15 000 allocations. Sans surprise elle perd contre tout le monde vu que la proba de tomber sur une bonne allocation est d'environ 0.07%. Ca sert juste de référence : si une stratégie fait pas mieux que ca, "elle sert a rien".

A chaque tour : `random.choice(self.allocations)`, c'est tout.

### 2. Têtu

Joue toujours la meme allocation, la `meilleure_fixe` calculée par `analyser_allocations`. C'est la meilleure contre un adversaire aléatoire, mais c'est prédictible : un adversaire adaptatif la counter en un tour.

A l'init il récupère `meilleure_fixe` depuis les données de la carte. Après il retourne ca a chaque tour, aucun calcul pendant le jeu.

### 3. Aléatoire Expert

Tire au hasard parmi les 10 meilleures allocations (top_allocs) au lieu des 15 000. Mieux que l'aléatoire pur car les options sont filtrées mais toujours pas adaptatif.

A chaque tour : `random.choice(self.top_allocs)`.

### 4. Aléatoire Coordonné

Comme expert mais avec des poids : les allocations concentrées sont jouées plus souvent. On pondère par `max(alloc)` donc une allocation comme`(5, 3, 0, 0, 0)` (max=5) est tirée plus souvent que `(2, 2, 2, 1, 1)` (max=2). L'idée c'est que concentrer ses joueurs aide a dépasser les seuils (rouge, verte).

A noter : sur yellow-map ou les top_allocs sont toutes des permutations de `(2, 2, 2, 1, 1)`, le max est 2 pour toutes donc la pondération change rien. Ca fait une vraie différence que sur les cartes avec des top_allocs variées (green, mixed).

### 5. Fictitious Play

C'est la ou ca devient intéressant. Fictitious play est un algorithme classique de théorie des jeux : on joue la meilleure réponse a ce que l'adversaire a joué en moyenne. La littérature a montré que ca converge vers un équilibre de Nash dans les jeux a 2 joueurs somme nulle.

Concrètement, pour chaque allocation possible on accumule le gain qu'elle aurait donné contre chaque coup adverse passé (`gains[i] += p0 - p1`). Puis on joue celle avec le plus gros gain cumulé (`argmax`). C'est la strategie qui fait le plus d'appels a `calculer_score` par tour (15 000 appels). Au tour 0, pas d'historique donc on joue `meilleure_fixe`.

Le point important c'est que fictitious est déterministe : il prend toujours le meilleur (argmax). Pas de hasard dans le choix. Ca le rend précis mais aussi prédictible une fois convergé.

### 6. Regret Matching

Le principe : on joue proportionnellement aux regrets positifs. Le regret d'une action c'est "combien j'aurais gagné de plus si j'avais joué ca au lieu de ce que j'ai réellement fait". On accumule ces regrets, on garde les positifs, on normalise en probas et on sample.

On a restreint l'espace d'actions aux 10 top_allocs au lieu des 15 000. On a testé avec plus (20, 50) mais ca rendait le sampling trop dilué. La borne de convergence est O(sqrt(ln(N)/T)) : avec N=15 000 et T=50 le regret moyen est environ 0.44 (ca converge pas), avec N=10 c'est ~0.21 (ca commence a converger). C'est un compromis entre exploration et convergence.

La grosse différence avec fictitious : fictitious itère sur 15 000 et prend le meilleur (déterministe), regret itère sur 10 et tire au dé (stohcastique).

Si tous les regrets sont négatifs (on a joué le mieux possible), on fallback sur `meilleure_fixe`.

### 7. Méta Stratégie

C'est notre stratégie principale, celle qu'on a passé le plus de temps a développer. L'idée de base : au lieu de choisir un seul algorithme, on classifie l'adversaire et on adapte la réponse.

**Classifieur d'adversaire** : après 5 observations, on calcule l'entropie de Shannon des derniers coups adverses. Entropie basse (strict inférieure à 0.3) = adversaire fixe (comme têtu), entropie haute (strictement superierieur à 0.7) = aléatoire (comme expert), entre les deux = adaptatif (comme fictitious).

**Réponses** :
- Fixe : `best_response`, on teste les 15 000 allocs contre son dernier coup et on prend la meilleure. C'est le counter parfait.
- Aléatoire : on joue au hasard parmi les top_allocs. Contre un adversaire imprévisible, diversifier c'est la meilleure défense.
- Adaptatif : `argmax(weighted_gains)`, comme fictitious play mais avec un decay de 0.85. Le decay oublie les vieilles observations pour réagir plus vite quand l'adversaire change.

On reclassifie tous les 5 tours au cas ou l'adversaire change de comportement.

**Epsilon-greedy** : 5% du temps on joue un top_alloc au hasard pour pas etre trop prédictible.

**Blue-map** : sur les cartes tout bleu, meta joue un `spread_blue` fixe a chaque tour. C'est 1 spy par fiole + le surplus concentré sur une fiole (cappé a 8 max ici). C'est la strategies la plus robuste contre les strategies simples (jamais de défaite), meme si fictitious arrive a la counter (voir la section blue-map plus bas).

**Optimisation bleues sur cartes mixtes** : `_optimiser_bleues` fait du spy-in (si l'adversaire met toujours 2+ sur une bleue ou on a 0, on vole un joueur d'ailleurs pour placer un spy) et de la réduction (si on a 2+ sur une bleue, on réduit a 1 et on redistribue le surplus).

Chemin d'appel en gros :
1. Tour 0 : spread_blue sur blue-map sinon random top_alloc
2. Tour t > 0 : update les weighted_gains (avec decay) pour les 15 000 allocs puis si carte all-blue retourne spread_blue direct sinon classifie et joue en conséquence puis optimise les bleues sur cartes mixtes

## Description des résultats

### Protocole

Round-robin : chaque paire de stratégies joue sur chaque carte, 10 runs de 50 épisodes. Le classement compte les victoires (un draw = 0 pour les deux).

Cartes :
- yellow-map : 5 jaunes, 8 joueurs (495 allocs)
- red-map : 5 rouges, 8 joueurs (495 allocs)
- green-map : 8 vertes, 17 joueurs (15 000 allocs)
- blue-map : 8 bleues, 17 joueurs (15 000 allocs)
- mixed-map : 9 mixtes, 17 joueurs (15 000 allocs)

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

Meta finit première avec 255 victoires, 15 devant fictitious. On voit clairement trois paliers : les adaptatives (meta, fictitious, regret) au dessus des statiques (coordonne, expert, tetu), elles-memes au dessus de l'aléatoire.

### Yellow-map et Red-map

Les petites cartes avec 495 allocations (pas d'échantillonnage). Résultats nets : meta 10-0 contre tout le monde sur yellow, quasi-parfait sur red. Fictitious est second.

**Les draws sur yellow-map** : c'est le résultat le plus surprenant du tournoi. Les strats statiques font toutes des draws entre elles :

- `tetu vs regret : 0W-10D-0L` avec un score de 0.0 vs 0.0
- `tetu vs expert : 0W-10D-0L` 
- `expert vs coordonne : 0W-10D-0L`
- ect...

Le cas tetu vs regret est le plus frappant : zéro point pour les deux sur 50 épisodes, a chaque run. En fait, sur yellow-map, `meilleure_fixe` = `(2, 2, 2, 1, 1)`. Tetu la joue par définition. Regret converge vers la meme parce que c'est la meilleure réponse a elle-meme. Les deux jouent pareil et sur des fioles jaunes, meme nombre de joueurs = égalité = personne marque. D'ou le 0-0.

C'est un équilibre de Nash : les deux jouent la meme allocation optimale, aucun peut améliorer unilatéralement. Seules les strats adaptatives (fictitious, meta) cassent ca en trouvant des counters.

 Pour tetu vs expert s'expliquent pareil : expert joue des permutations de (2,2,2,1,1) qui sont toutes dans les top_allocs. Chaque permutation gagne autant de fioles qu'elle en perd par rapport a tetu, du coup ca s'équilibre.

### Green-map

La carte la plus intéressante théoriquement. Les vertes marchent par majorité (total >= 3, celui qui en a le plus gagne). Ca crée un jeu type matching pennies (ce que gagne un joueur est perdu par l'autre) ou aucune stratégie pure domine.

Et ca se voit dans les résultats :
- expert vs meta : 5W-2D-3L, expert gagne
- coordonne vs meta : 7W-1D-2L
- regret vs meta : 7W-1D-2L

Meta perd ici parce qu'elle classifie tout le monde comme "aleatoire" et joue des top_allocs au hasard. Mais le classifieur n'apporte rien sur cette carte : c'est un vrai jeu de matching pennies ou la stratégie optimale est mixte. Coordonné fait mieux parce que sa pondération par max favorise les allocations concentrées ce qui marche bien avec la mécanique de majorité. Regret apprend via ses regrets et adapte ses poids ce que meta ne fait pas en mode "aleatoire".

Fait intéressant : fictitious perd aussi contre expert (6-3) et coordonne (5-4) sur green. Parce que fictitious converge vers une allocation fixe (argmax = déterministe) et sur un matching pennies, jouer fixe c'est se faire exploiter. Il "chasse le bruit" de l'adversaire au lieu de jouer l'optimum global.

### Blue-map

La carte avec la mécanique spy (1 joueur seul bat un groupe de 2+). Meta joue son `spread_blue` a chaque tour : 1 spy sur chaque fiole + le surplus concentré. Genre `(8, 3, 1, 1, 1, 1, 1, 1)`.

Résultats :
- Meta 10-0 contre tetu, expert, coordonne et regret (les spies captent les fioles ou l'adversaire concentre ses joueurs)
- Fictitious 10-0 contre meta : le résultat le plus intéressant du tournoi

Fictitious trouve le counter au spread_blue en un tour : il met 1 spy sur les fioles ou meta a 8 et 3 (il gagne 2 fioles) et concentre le reste sur une seule fiole (meta gagne 1 avec son spy). Score par épisode : 2-1 pour fictitious soit environ 100-50 sur 50 épisodes.

Le dilemme du surplus : avec 17 joueurs et 8 fioles, y a 9 joueurs en surplus (17 - 8). Ce surplus doit aller quelque part et ou qu'on le mette il est vulnérable aux spies adverses. Si on concentre (spread_blue) on minimise les cibles mais l'adversaire peut les cibler précisément. Si on répartit on crée plus de cibles. C'est un jeu qui a pas d'équilibre de Nash en stratégie pure : toute allocation fixe a un counter. Meta choisit le spread parce que c'est la plus robuste (jamais de défaite contre les strats simples) meme si fictitious la counter.

### Mixed-map

La carte la plus complexe (jaune, verte, jaune, rouge, bleue, rouge, jaune, verte, jaune). Meta excelle ici :

- 10-0 contre tetu, coordonne, regret
- 9-0 contre expert
- Fictitious vs meta : 4W-0D-6L, match serré

C'est la carte ou l'optimisation `_optimiser_bleues` aide le plus : quand l'adversaire met 2+ sur la fiole bleue, meta vole un joueur pour placer un spy et gagne la fiole gratuitement.

### Pourquoi meta gagne le tournoi

En gros meta combine trois trucs que les autres ont pas en meme temps :
1. Counter immédiat des fixes via best_response (mieux que la convergence lente de fictitious/regret)
2. Diversification contre les aléatoires (random top_allocs)
3. Les optim spécifiques (spy-in, spread_blue)

### Pourquoi fictitious bat regret

Fictitious cherche dans les 15 000 allocations et prend le meilleur. Regret cherche dans 10 et chosit. La précision de fictitious l'emporte largement : il trouve toujours le bon counter, regret le rate souvent a cause du sampling.

### Convergence et théorie des jeux

Nos résultats illustrent pas mal de concepts vus en cours :

**Equilibre de Nash** : les draws a 0-0 sur yellow-map c'est littéralement un équilibre de Nash. Les deux jouent la meme allocation optimale aucun peut améliorer unilatéralement. On avait vu que fictitious play converge vers cet équilibre et c'est ce qu'on observe.

**Equilibre corrélé** : regret matching converge vers un équilibre corrélé, plus général que Nash. Avec nos 10 allocations et 50 tours, la convergence est partielle mais suffisante pour battre les strats statiques.

**Théorème d'approchabilité de Blackwell** : c'est la garantie théorique derrière regret matching. Le regret moyen tend vers 0 quand T grandit. En pratique avec T=50 c'est pas complètement convergé (regret moyen environ 0.21) ce qui explique que regret fait moins bien que fictitious.

**Pas de stratégie universelle** : meta perd sur green-map, se fait counter par fictitious sur blue-map. Aucune strat domine partout. C'est cohérent avec la théorie : dans un jeu compétitif toute stratégie a des faiblesses.

### Choix et impact du nombre d'épisodes

Avec 20 épisodes les adaptatives (fictitious, meta) ont pas le temps de converger et les statiques (tetu) sont plus compétitives. Avec 100+ les adaptatives dominent encore plus. 50 c'est le point ou elles commencent a avoir un vrai avantage sans que le tournoi prenne trop longtemps.
