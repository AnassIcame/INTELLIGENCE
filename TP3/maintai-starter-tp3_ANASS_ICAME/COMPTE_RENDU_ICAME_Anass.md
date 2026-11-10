# Compte rendu · TP3 : Interface interactive Streamlit pour MaintAI

**Module :** Développement et déploiement d'applications intelligentes  
**Projet :** MaintAI — Système de maintenance prédictive  
**Étudiante :** ICAME Anass  
**Groupe :** G7 
**Date :** 09/11/2026  

---

## 1. Contexte opérationnel et état initial des tests

### 1.1 Objectifs du TP3
L'objectif de cette séance est de concevoir un tableau de bord analytique et décisionnel complet en Python à l'aide de **Streamlit**, permettant d'interagir nativement avec l'API REST sécurisée de **MaintAI**. Ce tableau de bord remplace le client web statique du TP2 par une interface d'ingénierie riche, structurée en deux vues complémentaires :
1. Une vue d'**exploration des données historiques** (statistiques descriptives, distribution des avaries et corrélation vibratoire/thermique).
2. Une vue d'**inférence prédictive en temps réel** (saisie interactive des paramètres télémétriques, interrogation sécurisée du modèle via le client HTTP et affichage dynamique des alertes de maintenance).

### 1.2 Diagnostic initial et corrections apportées
Dès l'intégration du squelette de départ, l'exécution du banc de tests automatisé a révélé **4 échecs sur 23 tests** (`4 failed, 19 passed`) :
```powershell
python -m pytest
```

Les anomalies identifiées et corrigées concernaient :
- **L'encapsulation du client HTTP (`maintai/client.py`) :** La méthode `predict()` devait envoyer une requête `POST` formatée sur `/v1/predict` tout en véhiculant obligatoirement la clé d'authentification dans l'en-tête HTTP `X-API-Key`.
- **L'alignement des conventions de nommage (`ui/app.py`) :** Harmonisation des identifiants de champs entre le dictionnaire renvoyé par l'API (`failure_probability`, `alert`, `threshold`) et ceux attendus par les composants Streamlit.
- **La résilience face aux pannes :** Gestion explicite des erreurs HTTP via la levée de l'exception personnalisée `APIError(status_code, detail)`.

### 1.3 Validation intégrale des tests
Après correction et optimisation du code, l'ensemble des 23 tests unitaires et d'intégration a été validé avec succès :

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\hp\Downloads\TP1_YEKHLEF_Aya\TP\TP3\TP3-maintai-Hajar-Belhachmi
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1
collected 23 items

tests\test_api.py .......                                                [ 30%]
tests\test_client.py ...                                                 [ 43%]
tests\test_data.py ...                                                   [ 56%]
tests\test_security.py .....                                             [ 78%]
tests\test_train.py ...                                                  [ 91%]
tests\test_ui.py ..                                                      [100%]

======================== 23 passed, 1 warning in 8.86s ========================
```
*Note sur l'avertissement :* Le `StarletteDeprecationWarning` est un simple message informatif de compatibilité entre `httpx` et `starlette.testclient`, sans incidence sur le bon fonctionnement applicatif.

---

## 2. Déploiement et exécution de l'application Streamlit

Pour instancier le serveur de présentation Streamlit, nous exécutons la commande :
```powershell
python -m streamlit run ui/app.py
```
Le tableau de bord est immédiatement accessible localement à l'adresse réseau :
```text
http://localhost:8501
```

L'application organise le parcours utilisateur via deux onglets distincts (`st.tabs`) :
- **Données :** Restitution statistique et analyse visuelle du comportement des machines.
- **Prédiction :** Simulateur d'inférence avec saisie des télémétries et restitution visuelle des alertes de casse.

---

## 3. Vue 1 : Exploration et analyse visuelle des données

### 3.1 Indicateurs synthétiques clés (KPIs)
Dans la section analytique, trois métriques globales permettent d'appréhender instantanément la volumétrie et la distribution du jeu de données :

| Indicateur métier | Fonction Pandas | Valeur mesurée | Interprétation technique |
|---|---|---:|---|
| **Volume de relevés** | `len(df)` | **5 000** | Échantillon représentatif de télémétries machines. |
| **Taux d'avarie global** | `df['failure'].mean() * 100` | **13,6 %** | Déséquilibre caractéristique de la maintenance industrielle (les défaillances sont minoritaires). |
| **Température moyenne** | `df['temperature_c'].mean()` | **59,8 °C** | Niveau d'échauffement nominal de croisière des équipements. |

### 3.2 Taux de panne selon la température (Histogramme par tranches)
Afin d'analyser l'influence de la contrainte thermique sur la probabilité de casse :
- La variable continue `temperature_c` a été segmentée en **10 intervalles réguliers** via `pd.cut()`.
- Pour chaque plage, le taux moyen de défaillance a été agrégé puis visualisé à l'aide de `st.bar_chart()`.
- **Constat analytique :** On observe une non-linéarité marquée : le risque de panne demeure faible et stable en dessous de 65 °C, puis connaît une croissance quasi-exponentielle dès lors que la température franchit les 80 °C.

### 3.3 Cartographie bivariée : Température vs Vibrations
Pour observer le couplage des sollicitations mécaniques :
- Un nuage de points (`st.scatter_chart`) projette la température en abscisse ($X$) et la vitesse vibratoire en ordonnée ($Y$).
- La dimension couleur sépare nettement les machines saines (`failure = 0`) des machines tombées en panne (`failure = 1`).
- **Constat analytique :** Les points défaillants se concentrent massivement dans le quadrant supérieur droit (zones conjointes de haute température et de fortes vibrations), confirmant la pertinence de ces deux facteurs dans la modélisation prédictive.

### 3.4 Stratégie d'optimisation : Mise en cache avec `@st.cache_data`
Le chargement du fichier CSV est encapsulé dans une fonction décorée par `@st.cache_data` :
```python
@st.cache_data
def charger_donnees():
    return load_data()
```
* **Principe :** Par nature, Streamlit réexécute l'intégralité du script Python à chaque interaction utilisateur (manipulation d'un slider, clic sur un bouton).
* **Gain technique :** Grâce à `@st.cache_data`, les données lues sont persistées dans la mémoire vive du processus serveur. Les relectures disques inutiles sont évitées, garantissant une fluidité parfaite et une latence d'affichage quasi-nulle.

---

## 4. Vue 2 : Interface de prédiction opérationnelle

### 4.1 Formulaire ergonomique de saisie
Pour garantir la robustesse des entrées, le formulaire regroupe les paramètres d'exploitation en s'appuyant sur des widgets interactifs bornés :
- `st.slider` pour la **température** (plage : -40 °C à 150 °C).
- `st.slider` pour la **vibration** (plage : 0 à 100 mm/s).
- `st.slider` pour la **charge** (plage : 0 % à 100 %).
- `st.number_input` pour les **heures de fonctionnement** (valeurs positives, jusqu'à 200 000 h).
- `st.form_submit_button` pour déclencher atomiquement la requête sans soumission prématurée à chaque modification de curseur.

### 4.2 Implémentation du client d'API (`MaintaiClient`)
La communication réseau est déléguée à la classe `MaintaiClient` dans `maintai/client.py` :
```python
def predict(self, releve: dict) -> dict:
    """Transmet le relevé de capteurs à l'API MaintAI et retourne la prédiction."""
    headers = {}
    if self.api_key:
        headers["X-API-Key"] = self.api_key

    response = self.http.post("/v1/predict", json=releve, headers=headers)

    if response.status_code != 200:
        raise APIError(response.status_code, response.json().get("detail"))

    return response.json()
```

### 4.3 Restitution visuelle et gestion des alertes
Lors de la réception de la réponse JSON de l'API :
- **Probabilité de défaillance :** Affichée sous forme de pourcentage calibré.
- **Statut opérationnel :**
  - Si `alert == True` (probabilité $\ge$ seuil de 0,3) : Déclenchement d'un bandeau rouge `st.error` alertant sur l'imminence d'une défaillance mécanique nécessitant une intervention d'urgence.
  - Si `alert == False` : Affichage d'un bandeau vert `st.success` confirmant un état de marche nominal.
- **Gestion d'erreurs :**
  - Interception des erreurs de sécurité `401 Unauthorized` (clé API invalide ou absente).
  - Capture des erreurs de communication réseau `httpx.HTTPError` (API non lancée ou inaccessible) avec affichage d'un message didactique invitant à démarrer le serveur FastAPI.

### 4.4 Matrice de qualification des scénarios

| Scénario testé | Paramètres simulés | Réponse système observée |
|---|---|---|
| **Fonctionnement nominal** | T: 50 °C, Vib: 2 mm/s, Charge: 45 %, Heures: 2 000 | Statut 200, probabilité < 0.3, bannière verte de conformité |
| **Surcharge critique** | T: 95 °C, Vib: 12 mm/s, Charge: 95 %, Heures: 18 000 | Statut 200, probabilité > 0.8, alerte rouge de maintenance requise |
| **Clé API erronée** | En-tête `X-API-Key` incorrect | Levée d'`APIError(401)`, message d'erreur d'authentification |
| **Serveur API hors ligne** | Uvicorn arrêté sur le port 8000 | Levée de `httpx.ConnectError`, alerte d'indisponibilité du service |

---

## 5. Analyse conceptuelle et questions de réflexion

### 5.1 Quelle est la différence fondamentale entre l'interface du TP2 et celle du TP3 ?
* **Architecture TP2 (Web classique / Client-Side) :** L'interface repose sur du HTML/JavaScript s'exécutant directement dans le moteur de rendu du navigateur client. C'est le navigateur de l'utilisateur qui forge et envoie directement les requêtes HTTP `fetch()` vers l'API, ce qui soulève notamment la problématique des restrictions CORS (*Cross-Origin Resource Sharing*).
* **Architecture TP3 (Streamlit / Server-Side) :** L'interface est entièrement rédigée en Python et s'exécute côté serveur. Les appels réseau vers l'API FastAPI sont initiés par le processus Python du backend Streamlit (via `httpx`). Le navigateur ne reçoit que le rendu visuel généré. Il n'y a donc aucun blocage CORS et la clé API peut rester protégée sur le serveur applicatif sans être divulguée dans le code JavaScript côté client.

### 5.2 Pourquoi les tests unitaires fonctionnent-ils sans démarrer le serveur Uvicorn ?
La bibliothèque de test s'appuie sur `TestClient` (dérivé de Starlette et s'appuyant sur HTTPX). `TestClient` dialogue directement avec l'objet applicatif ASGI `app = FastAPI()` en mémoire, via des appels de fonctions asynchrones internes. Il n'est donc pas nécessaire d'ouvrir un socket TCP réel sur le port 8000 ni de lancer le serveur Uvicorn en arrière-plan, ce qui confère aux tests une rapidité d'exécution extrême et une isolation totale vis-à-vis des aléas réseau.

### 5.3 Quelle technologie recommander pour une application industrielle en production ?
Le choix technologique dépend directement du public cible et des exigences de charge :
* **Streamlit est idéal pour :** Les outils internes d'ingénierie, la surveillance d'atelier par des équipes techniques restreintes, le prototypage rapide et les tableaux de bord de data science. Il permet une vélocité de développement exceptionnelle et une intégration directe avec les bibliothèques d'IA Python.
* **Une solution Web découplée (FastAPI + React/Vue/Angular) est requise pour :** Les applications SaaS industrielles à forte concurrence (milliers d'utilisateurs simultanés), nécessitant une personnalisation graphique poussée au pixel près, une gestion granulaire des droits d'accès côté client et une optimisation fine de la bande passante mobile.

---

## 6. Synthèse et enseignements

Ce TP3 a permis de finaliser l'architecture applicative complète de **MaintAI** en reliant la chaîne de modélisation statistique, l'exposition par microservice REST et l'interface utilisateur décisionnelle. 

Points clés assimilés :
- Utilisation pragmatique de Streamlit pour construire des tableaux de bord interactifs pilotés par la donnée.
- Intégration d'un cache mémoire intelligent (`@st.cache_data`) pour optimiser les performances de calcul.
- Sécurisation et découplage propre de la logique métier grâce à un client HTTP dédié encapsulant la gestion des en-têtes et des exceptions.
- Validation rigoureuse par 23 tests automatisés garantissant la non-régression du système.

