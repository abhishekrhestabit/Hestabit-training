import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

class TitanicFeatureCreator(BaseEstimator, TransformerMixin):
    def __init__(self):
        pass

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        df = X.copy()
        
        # Ensure numeric columns are actually numeric
        cols_to_numeric = ['Age', 'Fare', 'SibSp', 'Parch', 'Pclass']
        for col in cols_to_numeric:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Defaults for missing data
        df['Fare'] = df['Fare'].fillna(14.45)
        df['Age'] = df['Age'].fillna(28.0)
        df['SibSp'] = df['SibSp'].fillna(0)
        df['Parch'] = df['Parch'].fillna(0)

        # --- MATH LOGIC ---
        df['FamilySize'] = df['SibSp'] + df['Parch'] + 1
        df['IsAlone'] = (df['FamilySize'] == 1).astype(int)
        
        df['Fare_Log'] = np.log1p(df['Fare'])
        df['Fare_Per_Person'] = df['Fare'] / df['FamilySize']
        
        df['Is_Child'] = (df['Age'] < 10).astype(int)
        df['Is_Senior'] = (df['Age'] > 60).astype(int)
        
        df['Age_Class'] = df['Age'] * df['Pclass']
        df['Age_Fare'] = df['Age'] * df['Fare_Log']
        df['Age_Sq'] = df['Age'] ** 2
        df['Fare_Sq'] = df['Fare_Log'] ** 2
        
        # Binary encodings for best_model.pkl compatibility
        # Create Sex_male and Pclass_3 as binary features
        df['Sex_male'] = (df['Sex'] == 'male').astype(int)
        df['Pclass_3'] = (df['Pclass'] == 3).astype(int)
        
        return df