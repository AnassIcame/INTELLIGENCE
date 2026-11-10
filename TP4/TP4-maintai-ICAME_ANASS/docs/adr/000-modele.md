# ADR 001 : Transformation de MaintAI en package Python distribuable

**Date :** 09/11/2026 · **Auteur :** ICAME Anass

## Contexte

Le projet MaintAI contient plusieurs modules Python pour la génération des données, l'entraînement du modèle et la prédiction des pannes. Il est nécessaire de rendre ces fonctionnalités réutilisables et installables dans différents environnements Python, sans obliger les utilisateurs à travailler directement dans le dossier source du projet.

## Options étudiées

1. **Conserver le projet sous forme de scripts Python :**
   - Avantages : structure simple, développement rapide et exécution directe des fichiers.
   - Inconvénients : installation moins pratique, réutilisation plus difficile et absence de commande standard pour lancer les prédictions.

2. **Transformer le projet en package Python avec `pyproject.toml` et créer un fichier Wheel :**
   - Avantages : installation avec pip, organisation claire des modules, gestion des dépendances et création d'une commande dédiée `maintai-predict`.
   - Inconvénients : configuration initiale plus complexe et nécessité de gérer les versions des dépendances et les fichiers nécessaires au fonctionnement du modèle.

## Décision

Nous avons choisi de transformer MaintAI en package Python en utilisant `pyproject.toml` et setuptools, puis de construire une distribution au format Wheel.

La raison principale est de faciliter l'installation et la réutilisation de MaintAI dans différents environnements Python. Le point d'entrée `maintai-predict` permet également de lancer les prédictions directement depuis le terminal.

## Conséquences

- Facilite l'installation du package avec `pip install`.
- Permet de réutiliser les modules Python sans dépendre directement du dossier source.
- Permet de créer une commande dédiée `maintai-predict`.
- Facilite la distribution du projet grâce aux fichiers `.whl` et `.tar.gz`.
- Nécessite de maintenir les dépendances et leurs versions pour assurer la compatibilité.
- Le modèle entraîné doit être rendu accessible séparément si celui-ci n'est pas inclus dans le Wheel.
- Il faut vérifier que les versions des bibliothèques utilisées pour entraîner et charger le modèle sont compatibles.