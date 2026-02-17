# competitive level-based foraging 
Template et instructions pour le projet 2026 IA et Jeux

## Présentation générale du projet

On propose dans ce projet d'implémenter un jeu stratégique reprenant certaines des notions vues en cours. 

### Phase de jeu principale
Chaque jour, deux équipes de plusieurs joueurs disposés sur une carte effectuent un choix sur des ressources à aller collecter. 
Chaque **ressource** disposée sur le terrain possède un nombre minimal nécessaire pour la collecter, selon son type.  
Chaque joueur choisit une fiole selon des stratégies que vous devrez définir. Les joueurs doivent être disposés autour des fioles, **sur des cases différentes**. Il y a donc au maximum 8 joueurs autour d'une fiole.   



* les fioles **jaunes** nécessitent seulement un joueur de la même équipe pour être collectées. Si les deux équipes remplissent la condition, l'équipe avec le plus de joueurs autour de la fiole collecte la fiole.  
* les fioles **rouges** nécessitent au moins 2 joueurs de la même équipe pour être collectées. Si les deux équipes remplissent la même condition, l'équipe avec le plus de joueurs 
* les fioles **vertes** nécessitent au moins 3 joueurs **au total** pour être collectées. Si la condition est vérifiée, l'équipe avec le plus de joueurs collecte la fiole. 
* les fioles **bleues** se comportent comme les fioles rouges, mais si un joueur d'une équipe est seul alors que l'autre équipe remplit la condition, l'équipe du joeur seul remporte la fiole. 

Dans tous les cas précédents, s'l y a égalité après vérification des conditions, la fiole n'est pas collectée.   

### Exemples
On suppose deux équipes T1 et T2. 
* Autour d'une fiole jaune, 1 joueur T1 et 2 joueurs T2 : l'équipe T2 remporte la fiole. 
* Autour d'une fiole rouge, 1 joueur T1. Personne ne remporte la fiole. 
* Autour d'une fiole rouge, 2 joueurs T1 et 3 joueurs T2 : T2 remporte la fiole. 
* Autour d'une fiole verte, 2 joueurs T1 : personne ne remporte la fiole. 
* Autour d'une fiole verte, 2 joueurs T1 et 1 joeur T2 : T1 remporte la fiole. 
* Autour d'une fiole verte, 2 joueurs T1 et 2 joueurs T2 : personne ne remporte la fiole. 
* Autour d'une fiole bleue: 1 joueur T1 et 2 joueurs T2 : T1 remporte la fiole. 
* Autour d'une fiole bleue: 2 joueur T1 et 3 joueurs T2: T2 remporte la fiole  






### Déroulement d'une partie 

Un épisode (jour) du jeu se déroule de la manière suivante: 
* les équipes décident de l'allocation de leurs joueurs, selon une stratégie donnée. 
* dans le cas où l'allocation visée n'est pas possible (par exemple si T1 décide d'allouer 5 joeurs à la fiole 1 alors qu'il y a déjà 4 joueurs autour), le joueur ne sera pas compté. 
* lorsque les joueurs ont atteint les fioles visées, l'arbitre compte les points, c'est-à-dire le nombre de fioles remportées par chaque équipe



Chaque équipe dispose d'une stratégie (qui peut être stochastique) mais qui reste fixe pour l'ensemble de la partie.  
Une partie se déroule en un nombre fixe de journées. Les scores des joueurs sont les scores cumulés au cours des journées. 



### Hypothèses importantes 
* les décisions des deux équipes sont réalisées **de manière simultanée** (même si à l'affichage une équipe se déplace après l'autre). 
* Les joueurs ont une **observabilité totale de l'environnement** 
* Les joueurs ont une mémoire parfaite des évènements, c'est-à-dire qu'ils connaissent l'historique des journées précédentes.  '
* Les déplacements des joueurs ne sont pas contraints par les autres joueurs (pas de collision), par contre les joueurs doivent être positionnées autour des fioles sur des cases libres




## Modules disponibles

### Module pySpriteWorld

Pour la partie graphique, vous utiliserez le module `pySpriteWorld` (développé par Yann Chevaleyre) qui s'appuie sur `pygame` et permet de manipuler simplement des personnages (sprites), cartes, et autres objets à l'écran.

Cinq cartes par défaut vous sont proposées pour ce projet  (`yellow-map`, `red-map`, `green-map`, `blue-map`, `mixed-map`): elles comportent 2 équipes de 8 joueurs et 5 fioles au centre de la carte.   

La gestion de la carte s'opère grâce à des calques:
* un calque `background`, qui contient le fond de la carte
* un calque `joueur`, où seront présents les joueurs
* un calque `ramassable`, qui contiendra les fioles


Les joueurs et les ramassables sont des objets Python sur lesquels vous pouvez effectuer des opérations classiques.
Par exemple, il est possible récupérer leurs coordonnées sur la carte avec `o.get_rowcol(x,y)` ou à l'inverse fixer leurs coordonnées avec `o.set_rowcol(x,y)`.
La mise à jour sur l'affichage est effective lorsque `mainiteration()` est appelé.


Notez que vous pourrez ensuite éditer vos propres cartes à l'aide de l'éditeur [Tiled](https://www.mapeditor.org/), et exporter ces cartes au format `.json`. 

Il est ensuite possible de changer la carte utilisée en modifiant le nom de la carte utilisée dans la fonction `init` du `main`:
`name = _boardname if _boardname is not None else 'yellow-map'``

La vitesse d'affichage peut être modifiée avec le paramètre `game.fps`

:warning: Vous n'avez pas à modifier le code de `pySpriteWorld`

### Module search

Le module `search` qui accompagne le cours est également disponible. Il permet en particulier de créer des problèmes de type grille et donc d'appeler directement certains algorithmes de recherche à base d'heuristiques vus en cours, comme A:star: pour la recherche de chemin.

## Travail demandé

### Semaine 1
**Prise en main**. A l'éxécution du fichier `main.py`, vous devez observer le comportement suivant: chaque joueur de l'équipe 0 choisit au hasard une fiole et une position libre autour de cette fiole, puis se déplace vers cette position. Puis les joueurs de l'équipe 1 font de même. 
Lorsque tous les joueurs se sont déplacés, un affichage du nombre de joueurs de chaque équipe autour de chaque fiole est réalisé. 
Vous devrez bien comprendre le code, implémenter le décompte des points; puis répéter le jeu un nombre fixe d'épisodes, et afficher l'équipe gagnante au final. 
Afin de préserver l'équité, l'ordre de priorité devrait être inversé chaque joueur. 

### Semaine 2 et 3
**Mise en place et test de différentes stratégies**. Il est possible de définir pour ce jeu : 
* des stratégies **stationnaires**: tétu (toujours jouer la même distribution), aléatoire uniforme (chaque joueur choisit de manière uniforme parmi les fioles), aléatoire expert (choisir une distribution parmi un ensemble de distributions prédéfinies), aléatoire avec coordination (pour favoriser les chances de choisir la même fiole), etc. 
* des stratégies **basées sur l'historique**, qui s'appuient sur les expériences des tours précédents: par exemple **fictitious play**, **regret-matching**

Il est évidemment possible de combiner ces différents pour obtenir des stratégies encore plus complexes. 

### Semaine 4
**Soutenances**. Celles-ci ont lieu en binôme. Vous présenterez les principaux résultats de votre projet. 
Il est attendu que vous compariez **au moins 5 stratégies**. 
Chaque couple de stratégie devra être comparé, sur l'ensemble des cartes disponibles (et plus si vous le souhaitez). 
Le rapport doit être rédigé en markdown dans le fichier prévu à cet effet dans le répertoire `docs` (voir le template `rapport.md`).

