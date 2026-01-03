#  API Retrain – Fraud Detection Model

##  Objectif

Cette API permet de **réentraîner automatiquement le modèle de détection de fraude** lorsqu’une dégradation de performance est détectée (baisse du F1-score).

Elle s’intègre dans une architecture **MLOps complète**, orchestrée par Airflow, et assure :

* le réentraînement du modèle sur les données récentes
* le versioning du modèle via **MLflow**
* le stockage du nouveau modèle sur **AWS S3**
* la notification automatique de l’API de prédiction pour recharger le modèle

---

##  Architecture & Rôle

* **Framework** : FastAPI
* **Modèle ML** : XGBoost
* **Suivi expérimental** : MLflow
* **Stockage modèles** : AWS S3
* **Déclenchement** : DAG Airflow (monitoring modèle)
* **Communication inter-API** : HTTP REST

```
Airflow (monitoring)
        ↓
API-RETRAIN
        ↓
MLflow → S3 (nouveau modèle)
        ↓
API-FRAUD (/reload-model)
```

---

##  Cycle de réentraînement

1. Airflow détecte une baisse de performance (F1-score < seuil)
2. L’API `/retrain` est appelée
3. Le modèle est réentraîné sur les données historiques
4. Les métriques sont enregistrées dans MLflow
5. Le nouveau modèle est sauvegardé sur S3
6. L’API de prédiction est notifiée pour recharger le modèle

 **Aucun redémarrage manuel n’est nécessaire**

---

##  Endpoints

###  `GET /`

Vérification que l’API est bien accessible.

**Response**

```json
{
  "message": "Bienvenue sur l'API de retrain du modèle XGBoost pour la prédiction de fraude de transaction"
}
```

---

###  `POST /retrain`

Lance le réentraînement du modèle.

**Fonctionnalités exécutées :**

* chargement des données depuis PostgreSQL (Neon)
* preprocessing (numérique + catégoriel)
* entraînement XGBoost
* évaluation (F1, Recall, Precision)
* log des métriques dans MLflow
* sauvegarde du modèle sur S3
* notification de l’API-FRAUD

**Response (exemple)**

```json
{
  "status": "retraining completed",
  "f1_score": 0.89,
  "precision": 0.96,
  "recall": 0.83
}
```

---

##  Entraînement du modèle

* **Features numériques** : StandardScaler
* **Features catégorielles** : OneHotEncoder
* **Pipeline sklearn** avec ColumnTransformer
* **Modèle** : XGBoostClassifier
* **Split** : Train / Test stratifié
* **Metric principale** : F1-score

---

##  Suivi expérimental avec MLflow

Chaque run enregistre :

* paramètres du modèle
* métriques de performance
* version du modèle
* artefact modèle (joblib)

MLflow permet :

* comparaison entre versions
* audit des performances
* traçabilité des réentraînements

---

## ☁️ Stockage du modèle (S3)

* Chaque modèle est stocké avec un nom unique :

```
mlflow/models/model_<run_id>.joblib
```

* L’API de prédiction charge automatiquement **le dernier modèle uploadé**

---

##  Communication avec l’API de prédiction

Une fois le réentraînement terminé :

```python
requests.post("https://gdleds-api-fraud.hf.space/reload-model")
```

 Le nouveau modèle est chargé **à chaud**, sans interruption de service.

---

##  Lancement avec Docker

### Build

```bash
docker build -t api-retrain .
```

### Run

```bash
docker run -p 7860:7860 --env-file .env api-retrain
```

---

##  Variables d’environnement requises

| Variable                | Description               |
| ----------------------- | ------------------------- |
| `S3_BUCKET`             | Bucket S3 des modèles     |
| `AWS_ACCESS_KEY_ID`     | Clé AWS                   |
| `AWS_SECRET_ACCESS_KEY` | Secret AWS                |
| `AWS_DEFAULT_REGION`    | Région AWS                |
| `MLFLOW_TRACKING_URI`   | URI MLflow                |
| `POSTGRES_CONN`         | Connexion Neon PostgreSQL |

---

##  Bonnes pratiques MLOps implémentées

* Réentraînement automatisé
* Versioning modèle
* Traçabilité complète
* Monitoring de la performance
* Déploiement sans downtime
* Séparation prediction / training

---

##  Intégration globale

Cette API est utilisée par :

* le DAG de monitoring du modèle
* le DAG de prédiction temps réel
* l’API-FRAUD pour le rechargement dynamique

---
