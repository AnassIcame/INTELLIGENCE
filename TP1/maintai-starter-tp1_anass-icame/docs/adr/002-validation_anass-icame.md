# ADR 002 : Validation des relevés de capteurs et stratégie de disponibilité du modèle MaintAI

Date : 26/10/2026 · Auteur : anass icame

## Contexte
L'API MaintAI expose un service de prédiction de panne destiné à être interrogé en continu par divers systèmes industriels (automates programmables, tableaux de bord de supervision, applications d'atelier). Deux enjeux majeurs d'architecture logicielle se posent :
1. **Intégrité et validité des données entrantes** : Comment garantir que les valeurs reçues sur l'endpoint `/v1/predict` sont conformes à la réalité physique des machines, et éviter que des valeurs aberrantes ou corrompues ne polluent l'inférence du modèle ?
2. **Gestion du cycle de vie et résilience au démarrage** : Quelle stratégie adopter lorsque le fichier de modèle sérialisé (`models/model.joblib`) est absent au lancement du serveur web ?

---

## Décision 1 : Définition de bornes physiques réalistes via Pydantic

### Options étudiées
1. **Validation basée sur les extrêmes empiriques du jeu de données (`min` et `max` de `sensors.csv`)** :
   - *Inconvénients* : Approche fragile et trop restrictive. Un échantillon de données d'entraînement ne couvre jamais l'ensemble des conditions réelles d'exploitation. Une machine industrielle en conditions climatiques inhabituelles ou en surrégime transitoire se verrait indûment rejetée par l'API (faux négatif de communication).
2. **Absence totale de validation numérique (validation de type uniquement)** :
   - *Inconvénients* : Le modèle recevrait des valeurs mathématiquement absurdes (ex: température de 500 °C ou temps de fonctionnement négatif). La régression logistique produirait alors des probabilités faussées sans avertir le système appelant.
3. **Validation stricte par bornes physiques théoriques et mécaniques (Option retenue)** :
   - *Avantages* : Protège le modèle contre toute aberration de capteur (court-circuit, sonde débranchée, bogue de communication réseau), tout en autorisant une marge de fonctionnement réaliste propre au matériel.

### Décision retenue et Justifications Physiques
Nous utilisons le schéma Pydantic `SensorReading` avec des contraintes explicites `ge` (greater or equal) et `le` (less or equal) de type `float` :

* **`temperature_c` : `[-40.0 °C, 150.0 °C]`**
  - *Justification* : -40 °C correspond à la limite thermique inférieure pour les équipements industriels en environnement sévère sans préchauffage. 150 °C représente le seuil critique absolu d'un moteur électrique en classe d'isolation standard (H/F) ; au-delà, les isolants des bobinages fondent et les paliers se soudent mécaniquement. Une valeur supérieure à 150 °C (telle que 500 °C) relève d'une sonde défaillante ou d'un incendie majeur qui n'a pas à être traité par un modèle de prédiction statistique.
* **`vibration_mm_s` : `[0.0 mm/s, 100.0 mm/s]`**
  - *Justification* : La vitesse efficace de vibration (norme ISO 10816/20816) est une grandeur scalaire d'amplitude qui ne peut être négative (seuil min à 0). Une valeur supérieure à 45-50 mm/s classe déjà la machine en zone d'arrêt d'urgence destructeur (rupture d'arbre, desserrage massif). Borner à 100 mm/s autorise l'observation de chocs mécaniques violents tout en rejetant les valeurs aberrantes.
* **`load_pct` : `[0.0 %, 100.0 %]`**
  - *Justification* : Le taux de charge représente le pourcentage de sollicitation par rapport à la puissance nominale du groupe moteur. Une valeur négative est physiquement impossible. Le plafond à 100 % correspond à la pleine charge nominale continue de la machine.
* **`runtime_hours` : `[0.0 h, 200 000.0 h]`**
  - *Justification* : Le compteur horaire cumulé démarre à 0 pour une machine neuve. Une limite supérieure de 200 000 heures correspond à plus de 22 années d'exploitation ininterrompue 24h/24 et 7j/7, ce qui excède largement la durée de vie moyenne avant décommissionnement ou rénovation complète d'un équipement industriel de cette classe.

---

## Décision 2 : Gestion de l'absence du modèle (Code HTTP 503 vs Refus de démarrage)

### Options étudiées
1. **Échouer au démarrage (Crash/Fast-Fail)** :
   - L'application refuse de se lancer et s'arrête brutalement (`sys.exit(1)` ou exception non interceptée) si `models/model.joblib` est manquant.
   - *Ce que cette option fait perdre* : 
     - Perte totale d'observabilité : l'orchestrateur de conteneurs (ex: Kubernetes, Docker) ou les outils de monitoring ne peuvent plus interroger le point de santé `/health`.
     - Impossible d'accéder à la documentation interactive OpenAPI `/docs`.
     - Impossibilité pour un pipeline CI/CD ou un script d'administration de diagnostiquer l'état exact du service via le réseau.
2. **Démarrer en mode dégradé et répondre avec le code HTTP 503 (Option retenue)** :
   - Au démarrage (dans le gestionnaire `lifespan`), si `Predictor.load(...)` lève `FileNotFoundError`, nous enregistrons `state["predictor"] = None`.
   - L'endpoint `/health` reste opérationnel et signale `"model_loaded": false`.
   - Tout appel à `/v1/predict` lève immédiatement une `HTTPException` avec le code de statut **503 Service Unavailable** et un message explicite : `"Modèle non disponible : lancez d'abord python -m maintai.train."`.
   - *Ce que cette option fait perdre* :
     - Les requêtes de prédiction envoyées au service échouent temporairement jusqu'au chargement du modèle.
   - *Ce que cette option apporte* :
     - L'infrastructure réseau sait exactement que le serveur web fonctionne correctement mais que la ressource d'inférence est indisponible (différence sémantique essentielle entre une erreur de programmation 500 et une indisponibilité temporaire de ressource 503).
     - Le monitoring remonte immédiatement le statut sans panique du processus.

---

## Conséquences globales
- **Bénéfices** :
  - Rejet automatique des données invalides dès la couche protocolaire HTTP avec un statut `422 Unprocessable Entity` détaillé.
  - Résilience opérationnelle : l'API reste supervisable via `/health` même lors de phases de maintenance ou de réentraînement du modèle.
  - Documentation Swagger `/docs` auto-générée reflétant fidèlement les tolérances physiques mécaniques.
- **Points de vigilance** :
  - Si un nouveau type de machine industrielle aux caractéristiques plus puissantes (ex: charge avec pic à 110 % ou température de fonctionnement continu plus haute) est déployé, le schéma devra être adapté via une montée de version (`/v2`).
