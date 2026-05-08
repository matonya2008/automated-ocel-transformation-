
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
import re

from figure_style import apply_pub_style, pub_savefig, PUB_DPI, MATLAB_COLORS

apply_pub_style()

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data" / "sample"
OUTPUT_DIR = REPO_ROOT / "outputs"


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
    features['is_upper'] = 1 if s.isupper() else 0
    features['space_count'] = s.count(' ')
    return pd.Series(features)

def calculate_entropy(probs):
    eps = 1e-12
    return -np.sum(probs * np.log2(probs + eps), axis=1)

def evaluate_dataset(path, name, role_map):
    print(f"Evaluating {name} sector...")
    df = pd.read_csv(path)
    
    data = []
    labels = []
    SAMPLE_SIZE = 1000
    for col, role in role_map.items():
        if col in df.columns:
            vals = df[col].dropna().unique()
            if len(vals) > SAMPLE_SIZE:
                np.random.seed(42)
                vals = np.random.choice(vals, SAMPLE_SIZE, replace=False)
            for v in vals:
                data.append(v)
                labels.append(role)
    
    X = pd.DataFrame([get_features(x) for x in data])
    le = LabelEncoder()
    y = le.fit_transform(labels)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, stratify=y, random_state=42)
    
    model = XGBClassifier(n_estimators=100, learning_rate=0.1, max_depth=4, random_state=42)
    model.fit(X_train, y_train)
    
    probs = model.predict_proba(X_test)
    entropies = calculate_entropy(probs)
    y_pred = np.argmax(probs, axis=1)
    
    thresholds = np.linspace(0, 2.5, 60)
    accuracies = []
    for delta in thresholds:
        query_mask = entropies > delta
        final_preds = y_pred.copy()
        final_preds[query_mask] = y_test[query_mask]
        accuracies.append(np.mean(final_preds == y_test))
    
    return thresholds, accuracies

def run_cross_sector_validation():
    _ensure_output_dir()
    configs = [
        {
            'path': DATA_DIR / 'expanded_timber_ocel_10k.csv',
            'name': 'Synthetic Timber Sample',
            'role_map': {
                'ocel:activity': 'Activity', 'ocel:timestamp': 'Timestamp',
                'ocel:eid': 'EventID', 'CaseID': 'Object', 'OperatorID': 'Resource',
                'ProductionM3': 'Attribute', 'YieldPercent': 'Attribute'
            }
        },
        {
            'path': DATA_DIR / 'tube_logs_sample.csv',
            'name': 'Tube Manufacturing (Logs)',
            'role_map': {
                'Case ID': 'Object', 'Activity': 'Activity', 'Timestamp': 'Timestamp',
                'Object _type': 'Attribute', 'Attributes': 'Attribute'
            }
        },
        {
            'path': DATA_DIR / 'tube_sensor_sample.csv',
            'name': 'Tube Manufacturing (Sensors)',
            'role_map': {
                'ts_hour_tz': 'Timestamp', 'time_index': 'EventID',
                'S1_201': 'Attribute', 'S2_201': 'Attribute', 'S3_201': 'Attribute'
            }
        }
    ]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    markers = ['o', 's', '^']
    colors = [MATLAB_COLORS[0], MATLAB_COLORS[1], MATLAB_COLORS[4]]

    plotted = 0
    for idx, config in enumerate(configs):
        if not Path(config['path']).exists():
            print(f"  Skipping {config['name']}: dataset not found at {config['path']}")
            continue
        thresholds, accuracies = evaluate_dataset(config['path'], config['name'], config['role_map'])
        ax.plot(thresholds, accuracies, label=config['name'],
                color=colors[idx % len(colors)],
                marker=markers[idx % len(markers)], markersize=5.5,
                markerfacecolor='white', markeredgewidth=1.1,
                markevery=5, linewidth=2.0)
        print(f"  {config['name']} Baseline Accuracy (No queries): {accuracies[-1]:.4f}")
        plotted += 1

    if plotted == 0:
        raise FileNotFoundError(
            f"No sample datasets were found under {DATA_DIR}. "
            "Generate them first with scripts/generate_release_sample_data.py."
        )
    ax.set_xlabel(r'Entropy Threshold ($\delta$)')
    ax.set_ylabel('Role Assignment Accuracy')
    ax.legend(frameon=True, fancybox=False, edgecolor='black')
    ax.grid(True, linestyle=':', alpha=0.25)
    fig.tight_layout()
    output_path = OUTPUT_DIR / 'Fig_Scalability_Comparison.png'
    pub_savefig(fig, output_path)
    plt.close(fig)
    print(f"\nGenerated {output_path}")

if __name__ == "__main__":
    run_cross_sector_validation()
