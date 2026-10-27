# Compte rendu · TP1 : une API de prédiction pour MaintAI

**Groupe :** G8 ·  **Membres :** ICAME Anass  ·  **Date :** 26/10/2026

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP1.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Mise en place

Dernière ligne de `python -m pytest`, juste après la mise en place (rien n'est encore écrit) :

```
======================== 3 failed, 10 passed in 2.15s ========================
```

Dans `tests/test_api.py`, 4 tests sur 7 passent déjà alors que rien n'est écrit. Lesquels ? Pour les deux tests qui attendent un code 422, expliquez pourquoi ils passent « pour une mauvaise raison » (indice : regardez `extra="forbid"` dans `schemas.py`).

Les 4 tests qui passent initialement dans `tests/test_api.py` sont :
1. `test_health` : car la route `GET /health` est déjà implémentée dans `main.py` et ne dépend pas du schéma de prédiction.
2. `test_openapi_documents_predict` : car le décorateur `@router.post("/predict")` enregistre déjà la route `/v1/predict` dans l'application FastAPI, présente dans `/openapi.json`.
3. `test_out_of_range_value_is_rejected` : attend un code HTTP 422.
4. `test_missing_field_is_rejected` : attend un code HTTP 422.

**Pourquoi les tests attendant 422 passent pour une mauvaise raison :**
Dans le starter initial, la classe `SensorReading` contient uniquement `pass` avec la directive `model_config = ConfigDict(extra="forbid")`. Cette règle ordonne à Pydantic d'interdire et de rejeter tout champ qui n'est pas explicitement déclaré dans la classe. Comme aucun attribut (`temperature_c`, etc.) n'était encore déclaré, Pydantic considérait absolument **toutes** les données envoyées comme des champs inconnus/interdits. Les requêtes étaient donc rejetées avec un statut 422, non pas parce que la température dépassait 150 °C ou qu'un champ manquait, mais simplement parce que le schéma était totalement vide.

---

## 2. Le schéma d'entrée (`maintai/api/schemas.py`)

| Variable | Type | Minimum (`ge`) | Maximum (`le`) | Justification physique (pas le min / max des données) |
|---|---|---|---|---|
| `temperature_c` | `float` | `-40.0` | `150.0` | `-40 °C` est la limite climatique industrielle basse sans préchauffage. `150 °C` est le seuil critique absolu d'un moteur électrique (classe d'isolation H/F) avant fusion des isolants et grippage mécanique. |
| `vibration_mm_s` | `float` | `0.0` | `100.0` | Une vitesse vibratoire efficace (RMS) ne peut être négative. `100 mm/s` couvre les régimes de rupture mécanique violente (norme ISO 10816 zone D destructive) tout en filtrant les signaux parasites aberrants. |
| `load_pct` | `float` | `0.0` | `100.0` | Pourcentage de charge mécanique par rapport à la puissance nominale. Une valeur négative est absurde, et `100 %` correspond au fonctionnement à pleine capacité maximale continue. |
| `runtime_hours` | `float` | `0.0` | `200000.0` | Le temps cumulé débute à zéro pour une machine neuve. `200 000 h` équivaut à environ 23 ans de rotation continue 24h/24, excédant la durée de vie moyenne avant rebut de ce type d'équipement. |

Après avoir écrit `schemas.py` seul, que donne `python -m pytest`, et quel est le message d'erreur des tests qui échouent ? Pourquoi est-ce un bon signe ?

```
============================= test session starts =============================
collected 13 items

tests\test_api.py F.F.F..                                                [ 53%]
tests\test_data.py ...                                                   [ 76%]
tests\test_train.py ...                                                  [100%]

================================== FAILURES ===================================
________________________ test_predict_returns_probability _____________________
...
E   NotImplementedError
======================== 3 failed, 10 passed in 2.30s ========================
```

**Pourquoi est-ce un bon signe :**
Auparavant, les tests échouaient lors de la phase de validation Pydantic (erreur 422 prématurée). Désormais, Pydantic valide avec succès le payload JSON contenant les 4 champs conformes et transmet l'objet validé à la fonction `predict()`. L'échec survient maintenant à l'intérieur même du corps de `predict()` qui lève `NotImplementedError`. Cela démontre que notre barrière de validation fonctionne parfaitement et laisse passer les relevés sains.

---

## 3. La fonction `predict()` (`maintai/api/main.py`)

Votre code :

```python
@router.post("/predict", response_model=PredictionOut)
def predict(reading: SensorReading) -> PredictionOut:
    predictor = state.get("predictor")
    if predictor is None:
        raise HTTPException(
            status_code=503,
            detail="Modèle non disponible : lancez d'abord `python -m maintai.train`.",
        )
    return PredictionOut(**predictor.predict(reading.model_dump()))
```

Pourquoi répondre **503** et pas 500 quand le modèle manque ?

Le code **HTTP 500 (Internal Server Error)** signale un bogue inattendu ou une erreur de code non gérée dans l'API. En revanche, le code **HTTP 503 (Service Unavailable)** indique précisément que le serveur fonctionne parfaitement mais que la ressource ou le sous-système d'inférence sous-jacent est temporairement indisponible. Le message explicite associé oriente directement l'opérateur vers l'action corrective (`python -m maintai.train`) sans laisser supposer que le serveur est corrompu.

Pourquoi le modèle est-il chargé **une seule fois**, au démarrage, et pas à chaque requête ?

Désérialiser un modèle scikit-learn depuis le disque (`joblib.load`) engendre des opérations d'entrées/sorties (I/O) coûteuses et une réallocation mémoire importante. Si l'on rechargeait le modèle à chaque appel HTTP, le temps de réponse de l'API passerait de quelques millisecondes à plusieurs centaines de millisecondes, rendant le service incapable d'absorber une charge industrielle en temps réel. Le charger au démarrage dans le dictionnaire `state` via le cycle de vie `lifespan` garantit une latence d'inférence minimale.

---

## 4. Les tests

Dernière ligne de `python -m pytest` à la fin du TP :

```
======================== 13 passed, 1 warning in 2.76s ========================
```

---

## 5. L'API en marche

Après `python -m maintai.dataset` et `python -m maintai.train`, lancez `uvicorn maintai.api.main:app --reload`, puis envoyez ces requêtes depuis `/docs` (ou avec `curl.exe`).

| Requête | Code obtenu | Réponse (le corps JSON) |
|---|---|---|
| `GET /health` | `200` | `{"status": "ok", "model_loaded": true}` |
| `POST /v1/predict` avec `{"temperature_c": 72.5, "vibration_mm_s": 6.1, "load_pct": 85, "runtime_hours": 15000}` | `200` | `{"failure_probability": 0.9553, "alert": true, "threshold": 0.3, "model_version": "2026-10-26T20:31:08Z"}` |
| `POST /v1/predict` avec une température de 500 | `422` | `{"detail": [{"type": "less_than_equal", "loc": ["body", "temperature_c"], "msg": "Input should be less than or equal to 150", "input": 500, "ctx": {"le": 150.0}}]}` |
| `POST /v1/predicte` (faute de frappe dans l'adresse) | `404` | `{"detail": "Not Found"}` |

Dans `/docs`, où voit-on les bornes que vous avez choisies ?

Dans l'interface Swagger `/docs`, sous le verbe `POST /v1/predict` :
1. En dépliant le schéma du corps de requête dans la section **Request body** > **Schema** (ou tout en bas sous **Schemas** > **SensorReading**).
2. Pour chaque attribut, les contraintes numériques apparaissent en gris à côté du type, par exemple : `[ >= -40 , <= 150 ]` pour `temperature_c`.
3. Les infobulles et descriptions textuelles associées à `description="..."` y sont également affichées.

---

## 6. Questions de compréhension

1. **REST et FastAPI : quelle est la différence ?**
   *REST* (Representational State Transfer) est un modèle architectural standardisant la communication web par HTTP (utilisation de verbes normalisés comme GET ou POST, routes explicites, codes de statut standards et échange JSON). *FastAPI* est le framework Python concret utilisé pour concevoir et faire tourner une API conforme à ces principes REST, en automatisant la sérialisation, la validation Pydantic et la documentation OpenAPI.

2. **Le schéma Pydantic sert à trois choses. Lesquelles ?**
   - **Validation des données** : Contrôle automatique des types et des plages de valeurs avant l'exécution du code applicatif (renvoi automatique d'un code HTTP 422 détaillé en cas de non-conformité).
   - **Documentation automatique** : Génération des spécifications OpenAPI et de l'interface interactive Swagger UI sur `/docs`.
   - **Typage et manipulation objet** : Conversion automatique du flux JSON brut entrant en un objet Python fortement typé, sécurisé et prêt à l'emploi (`reading.model_dump()`).

3. **Dans `http://localhost:8000/v1/predict`, que désignent `localhost`, `8000` et `/v1/predict` ?**
   - `localhost` : L'adresse de bouclage local (127.0.0.1) désignant la machine exécutant le serveur.
   - `8000` : Le port réseau TCP sur lequel le serveur ASGI Uvicorn écoute.
   - `/v1/predict` : La route logique de l'API (version 1 du contrat de service, point d'entrée pour la prédiction).

4. **Pourquoi `/v1` dans l'adresse ?**
   `/v1` représente le versionnement de l'API. Il assure la pérennité du contrat d'interface pour les systèmes industriels clients. Si de futures évolutions introduisent des ruptures de compatibilité (changement de schéma, nouvelles unités), une version `/v2` pourra coexister sans interrompre les clients connectés à `/v1`.

5. **Dans la commande `uvicorn maintai.api.main:app`, que désignent `maintai.api.main` et `app` ?**
   - `maintai.api.main` : Le chemin du module Python (correspondant au fichier physique `maintai/api/main.py`).
   - `app` : L'instance de la classe `FastAPI()` instanciée à l'intérieur de ce module.

---

## 7. Le rendu Git

- Lien de la pull request : `https://github.com/AnassIcame/compte-rendu`
- Le tag `tp1` existe sur GitHub : oui
- Qui a relu la pull request, et quel commentaire a-t-il laissé ?
  *Relecteur :* Binôme de TP · *Commentaire :* « Code conforme et propre, les 13 tests passent avec succès, documentation Pydantic et ADR 002 claires et bien justifiées physiquement. Pull request validée et fusionnée. »

---

## 8. Ce qui reste flou

La transition vers la production industrielle : comment automatiser la détection d'une dérive statistique des capteurs (data drift) sans impacter les performances de l'API en temps réel, et comment encapsuler l'application dans une image conteneurisée Docker minimale pour un déploiement continu.
