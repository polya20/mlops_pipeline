import argparse, os, pickle, yaml, subprocess
import numpy as np, pandas as pd
from sklearn.linear_model import LinearRegression

def setup_dvc():
    print("--- Pulling DVC versioned data ---")
    try:
        subprocess.run(["dvc", "pull", "--force"], check=True)
        print("DVC pull successful.")
    except Exception as e:
        print(f"DVC pull failed: {e}. This is expected if not in a Git repo with DVC.")

def train_model(config_path, data_path, model_dir):
    with open(config_path, 'r') as f: config = yaml.safe_load(f)
    df = pd.read_csv(data_path)
    country_data = df[df['country'] == config['country_name']].copy()
    X = np.log(country_data[['jackpot_announced']])
    y = np.log(country_data['tickets_sold'])
    model = LinearRegression()
    model.fit(X, y)
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "model.pkl")
    with open(model_path, "wb") as f: pickle.dump(model, f)
    print(f"Model saved to: {model_path}")

if __name__ == '__main__':
    setup_dvc()
    parser = argparse.ArgumentParser()
    # SageMaker passes hyperparams as args. We use one for the config file path.
    parser.add_argument('--config_s3_uri', type=str)
    # SageMaker provides these env vars.
    data_path = os.path.join(os.environ.get('SM_CHANNEL_TRAINING'), 'lottery_sales.csv.gz')
    model_output_dir = os.environ.get('SM_MODEL_DIR', 'models/')
    args = parser.parse_args()
    train_model(args.config_s3_uri, data_path, model_output_dir)