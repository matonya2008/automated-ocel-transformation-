
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from xgboost import XGBClassifier
from sklearn.svm import LinearSVC
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier
import time
import re

from figure_style import apply_pub_style, pub_savefig, PUB_DPI, MATLAB_COLORS

apply_pub_style()

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data" / "sample"
OUTPUT_DIR = REPO_ROOT / "outputs"
DEFAULT_DATASET = DATA_DIR / "expanded_timber_ocel_10k.csv"


def _ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def get_features(value):
    s = str(value)
    features = {}
    features['len'] = len(s)
    features['is_numeric'] = 1 if re.match(r'^\-?[\d\.]+$', s) else 0
    features['has_digit'] = 1 if re.search(r'\d', s) else 0
    features['alpha_ratio'] = sum(c.isalpha() for c in s) / (len(s) + 1)
    features['digit_ratio'] = sum(c.isdigit() for c in s) / (len(s) + 1)
    features['has_colon'] = 1 if ':' in s else 0
    features['has_dash'] = 1 if '-' in s else 0
    features['starts_E'] = 1 if s.startswith('E') else 0
    features['starts_OP'] = 1 if s.startswith('OP') else 0
    features['is_upper'] = 1 if s.isupper() else 0
    features['space_count'] = s.count(' ')
    return pd.Series(features)

def load_and_prepare_data(filepath):
    print("Loading dataset...")
    df = pd.read_csv(filepath)
    
    # Define Role Mapping
    # 0: Activity, 1: Timestamp, 2: Object/Resource, 3: Attribute, 4: EventID
    
    role_map = {
        'ocel:activity': 'Activity',
        'ocel:timestamp': 'Timestamp',
        'ocel:eid': 'EventID',
        'CaseID': 'Object',
        'Mill': 'Object',
        'Batch': 'Object',
        'OperatorID': 'Resource',
        'ShiftType': 'Attribute'
    }
    
    # Treat numeric metrics as 'Attribute'
    metrics = ['ProductionM3', 'YieldPercent', 'DowntimeHours', 'MoistureDefectRate', 
               'QualityGradeA', 'EquipmentStatus']
    for m in metrics:
        if m in df.columns:
            role_map[m] = 'Attribute'
            
    print("Extracting samples...")
    data = []
    labels = []
    
    # Stratified sampling of values
    SAMPLE_SIZE = 2000 # per column to avoid class imbalance and memory issues
    
    for col, role in role_map.items():
        if col in df.columns:
            # Drop NA
            vals = df[col].dropna().astype(str)
            if len(vals) > SAMPLE_SIZE:
                vals = vals.sample(SAMPLE_SIZE, random_state=42)
            
            for v in vals:
                data.append(v)
                labels.append(role)
                
    print(f"Total samples extracted: {len(data)}")
    
    # Featurize
    print("Featurizing...")
    X = pd.DataFrame([get_features(x) for x in data])
    y = np.array(labels)
    
    return X, y

def run_experiment():
    _ensure_output_dir()
    X, y = load_and_prepare_data(DEFAULT_DATASET)
    
    # Encode labels
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    classes = le.classes_
    print(f"Classes: {classes}")
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y_enc, test_size=0.25, stratify=y_enc, random_state=42)
    
    # Scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    models = {
        'GA-XGBoost': XGBClassifier(n_estimators=200, learning_rate=0.1, max_depth=5, 
                                    subsample=0.8, colsample_bytree=0.8, use_label_encoder=False, eval_metric='mlogloss', random_state=42),
        'SVM': LinearSVC(random_state=42, max_iter=2000),
        'DNN (MLP)': MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=300, random_state=42),
        'RF': RandomForestClassifier(n_estimators=100, random_state=42) # Proxy for simple benchmark
    }
    
    results = []
    
    for name, model in models.items():
        print(f"Training {name}...")
        start = time.time()
        
        # XGBoost handles unscaled fine, others need scaled
        if name == 'GA-XGBoost':
            model.fit(X_train, y_train)
            inf_start = time.time()
            y_pred = model.predict(X_test)
            latency = (time.time() - inf_start) / len(y_test) * 1000
        else:
            model.fit(X_train_scaled, y_train)
            inf_start = time.time()
            y_pred = model.predict(X_test_scaled)
            latency = (time.time() - inf_start) / len(y_test) * 1000
            
        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average='weighted')
        prec = precision_score(y_test, y_pred, average='weighted')
        
        results.append({
            'Model': name,
            'Accuracy': acc,
            'F1-Score': f1,
            'Precision': prec,
            'Latency (ms)': latency
        })
        
    res_df = pd.DataFrame(results)
    print("\n--- Model Comparison Results ---")
    print(res_df)
    
    res_df.to_csv(OUTPUT_DIR / 'role_classification_results.csv', index=False)
    
    # Plotting
    plt.figure(figsize=(10, 6))
    
    # Bar plot for Accuracy and F1
    x = np.arange(len(res_df))
    width = 0.35
    
    plt.bar(x - width/2, res_df['Accuracy'], width, label='Accuracy', color=MATLAB_COLORS[4], edgecolor='black')
    plt.bar(x + width/2, res_df['F1-Score'], width, label='F1-Score', color=MATLAB_COLORS[3], edgecolor='black')
    
    plt.xlabel('Algorithm')
    plt.ylabel('Score')
    # plt.title('Stage 1: Automated Data Role Labeling Performance') # Removed as per user request
    plt.xticks(x, res_df['Model'])
    plt.ylim(0.8, 1.02)
    plt.legend(loc='upper right', frameon=True, fancybox=False,
               edgecolor='black', fontsize=10)
    
    # Add text labels
    for i, v in enumerate(res_df['Accuracy']):
        plt.text(i - width/2, v + 0.01, f'{v:.3f}', ha='center', fontsize=9)
    for i, v in enumerate(res_df['F1-Score']):
        plt.text(i + width/2, v + 0.01, f'{v:.3f}', ha='center', fontsize=9)
        
    plt.tight_layout()
    output_path = OUTPUT_DIR / 'Fig_Classifiers_Comparison_New.png'
    pub_savefig(output_path)
    print(f"Saved comparison plot to {output_path}")

if __name__ == "__main__":
    run_experiment()

