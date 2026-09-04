# backend/prediction/train.py

import numpy as np
import pandas as pd
import joblib
import os
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report,
)
from xgboost import XGBClassifier


MODEL_DIR = os.path.join(os.path.dirname(__file__), "models", "saved")


class ModelTrainer:
    """
    Trains and evaluates Logistic Regression, Random Forest, and XGBoost
    on the band activity prediction task.
    All models output probabilities, not hard 0/1 predictions.
    """

    def __init__(
        self,
        feature_names: list[str],
        model_dir: str = MODEL_DIR,
        random_state: int = 42,
    ):
        self.feature_names = feature_names
        self.model_dir     = model_dir
        self.random_state  = random_state
        os.makedirs(model_dir, exist_ok=True)
        self.models: dict[str, object] = {}

    def _get_X_y(self, df: pd.DataFrame):
        X = df[self.feature_names].values.astype(np.float32)
        y = df["label"].values.astype(np.int32)
        return X, y

    def _build_logistic(self):
        return LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            random_state=self.random_state,
        )

    def _build_random_forest(self):
        return RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            class_weight="balanced",
            random_state=self.random_state,
            n_jobs=-1,
        )

    def _build_xgboost(self):
        return XGBClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=3,
            eval_metric="logloss",
            random_state=self.random_state,
            verbosity=0,
        )

    def _evaluate(self, model, X_val, y_val, model_name: str) -> dict:
        y_prob = model.predict_proba(X_val)[:, 1]
        y_pred = (y_prob >= 0.5).astype(int)

        metrics = {
            "model":     model_name,
            "precision": precision_score(y_val, y_pred, zero_division=0),
            "recall":    recall_score(y_val, y_pred, zero_division=0),
            "f1":        f1_score(y_val, y_pred, zero_division=0),
            "roc_auc":   roc_auc_score(y_val, y_prob),
        }

        print(f"\n{'='*40}")
        print(f"Model: {model_name}")
        print(f"{'='*40}")
        print(f"  Precision : {metrics['precision']:.3f}")
        print(f"  Recall    : {metrics['recall']:.3f}   <- maps to Pd")
        print(f"  F1        : {metrics['f1']:.3f}")
        print(f"  ROC-AUC   : {metrics['roc_auc']:.3f}")
        print()
        print(classification_report(
            y_val, y_pred,
            target_names=["inactive", "active"],
            zero_division=0
        ))
        return metrics

    def train_all(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Train all three models on train_df, evaluate on val_df.
        Saves models to disk. Returns comparison DataFrame.
        """
        X_train, y_train = self._get_X_y(train_df)
        X_val,   y_val   = self._get_X_y(val_df)

        print(f"Training on {len(X_train)} examples")
        print(f"Validating on {len(X_val)} examples")
        print(f"Positive rate (train): {y_train.mean():.3f}")
        print(f"Positive rate (val):   {y_val.mean():.3f}")

        model_configs = [
            ("logistic",      self._build_logistic()),
            ("random_forest", self._build_random_forest()),
            ("xgboost",       self._build_xgboost()),
        ]

        all_metrics = []

        for name, model in model_configs:
            print(f"\nTraining {name}...")
            model.fit(X_train, y_train)
            metrics = self._evaluate(model, X_val, y_val, name)
            all_metrics.append(metrics)

            path = os.path.join(self.model_dir, f"{name}.joblib")
            joblib.dump(model, path)
            print(f"  Saved to {path}")
            self.models[name] = model

        comparison = pd.DataFrame(all_metrics).set_index("model")
        print(f"\n{'='*40}")
        print("COMPARISON SUMMARY")
        print(f"{'='*40}")
        print(comparison.to_string())
        return comparison

    def print_feature_importance(self, model_name: str) -> None:
        """Print feature importances for RF or XGBoost."""
        model = self.models.get(model_name)
        if model is None or not hasattr(model, "feature_importances_"):
            print(f"No feature importances for {model_name}")
            return

        importances = model.feature_importances_
        pairs = sorted(
            zip(self.feature_names, importances),
            key=lambda x: x[1],
            reverse=True,
        )
        print(f"\nFeature importance ({model_name}):")
        for name, imp in pairs:
            bar = "█" * int(imp * 40)
            print(f"  {name:<25} {imp:.3f}  {bar}")

    def load_model(self, name: str):
        """Load a saved model from disk."""
        path = os.path.join(self.model_dir, f"{name}.joblib")
        model = joblib.load(path)
        self.models[name] = model
        return model

    def best_model(self, comparison_df: pd.DataFrame, metric: str = "recall"):
        """Return (name, model) for the model with highest score on metric."""
        best_name = comparison_df[metric].idxmax()
        print(f"Best model by {metric}: {best_name}")
        return best_name, self.models[best_name]
