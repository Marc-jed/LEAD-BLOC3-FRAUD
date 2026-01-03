# Fraud Detection API – Real-Time Prediction

## Objectif

Cette API permet de **prédire en temps réel si une transaction est frauduleuse ou non**.
Elle s’appuie sur un modèle de Machine Learning **XGBoost** entraîné, versionné et stocké sur **AWS S3**, et s’intègre dans un pipeline Data & MLOps entièrement automatisé.

L’API est conçue pour :

* recevoir des transactions en temps réel
* effectuer une prédiction de fraude
* charger automatiquement le **dernier modèle disponible**
* mettre à jour le modèle **sans redémarrage** de l’API

---

## Architecture

* **Framework** : FastAPI
* **Modèle ML** : XGBoost
* **Stockage modèle** : AWS S3
* **Orchestration** : Airflow (appel API)
* **Monitoring & retrain** : MLflow + API de réentraînement

```
Transaction → API-FRAUD → Modèle XGBoost → Prédiction
                                ↑
                       Dernier modèle depuis S3
```

---

## Cycle de vie du modèle

1. L’API démarre et **charge automatiquement le dernier modèle** stocké sur S3
2. Les requêtes `/predict` utilisent ce modèle en mémoire
3. En cas de réentraînement :

   * une nouvelle version est enregistrée sur S3
   * l’API de retrain appelle `/reload-model`
   * le nouveau modèle est chargé **sans redémarrer l’API**

---

## Endpoints

###  `GET /`

Vérification que l’API est bien en ligne.

**Response**

```json
{
  "message": "Bienvenue sur l'API Fraude détéction - Utilisez /predict pour faire une prédiction"
}
```

---

###  `POST /predict`

Effectue une prédiction de fraude sur une transaction.

**Request body (exemple)**

```json
{
  "cc_num": 4716561796955522,
  "merchant": "fraud_Deckow-O'Conner",
  "category": "grocery_pos",
  "amt": 86.83,
  "first": "Lauren",
  "last": "Anderson",
  "gender": "F",
  "street": "11014 Chad Lake Apt. 573",
  "city": "Heart Butte",
  "state": "MT",
  "zip": 59448,
  "lat": 48.2777,
  "long": -112.8456,
  "city_pop": 743,
  "job": "Water engineer",
  "merch_lat": 49.016904,
  "merch_long": -113.640958,
  "year": 2025,
  "month": 11,
  "day": 17,
  "hour": 12,
  "minute": 45,
  "second": 10,
  "dob_year": 1972,
  "dob_month": 5,
  "dob_day": 4
}
```

**Response**

```json
{
  "is_fraud": 0
}
```

---

###  `POST /reload-model`

Recharge le **dernier modèle disponible sur S3** sans redémarrer l’API.

Cet endpoint est appelé automatiquement par l’API de réentraînement après un nouveau training.

**Response**

```json
{
  "status": "Rechargement en arrière-plan"
}
```

---

##  Chargement automatique du modèle (S3)

* L’API liste les modèles dans le bucket S3
* Sélectionne le plus récent via `LastModified`
* Charge automatiquement le dernier fichier `.joblib`

Cela garantit que :

* le modèle est **toujours à jour**
* aucune intervention manuelle n’est nécessaire

---

##  Lancement avec Docker

### Build

```bash
docker build -t api-fraud .
```

### Run

```bash
docker run -p 7860:7860 --env-file .env api-fraud
```

---

##  Variables d’environnement requises

| Variable                | Description                     |
| ----------------------- | ------------------------------- |
| `S3_BUCKET`             | Bucket S3 contenant les modèles |
| `AWS_ACCESS_KEY_ID`     | Clé AWS                         |
| `AWS_SECRET_ACCESS_KEY` | Secret AWS                      |
| `AWS_DEFAULT_REGION`    | Région AWS                      |

---

##  Performances du modèle

* **Modèle** : XGBoost
* **F1-score** : ~0.89
* **Précision** : ~0.96
* **Recall** : ~0.83

Le modèle est sélectionné pour :

* limiter les fausses alertes
* bloquer efficacement les fraudes
* garantir un bon équilibre métier

---

##  Sécurité & bonnes pratiques

* Modèle chargé une seule fois en mémoire
* Pas de données sensibles stockées dans l’API
* Versioning via S3 & MLflow
* Reload dynamique sans downtime

---

##  Intégration dans le pipeline global

Cette API est utilisée par :

* le DAG de prédiction temps réel (Airflow)
* le DAG de monitoring modèle
* l’API de réentraînement

---



