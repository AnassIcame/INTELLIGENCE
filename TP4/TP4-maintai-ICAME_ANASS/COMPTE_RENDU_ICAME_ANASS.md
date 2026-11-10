# Compte rendu · TP4 : MaintAI devient un package Python



**Nom et Prenom  :** ICAME Anass 
**Groupe :** G7
**Date :** 09/11/2026

---

## 1. Mise en place (dans `TP/TP4`, avec son propre `.venv`)

**Dernière ligne de `python -m pytest` juste après `pip install -r requirements.txt` :**

```text
2 failed, 25 passed, 1 warning in 8.58s
```

**Quels sont les deux tests qui échouent, et pourquoi ?**

Les deux tests qui échouent sont :

- `test_installed_version_matches_the_code`
- `test_command_is_declared`

Le premier échoue parce que le package `maintai` n'est pas encore installé dans l'environnement. Python ne trouve donc pas ses métadonnées de distribution.

Le deuxième échoue parce que la commande `maintai-predict` n'est pas encore déclarée comme point d'entrée dans l'environnement.

Ces deux tests sont liés à la configuration et à l'installation du package Python.

## 2. Sprint 1 : `pyproject.toml` et `pip install -e .`

**Sections `dependencies` et `[project.scripts]` :**

```toml
dependencies = [
    "numpy>=2.0",
    "pandas>=2.2",
    "scikit-learn>=1.5",
    "joblib>=1.4",
]

[project.scripts]
maintai-predict = "maintai.cli:main"
```

**Pourquoi `pytest` et `fastapi` ne sont-ils pas dans `dependencies` ?**

`pytest` sert uniquement à exécuter les tests. FastAPI est utilisé pour la partie API, mais il n'est pas indispensable au fonctionnement principal du package.

Ces bibliothèques sont placées dans des groupes optionnels :

- `dev` pour les outils de développement et les tests ;
- `api` pour les dépendances de l'API ;
- `ui` pour les dépendances de l'interface Streamlit.

Cela permet de ne pas installer des bibliothèques inutiles pour tous les utilisateurs.

**Sortie de `pip show maintai` (les quatre premières lignes) :**

```text
Name: maintai
Version: 0.2.0
Summary: Package Python de prédiction des pannes de maintenance industrielle
Home-page:
```

**Dernière ligne de `python -m pytest` à la fin du Sprint 1 :**

```text
27 passed, 1 warning in 3.16s
```

Les 27 tests passent. Le seul avertissement concerne l'utilisation de `httpx` avec `starlette.testclient`, qui est dépréciée.

**Exécution de la commande `maintai-predict` :**

Commande exécutée :

```powershell
maintai-predict 72 6 85 15000
```

Résultat :

```text
Probabilité de panne : 95 % (ALERTE)
```

La commande fonctionne après l'installation éditable du package.

**Modification du message dans `maintai/cli.py` sans réinstallation :**

Oui. Grâce à `pip install -e .`, le package est installé en mode éditable. Les modifications apportées aux fichiers sources sont directement prises en compte sans devoir réinstaller le package.

## 3. Sprint 2 : construire et installer le wheel

**Sortie de `dir dist` après `python -m build` :**

```text
maintai-0.2.0.tar.gz
maintai-0.2.0-py3-none-any.whl
```

La construction du package a réussi.

**Contenu du wheel (`tar -tf dist\maintai-0.2.0-py3-none-any.whl`) :**

```text
maintai/__init__.py
maintai/cli.py
maintai/client.py
maintai/config.py
maintai/data.py
maintai/dataset.py
maintai/predict.py
maintai/train.py
maintai/api/__init__.py
maintai/api/main.py
maintai/api/schemas.py
maintai/api/security.py
maintai-0.2.0.dist-info/METADATA
maintai-0.2.0.dist-info/WHEEL
maintai-0.2.0.dist-info/entry_points.txt
maintai-0.2.0.dist-info/top_level.txt
maintai-0.2.0.dist-info/RECORD
```

**Le modèle, les tests et `ui/` y sont-ils ? Pourquoi ?**

Non. Le wheel contient les modules Python du package `maintai` ainsi que les métadonnées de distribution.

Le modèle entraîné, les tests et le dossier `ui/` ne sont pas inclus, car la configuration de setuptools sélectionne uniquement les packages correspondant à `maintai*`.

**Installation dans un environnement neuf (`%TEMP%\essai`) :**

Le wheel a été installé dans un nouvel environnement virtuel avec la commande :

```powershell
python -m pip install "C:\Users\PC\Desktop\TP4\maintai-starter-tp4\dist\maintai-0.2.0-py3-none-any.whl"
```

L'installation a réussi.

Les imports de NumPy et Pandas ont également été vérifiés :

```text
NumPy OK
Pandas OK
```

**Résultat sans `MAINTAI_MODELS_DIR` :**

Cette vérification n'a pas été exécutée. Le package étant installé dans un environnement séparé du dossier du projet, il est probable que le modèle ne soit pas trouvé si aucun chemin de modèle par défaut n'est configuré.

**Résultat avec `MAINTAI_MODELS_DIR` configurée vers le dossier `models` :**

Commande exécutée :

```powershell
$env:MAINTAI_MODELS_DIR = "C:\Users\PC\Desktop\TP4\maintai-starter-tp4\models"
python -m maintai.cli 72 6 85 15000
```

Résultat :

```text
Probabilité de panne : 95 % (ALERTE)
```

Des avertissements `InconsistentVersionWarning` apparaissent lors du chargement du modèle.

**D'où vient l'avertissement `InconsistentVersionWarning` ? Quelle ligne de `models/model_info.json` permet de le comprendre ?**

Le modèle a été entraîné avec Scikit-learn 1.8.0, alors que l'environnement neuf utilise Scikit-learn 1.9.1.

Les avertissements concernent les objets `StandardScaler`, `LogisticRegression` et `Pipeline`.

Ils indiquent que le modèle a été enregistré avec une version différente de celle utilisée pour le charger. Cela peut entraîner des problèmes de compatibilité.

La version 1.8.0 est identifiée grâce aux avertissements affichés pendant le chargement du modèle. Le nom exact du champ correspondant dans `models/model_info.json` reste à vérifier.

**Test après installation de Scikit-learn 1.8.0 :**

La version utilisée pour entraîner le modèle est 1.8.0. Il est donc recommandé d'installer cette même version dans l'environnement neuf :

```powershell
python -m pip install scikit-learn==1.8.0
```

Le résultat attendu est une prédiction similaire :

```text
Probabilité de panne : 95 % (ALERTE)
```

Les avertissements de compatibilité devraient disparaître si la version installée correspond bien à celle utilisée pour entraîner le modèle. Ce résultat reste à confirmer par une exécution réelle.

## 4. Questions de compréhension

**1. Quelle différence entre `requirements.txt` et la liste `dependencies` de `pyproject.toml` ?**

`requirements.txt` sert à installer les dépendances d'un environnement de développement ou d'exécution. Il peut contenir des versions exactes afin de reproduire un environnement précis.

La liste `dependencies` de `pyproject.toml` déclare les bibliothèques nécessaires au fonctionnement du package lorsqu'un utilisateur l'installe. Elle peut utiliser des contraintes minimales de version.

**2. Quelle différence entre `pip install -e .` et `pip install dist\maintai-0.2.0-py3-none-any.whl` ?**

`pip install -e .` installe le package en mode éditable. Les modifications apportées aux fichiers sources sont directement prises en compte sans réinstallation.

`pip install dist\maintai-0.2.0-py3-none-any.whl` installe le package depuis un fichier wheel déjà construit. Il s'agit d'une installation classique indépendante du dossier source.

**3. Qu'est-ce qu'un point d'entrée (`[project.scripts]`) ? Où pip crée-t-il le fichier `maintai-predict.exe` ?**

Un point d'entrée permet de créer une commande utilisable directement dans le terminal.

Dans notre projet, `maintai-predict` appelle la fonction `main` du module `maintai.cli`.

Sous Windows, pip crée le fichier `maintai-predict.exe` dans le dossier `Scripts` de l'environnement virtuel :

```text
venv\Scripts\maintai-predict.exe
```

## 5. Le rendu Git

- **Le tag `tp4` existe sur GitHub :** oui


## 6. Ce qui reste flou

Tout est claire