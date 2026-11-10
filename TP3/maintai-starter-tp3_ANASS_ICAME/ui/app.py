
"""
Interface Streamlit de MaintAI :
explorer les données, puis demander une prédiction à l'API.

Lancement :
python -m streamlit run ui/app.py
"""

import httpx
import pandas as pd
import streamlit as st

from maintai.client import APIError, MaintaiClient
from maintai.config import FEATURES, get_settings


# =====================================================
# CONFIGURATION DE L'APPLICATION
# =====================================================

st.set_page_config(
    page_title="MaintAI",
    page_icon="🔧",
    layout="wide"
)

st.title("🔧 MaintAI · Prédiction de panne")
st.write("Analyse des données et prédiction des risques de panne.")


# =====================================================
# CHARGEMENT DES DONNÉES
# =====================================================

@st.cache_data
def charger(path) -> pd.DataFrame:
    """Charger les données CSV une seule fois."""
    return pd.read_csv(path)


# =====================================================
# BARRE LATÉRALE : CONFIGURATION API
# =====================================================

with st.sidebar:
    st.header("Configuration API")

    url = st.text_input(
        "URL de l'API",
        "http://localhost:8000"
    )

    cle = st.text_input(
        "Clé API",
        type="password"
    )


# =====================================================
# CRÉATION DES ONGLETS
# =====================================================

onglet_donnees, onglet_prediction = st.tabs(
    ["📊 Données", "🔮 Prédiction"]
)


# =====================================================
# SPRINT 1 : EXPLORER LES DONNÉES
# =====================================================

with onglet_donnees:

    st.header("Exploration des données")

    try:
        df = charger(get_settings().data_path)

        # Vérifier les colonnes nécessaires
        colonnes_requises = [
            "failure",
            "temperature_c",
            "vibration_mm_s"
        ]

        colonnes_manquantes = [
            col for col in colonnes_requises
            if col not in df.columns
        ]

        if colonnes_manquantes:
            st.error(
                f"Colonnes manquantes : {colonnes_manquantes}"
            )

        else:

            # 1. Trois indicateurs principaux
            st.subheader("Indicateurs principaux")

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Nombre de relevés",
                len(df)
            )

            c2.metric(
                "Taux de panne",
                f"{df['failure'].mean() * 100:.2f} %"
            )

            c3.metric(
                "Température moyenne",
                f"{df['temperature_c'].mean():.2f} °C"
            )

            st.divider()

            # 2. Choisir une variable
            st.subheader("Analyse d'une variable")

            variables_disponibles = [
                col for col in FEATURES
                if col in df.columns
                and pd.api.types.is_numeric_dtype(df[col])
            ]

            if variables_disponibles:

                variable = st.selectbox(
                    "Choisir une variable :",
                    variables_disponibles
                )

                # 3. Calculer le taux de panne par tranche
                tranches = pd.cut(
                    df[variable],
                    bins=10
                )

                taux = (
                    df.assign(tranche=tranches)
                    .groupby("tranche", observed=False)["failure"]
                    .mean()
                    .mul(100)
                    .dropna()
                    .rename_axis("tranche")
                    .reset_index(name="taux_panne")
                )

                # Convertir les intervalles en chaînes
                taux["tranche"] = taux["tranche"].astype(str)

                st.subheader(
                    f"Taux de panne selon {variable}"
                )

                if not taux.empty:
                    st.bar_chart(
                        taux,
                        x="tranche",
                        y="taux_panne",
                        x_label=variable,
                        y_label="Taux de panne (%)"
                    )
                else:
                    st.info(
                        "Aucune donnée disponible pour cette variable."
                    )

            else:
                st.warning(
                    "Aucune variable numérique disponible."
                )

            st.divider()

            # 4. Nuage de points température / vibration
            st.subheader("Température et vibration")

            st.scatter_chart(
                df,
                x="temperature_c",
                y="vibration_mm_s",
                color="failure"
            )

    except FileNotFoundError:
        st.error(
            "Fichier sensors.csv introuvable. "
            "Vérifiez le chemin configuré dans votre fichier .env."
        )

    except Exception as e:
        st.error(
            f"Erreur lors du chargement des données : {e}"
        )


# =====================================================
# SPRINT 2 : DEMANDER UNE PRÉDICTION À L'API
# =====================================================

with onglet_prediction:

    st.header("Prédiction du risque de panne")

    st.write(
        "Saisissez les mesures de votre machine "
        "pour obtenir une prédiction."
    )

    with st.form("releve"):

        releve = {
            "temperature_c": st.slider(
                "Température (°C)",
                -40.0,
                150.0,
                72.0
            ),

            "vibration_mm_s": st.slider(
                "Vibration (mm/s)",
                0.0,
                50.0,
                6.0
            ),

            "load_pct": st.slider(
                "Charge (%)",
                0.0,
                100.0,
                85.0
            ),

            "runtime_hours": st.number_input(
                "Heures de fonctionnement",
                min_value=0,
                max_value=100000,
                value=15000
            )
        }

        envoye = st.form_submit_button("🔍 Prédire")

    # Exécuter la prédiction après le clic
    if envoye:

        try:
            # 1. Créer le client et appeler predict()
            api = MaintaiClient(
                url,
                api_key=cle or None
            )

            resultat = api.predict(releve)

            # Récupérer la probabilité retournée par l'API
            probabilite = resultat.get(
                "probability",
                resultat.get("failure_probability")
            )

            if probabilite is None:

                st.error(
                    "La réponse de l'API ne contient pas "
                    "de probabilité de panne."
                )

            else:

                probabilite = float(probabilite)

                # Conversion en pourcentage
                pct = (
                    probabilite * 100
                    if 0 <= probabilite <= 1
                    else probabilite
                )

                # 2. Afficher la probabilité arrondie
                st.subheader("Résultat de la prédiction")

                st.metric(
                    "Probabilité de panne",
                    f"{pct:.0f} %"
                )

                # 3. Déterminer le niveau de risque
                alerte = resultat.get("alert")

                if alerte is None:
                    alerte = (
                        probabilite >= get_settings().threshold
                    )

                if alerte:
                    st.error(
                        "⚠️ ALERTE : risque de panne détecté ! "
                        "Une intervention est recommandée."
                    )

                else:
                    st.success(
                        "✅ Fonctionnement normal : "
                        "aucun risque élevé détecté."
                    )

                # Afficher les détails
                with st.expander("Détails de la prédiction"):
                    st.json(resultat)

        # Gestion des erreurs API
        except APIError as e:

            st.warning(
                f"Erreur API {e.status_code} : {e.detail}"
            )

        except httpx.HTTPError as e:

            st.error(
                f"API injoignable : {e}"
            )

        except Exception as e:

            st.error(
                f"Une erreur est survenue : {e}"
            )
