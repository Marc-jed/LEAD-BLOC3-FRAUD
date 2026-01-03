
#  MLFLOW-FRAUD – Tracking & Versioning du modèle

##  Objectif

Ce module est dédié au **suivi, au versioning et à l’évaluation des modèles de détection de fraude** via **MLflow**.

Il permet de :

* tracer les expériences de machine learning
* comparer les performances des modèles
* historiser les métriques et hyperparamètres
* versionner les modèles entraînés
* préparer les modèles à la mise en production

MLflow est utilisé comme **socle MLOps** du projet.

---

##  Rôle dans l’architecture globale

MLflow intervient dans le pipeline lors des phases :

* entraînement initial du modèle
* réentraînement automatique
* comparaison des performances (F1-score, Recall, Precision)
* stockage des artefacts de modèles
* traçabilité des décisions de réentraînement

 Les modèles validés sont ensuite exportés vers **AWS S3**
 Les APIs de prédiction chargent dynamiquement le dernier modèle disponible

---

##  Arborescence

```
MLFLOW-FRAUD/
│
├── Dockerfile
├── README.md
├── model.py
├── requirements.txt
```

---

##  Description des fichiers

### `model.py`

Script principal d’entraînement du modèle :

* Chargement des données
* Préprocessing (numérique + catégoriel)
* Entraînement du modèle (XGBoost)
* Évaluation sur jeu de test
* Log des métriques dans MLflow
* Sauvegarde du modèle entraîné

---

### `Dockerfile`

Permet de :

* déployer MLflow dans un environnement isolé
* assurer la cohérence des versions Python & librairies
* exposer l’UI MLflow pour le suivi des runs

---

### `requirements.txt`

Liste des dépendances ML :

* scikit-learn
* xgboost
* mlflow
* pandas
* numpy
* boto3
* joblib

---

##  Métriques suivies

Les principales métriques enregistrées dans MLflow sont :

* **F1-score** (métrique principale)
* **Recall**
* **Precision**

Ces métriques sont utilisées par :

* le DAG de monitoring du modèle
* la logique de déclenchement du réentraînement

---

##  Exemple de métriques observées

| Modèle       | F1-score | Precision | Recall   |
| ------------ | -------- | --------- | -------- |
| Logistic Reg | 0.09     | 0.05      | 0.87     |
| RandomForest | 0.77     | 0.84      | 0.70     |
| **XGBoost**  | **0.89** | **0.96**  | **0.83** |

 **XGBoost** a été retenu comme modèle de production.

---

##  Cycle de vie du modèle

1. Entraînement / réentraînement
2. Logging des résultats dans MLflow
3. Comparaison des runs
4. Export du modèle validé
5. Upload sur S3
6. Chargement dynamique par l’API de prédiction

---

##  Déploiement MLflow

### Lancement du service

```bash
docker build -t mlflow-fraud .
docker run -p 5000:5000 mlflow-fraud
```

### Accès à l’interface MLflow

```
http://localhost:5000
```

---

##  Bonnes pratiques MLOps appliquées

* Traçabilité complète des expériences
* Comparaison reproductible des modèles
* Séparation entraînement / prédiction
* Versioning explicite des modèles
* Déclenchement conditionnel du retrain
* Découplage MLflow ↔ API de production

---

##  Valeur ajoutée

* Vision claire de l’évolution des performances
* Réduction du risque de régression du modèle
* Base solide pour industrialiser le ML
* Approche orientée production & monitoring

---

