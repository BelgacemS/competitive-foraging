import numpy as np
import random
import os
from utils import calculer_score, preparer_carte
from strategies import creer_strategie

# On fait un round robin entre toutes les strategies sur toutes les cartes
#
# pas de pygame, pas d'affichage graphique, que du calcul
# on charge les types de fioles directement depuis les JSON des cartes
# on simule les matchs avec juste le scoring (pas de A*, pas de sprites)
# et on affiche/sauvegarde les resultats
#
# pour chaque couple de strategies, sur chaque carte :
#   - on joue nb_episodes episodes par match (avec alternance de priorite)
#   - on repete nb_runs fois pour la significativite statistique
#   - on enregistre victoires / nuls / defaites
#
# a la fin : matrice de win rates par carte, classement global, figures matplotlib


def appliquer_contrainte_physique(alloc, max_par_fiole=8):
    # simule la contrainte du vrai jeu : max 8 joueurs par fiole
    # le surplus est redistribue sur les fioles les moins chargees
    alloc = list(alloc)
    surplus = 0
    for i in range(len(alloc)):
        if alloc[i] > max_par_fiole:
            surplus += alloc[i] - max_par_fiole
            alloc[i] = max_par_fiole

    # redistribuer le surplus sur les fioles qui ont de la place
    while surplus > 0:
        min_idx = min(range(len(alloc)), key=lambda i: alloc[i])
        ajout = min(surplus, max_par_fiole - alloc[min_idx])
        if ajout <= 0:
            break
        alloc[min_idx] += ajout
        surplus -= ajout

    return tuple(alloc)


def simuler_match(strat0, strat1, types_fioles, nb_episodes=50):
    # simule un match complet entre deux strategies sans affichage sans A*
    # pas de pygame pas de sprites, juste des calculs de score
    # retourne le score final [pts_team0, pts_team1]

    score = [0, 0]
    hist0, hist1 = [], []

    for e in range(nb_episodes):
        # alternance de priorite comme dans main.py
        prio = e % 2

        # chaque strategie choisit son allocation
        alloc0 = appliquer_contrainte_physique(strat0.choisir(hist0, 0))
        alloc1 = appliquer_contrainte_physique(strat1.choisir(hist1, 1))

        # calculer les points de cet episode
        pts0, pts1 = calculer_score(alloc0, alloc1, types_fioles, priorite=prio)
        score[0] += pts0
        score[1] += pts1

        # mettre a jour les historiques
        hist0.append((alloc0, alloc1, (pts0, pts1)))
        hist1.append((alloc1, alloc0, (pts1, pts0)))

    return score


def round_robin(cartes_data, noms_strats, nb_episodes=50, nb_runs=10):
    # fait jouer chaque couple de strategies sur chaque carte

    resultats = {}

    total = len(cartes_data) * len(noms_strats) * (len(noms_strats) - 1) // 2 * nb_runs
    num = 0

    for carte_data in cartes_data:

        nom_carte = carte_data['nom']
        types = carte_data['types']
        resultats[nom_carte] = {}

        for i, nom_a in enumerate(noms_strats):
            for j, nom_b in enumerate(noms_strats):
                if j <= i:
                    continue

                cle = f"{nom_a} vs {nom_b}"
                wins_a, wins_b, nuls = 0, 0, 0
                scores_a, scores_b = [], []

                for r in range(nb_runs):
                    num += 1
                    # creer des instances reset a chaque run
                    sa = creer_strategie(nom_a, types, carte_data)
                    sb = creer_strategie(nom_b, types, carte_data)

                    score_a, score_b = simuler_match(sa, sb, types, nb_episodes)
                    scores_a.append(score_a)
                    scores_b.append(score_b)

                    if score_a > score_b: wins_a += 1
                    elif score_b > score_a: wins_b += 1
                    else: nuls += 1

                    if num % 50 == 0:
                        print(f"  Match {num}/{total}...")

                resultats[nom_carte][cle] = {
                    'wins_a': wins_a, 'wins_b': wins_b, 'nuls': nuls,
                    'score_moyen_a': np.mean(scores_a),
                    'score_moyen_b': np.mean(scores_b),
                    'std_a': np.std(scores_a),
                    'std_b': np.std(scores_b),
                }
                print(f"  {nom_carte} | {cle} : {wins_a}W-{nuls}D-{wins_b}L")

    return resultats


def classement_global(resultats, noms_strats):
    # compte les victoires de chaque strategie sur toutes les cartes

    points = {s: 0 for s in noms_strats}

    for carte, matchs in resultats.items():
        for cle, res in matchs.items():
            nom_a, nom_b = cle.split(" vs ")
            points[nom_a] += res['wins_a']
            points[nom_b] += res['wins_b']

    return sorted(points.items(), key=lambda x: -x[1])

def afficher_resultats(resultats, noms_strats):
    print("\n" + "=" * 60)
    print("RESULTATS DU TOURNOI")
    print("=" * 60)

    for carte, matchs in resultats.items():
        print(f"\n--- {carte} ---")
        for cle, res in matchs.items():
            print(f"  {cle} : {res['wins_a']}W-{res['nuls']}D-{res['wins_b']}L "
                  f"(score: {res['score_moyen_a']:.1f}+-{res['std_a']:.1f} vs "
                  f"{res['score_moyen_b']:.1f}+-{res['std_b']:.1f})")

    classement = classement_global(resultats, noms_strats)
    print(f"\n--- Classement global ---")
    for i, (nom, pts) in enumerate(classement):
        print(f"  {i + 1}. {nom} : {pts} victoires")


def generer_figures(resultats, noms_strats):
    # genere les figures matplotlib dans docs/figures/
    # heatmaps de win rates par carte + barplot du classement global
    try:
        import matplotlib
        matplotlib.use('Agg') 
        import matplotlib.pyplot as plt
    except ImportError:
        print("erreur pour l'import")
        return

    fig_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'figures')
    os.makedirs(fig_dir, exist_ok=True)

    # heatmap des win rates pour chaque carte
    for carte, matchs in resultats.items():
        n = len(noms_strats)
        mat = np.full((n, n), 0.5)  # diagonale = 0.5 (contre soi-meme)

        for cle, res in matchs.items():
            nom_a, nom_b = cle.split(" vs ")
            i, j = noms_strats.index(nom_a), noms_strats.index(nom_b)
            total = res['wins_a'] + res['wins_b'] + res['nuls']
            if total > 0:
                mat[i][j] = (res['wins_a'] + 0.5 * res['nuls']) / total
                mat[j][i] = (res['wins_b'] + 0.5 * res['nuls']) / total

        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.imshow(mat, cmap='RdYlGn', vmin=0, vmax=1)
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(noms_strats, rotation=45, ha='right')
        ax.set_yticklabels(noms_strats)

        # afficher les valeurs dans les cases
        for ii in range(n):
            for jj in range(n):
                ax.text(jj, ii, f'{mat[ii][jj]:.2f}', ha='center', va='center', fontsize=9)
        plt.colorbar(im)
        plt.title(f'Win rates (ligne vs colonne) - {carte}')
        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, f'heatmap_{carte}.png'), dpi=150)
        plt.close()
        print(f"  Figure sauvegardée: heatmap_{carte}.png")

    # barplot du classement global
    classement = classement_global(resultats, noms_strats)
    noms = [c[0] for c in classement]
    pts = [c[1] for c in classement]

    plt.figure(figsize=(10, 5))
    bars = plt.bar(range(len(noms)), pts, color='steelblue')

    # mettre en surbrillance le premier
    if bars:
        bars[0].set_color('gold')
    plt.xticks(range(len(noms)), noms, rotation=45, ha='right')
    plt.ylabel('Victoires totales')
    plt.title('Classement global des strategies')
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, 'classement.png'), dpi=150)
    plt.close()
    print(f"Figure sauvegardée: classement.png")

if __name__ == "__main__":
    print("=" * 60)
    print("TOURNOI DE FORAGING COMPETITIF")
    print("=" * 60)

    # on prepare les donnees de chaque carte
    cartes = ["yellow-map", "red-map", "green-map", "blue-map", "mixed-map"]
    cartes_data = []
    for c in cartes:
        cartes_data.append(preparer_carte(c))

    # lance le round-robin
    noms = ["aleatoire", "tetu", "expert", "coordonne", "fictitious", "regret", "meta"]
    print(f"\nStrategies: {noms}")
    print(f"Cartes: {cartes}")
    print(f"Lancement du round-robin\n")

    res = round_robin(cartes_data, noms, nb_episodes=50, nb_runs=10)

    # affiche les resultats
    afficher_resultats(res, noms)

    # genere les figures
    print("\nGeneration des figures")
    generer_figures(res, noms)

    print("\nTournoi terminé")
