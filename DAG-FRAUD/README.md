#  DAG-FRAUD – Orchestration Airflow (Fraud Detection)

##  Objectif

Ce module contient l’ensemble des **DAGs Airflow** permettant d’orchestrer automatiquement le pipeline de détection de fraude :

* collecte des transactions en temps réel
* prédiction de fraude via une API ML
* stockage des données brutes et enrichies
* reporting quotidien et visualisation BI
* supervision des performances du modèle
* déclenchement automatique du réentraînement

L’objectif est de garantir une **chaîne data & ML entièrement automatisée, fiable et scalable**.

---

##  Architecture globale

Les DAGs interagissent avec :

* **API de transactions** (temps réel)
* **API de prédiction FastAPI**
* **AWS S3** (stockage données brutes & modèles)
* **PostgreSQL (Neon)** (base analytique)
* **MLflow** (monitoring du modèle)
* **Tableau BI** (visualisation)
* **Email** (alerting & reporting)

---

##  Arborescence

```
DAG-FRAUD/
│
├── dags/
│   ├── transaction_predict_dags.py
│   ├── reportingBI_dags.py
│   ├── control_model_dags.py
│
├── docker-compose.yaml
```

---

##  Description des DAGs

---

### 1️ transaction_predict_dags.py

 **Pipeline temps réel – Collecte & prédiction**

**Fréquence** : toutes les X secondes / minutes

#### Étapes principales :

1. Appel d’une API de transactions en temps réel
2. Sauvegarde des données brutes (JSON) sur S3
3. Transformation des données
4. Appel de l’API de prédiction de fraude
5. Enregistrement des résultats dans PostgreSQL
6. Envoi d’un email en cas de fraude détectée

 **Objectif** : détection immédiate des transactions frauduleuses

---

###  reportingBI_dags.py

 **Reporting quotidien & analyse business**

**Fréquence** : 1 fois par jour (J+1)

#### Étapes principales :

1. Extraction des transactions de la veille depuis PostgreSQL
2. Calcul des KPIs :

   * volume de transactions
   * montant total
   * taux de fraude
3. Génération de graphiques (Plotly)
4. Envoi d’un rapport par email
5. Alimentation d’Airtable / Tableau BI

 **Objectif** : suivi business et analyse historique

---

###  control_model_dags.py

 **Monitoring & MLOps**

**Fréquence** : 1 fois par jour

#### Étapes principales :

1. Chargement des transactions récentes
2. Calcul des métriques du modèle (F1-score)
3. Détection de dérive de performance
4. Déclenchement de l’API de réentraînement si seuil atteint
5. Notification par email

 **Objectif** : garantir un modèle fiable dans le temps

---

##  Supervision du modèle

* **Metric principale** : F1-score
* **Seuil critique** : F1 < 0.8
* **Action** : déclenchement automatique du retrain

 Le réentraînement est délégué à l’API-RETRAIN
 Le nouveau modèle est chargé dynamiquement par l’API-FRAUD

---

##  Déploiement avec Docker

Le fichier `docker-compose.yaml` permet de lancer :

* Airflow (scheduler + webserver)
* connexions S3, PostgreSQL, SMTP

### Lancement

```bash
docker-compose up -d
```

### Accès UI Airflow

```
http://localhost:8080
```

---

##  Connexions Airflow utilisées

* `aws_default` → AWS S3
* `neon_default` → PostgreSQL Neon
* `smtp_default` → Envoi d’emails
* Variables Airflow :

  * `S3BucketName`
  * `AIRTABLE_API_KEY`
  * `AIRTABLE_BASE_ID`

---

##  Bonnes pratiques implémentées

* Séparation des DAGs par responsabilité
* Utilisation de XCom pour le passage d’état
* Stockage des données brutes (data lineage)
* Monitoring automatisé du modèle
* Déclenchement conditionnel (BranchOperator)
* Architecture MLOps event-driven

---

##  Valeur ajoutée du projet

* Orchestration complète du cycle de vie des données
* Intégration Data + ML + BI
* Résilience face à la dérive du modèle
* Réduction des interventions manuelles
* Scalabilité horizontale possible

---
