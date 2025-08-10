import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import pickle
import os
import yaml
import argparse

def train_model(config_path: str, model_dir: str = 'models/'):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    df = pd.read_csv(config['data_path'])
    country_data = df[df['country'] == config['country_name']]

    X = np.log(country_data[['jackpot_announced']])
    y = np.log(country_data['tickets_sold'])

    model = LinearRegression()
    model.fit(X, y)

    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, f"{config['country_name']}_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    
    print(f"Model for {config['country_name']} saved to: {model_path}")
    return model_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True, help='Path to the country config YAML file.')
    # SageMaker provides this environment variable
    model_output_dir = os.environ.get('SM_MODEL_DIR', 'models/')
    args = parser.parse_args()
    train_model(args.config, model_output_dir)