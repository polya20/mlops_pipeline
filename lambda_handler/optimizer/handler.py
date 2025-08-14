import os, boto3, json, pickle,yaml
from urllib.parse import urlparse
from src.optimise import find_optimal_jackpot

s3 = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')
ARTIFACT_BUCKET = os.environ['ARTIFACT_BUCKET']
LOCAL_TMP_DIR = "/tmp"

def lambda_handler(event, context):
    try:
        model_s3_path_full = event['model_s3_path']
        country = event['country']
        
        print(f"Starting optimization for {country}. Model path: {model_s3_path_full}")
        
        # Download model, config, and data from S3 to the /tmp directory
        parsed_path = urlparse(model_s3_path_full, allow_fragments=False)
        model_key = parsed_path.path.lstrip('/')
        local_model_path = os.path.join(LOCAL_TMP_DIR, "model.pkl")
        s3.download_file(parsed_path.netloc, model_key, local_model_path)
        
        local_config_path = os.path.join(LOCAL_TMP_DIR, f"{country}.yaml")
        local_data_path = os.path.join(LOCAL_TMP_DIR, "lottery_sales.csv.gz")
        s3.download_file(ARTIFACT_BUCKET, f"configs/{country}.yaml", local_config_path)
        s3.download_file(ARTIFACT_BUCKET, "data/lottery_sales.csv.gz", local_data_path)

        # Load config to get secret name
        with open(local_config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Securely fetch available cash from Secrets Manager
        secret_val = secrets_client.get_secret_value(SecretId=config['available_cash_secret_name'])
        available_cash = json.loads(secret_val['SecretString'])['cash']
        
        # Load the model
        with open(local_model_path, 'rb') as f:
            model = pickle.load(f)

        # Run the core optimization logic
        recommendation = find_optimal_jackpot(config, model, local_data_path, available_cash)
        
        return {
            'statusCode': 200,
            'body': json.dumps(recommendation)
        }
    except Exception as e:
        print(f"Error during optimization: {str(e)}")
        raise e