# LEAD-BLOC3-FRAUD-DETECTION

## Objectif
Détecter des transactions frauduleuses en temps réel à l’aide d’un pipeline
data entièrement automatisé et supervisé.

## Architecture globale
- Collecte temps réel via API
- Orchestration avec Airflow
- Prédiction via FastAPI
- Stockage : S3 + PostgreSQL (Neon)
- Monitoring & réentraînement automatique du modèle
- Visualisation via Airtable

## Pipeline de données
1. Récupération des transactions
2. Stockage des données brutes (S3)
3. Transformation & prédiction temps réel
4. Enregistrement en base PostgreSQL
5. Alertes email en cas de fraude
6. Reporting quotidien (BI)
7. Surveillance du modèle (F1-score)
8. Réentraînement automatique si dérive

## Machine Learning
- Modèle : XGBoost
- Optimisation : GridSearch
- Suivi des performances : MLflow
- Retrain automatique sous seuil de F1-score

## Structure du projet
(API-FRAUD, API-RETRAIN, DAG-FRAUD, MLFLOW-FRAUD…)

## Technologies
Airflow · FastAPI · S3 · PostgreSQL · XGBoost · MLflow · Docker · Airtable

## 📽️ Démo
Voir dossier VIDEO-PRESENTATION

## 👤 Auteur
Ton nom / GitHub / LinkedIn
