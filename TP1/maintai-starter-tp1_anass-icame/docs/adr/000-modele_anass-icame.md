# ADR 000 : Choix de l'architecture du modèle de prédiction de défaillance (Régression Logistique et seuillage à 0,3)

Date : 26/10/2026 · Auteur : anass icame

## Contexte
Dans le cadre de la maintenance prédictive industrielle MaintAI, le système doit anticiper les pannes d'équipements critiques à partir des flux de 4 capteurs télémétriques (température, vitesse de vibration, taux de charge et heures cumulées de fonctionnement). 
Dans l'environnement de production, les arrêts inopinés engendrent des pertes financières et matérielles majeures, tandis que les incidents réels restent rares (environ 13,6 % des observations). Le coût d'un faux négatif (panne non détectée menant au bris de machine) est incomparablement plus élevé que celui d'un faux positif (contrôle préventif superflu). Par ailleurs, le modèle doit être intégré dans un service d'inférence HTTP léger à haute disponibilité et fournir des résultats transparents et interprétables pour les techniciens de maintenance.

## Options étudiées
1. **Classifieur Naïf / Baseline majoritaire (`DummyClassifier`)** :
   - *Avantages* : Complexité algorithmique nulle, implémentation triviale, score d'exactitude (accuracy) flatteur (86,4 %) dû au déséquilibre des classes.
   - *Inconvénients* : Ne détecte strictement aucune défaillance (rappel = 0,0), ce qui le rend totalement inopérant et dangereux sur le plan industriel.
2. **Régression Logistique standardisée (`Pipeline` avec `StandardScaler`)** :
   - *Avantages* : Modèle linéaire rapide à entraîner, empreinte mémoire minimale, désérialisation quasi instantanée au démarrage de l'API. Fournit une estimation continue de la probabilité d'incident et des coefficients directement interprétables physiquement pour expliquer l'impact de chaque capteur.
   - *Inconvénients* : Hypothèse de séparabilité linéaire ; incapacité intrinsèque à capturer des interactions complexes d'ordre supérieur sans ingénierie de variables dédiée.
3. **Modèles ensemblistes non-linéaires (Forêt Aléatoire, Gradient Boosting)** :
   - *Avantages* : Modélisation des relations non linéaires et des effets de couplage entre capteurs sans mise à l'échelle préalable.
   - *Inconvénients* : Empreinte disque et mémoire plus lourde, temps d'inférence et de chargement plus long au démarrage de l'API, risque accru de surapprentissage sur de petits volumes, et perte d'explicabilité immédiate des coefficients.

## Décision
Nous retenons la **Régression Logistique précédée d'un `StandardScaler`**, packagée dans un unique `Pipeline` Scikit-Learn sérialisé avec `joblib`, associée à un **seuil d'alerte opérationnel abaissé à 0,3** (au lieu du seuil conventionnel de 0,5).

Ce choix découle directement de la contrainte métier industrielle :
- Maximiser le **rappel** (sensibilité) pour capturer un maximum de défaillances réelles.
- Sur notre jeu d'évaluation indépendant (1 000 relevés), ce paramétrage permet d'atteindre un rappel de **0,750** et une exactitude globale de **0,904** (avec une précision de 0,622), surpassant largement la baseline incapable d'émettre la moindre alerte.

## Conséquences
- **Ce que cette décision facilite** :
  - Démarrage ultra-rapide de l'API FastAPI et faible latence d'inférence sous Uvicorn.
  - Le pipeline scellé garantit l'application stricte et ordonnée du centrage-réduction des données sans fuite ni désynchronisation.
  - Le seuil de déclenchement d'alerte est configuré via une variable d'environnement (`MAINTAI_THRESHOLD`), permettant d'ajuster la politique de sensibilité de l'atelier sans réentraînement du modèle.
- **Ce qu'elle rend plus difficile** :
  - Avec une précision de 62,2 %, environ 38 % des alertes générées correspondent à de fausses alertes nécessitant un contrôle sans qu'une panne ne survienne immédiatement.
- **Ce qu'il faudra surveiller** :
  - Dérive des données (data drift) lors du passage des données de simulation aux signaux de capteurs réels d'usine.
  - Évolution conjointe du rappel et de la précision au cours du cycle de vie du modèle.
  - Stabilité de l'environnement d'exécution (version de scikit-learn documentée dans `model_info.json`).
