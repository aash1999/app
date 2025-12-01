
import time
import uuid
from flask import Flask, request, jsonify
from datetime import datetime
import boto3
from urlExtractor import featureExtraction  # your feature extraction function
import os
app = Flask(__name__)

# ====== AWS SETTINGS ======
S3_BUCKET = "cc-final-project-sagemaker-dataset"
dynamodb = boto3.resource("dynamodb", region_name="us-east-2")
CACHE_TABLE = "UrlPredictionCache"
API_HITS_TABLE = "ApiHits"
cache_table = dynamodb.Table(CACHE_TABLE)
hits_table = dynamodb.Table(API_HITS_TABLE)

# ====== MODEL CACHE ======
MODEL_DIR = "./models"
os.makedirs(MODEL_DIR, exist_ok=True)
loaded_models = {}  # cache loaded models

# ====== EC2 INSTANCE ID ======
try:
    import requests
    EC2_INSTANCE_ID = requests.get("http://169.254.169.254/latest/meta-data/instance-id", timeout=1).text
except:
    EC2_INSTANCE_ID = "local-dev"

# ====== HELPER: Load model from S3 ======
# def load_model_from_s3(model_name):
#     import os, joblib, boto3
#     s3 = boto3.client("s3")
#     model_path = os.path.join(MODEL_DIR, model_name)
#     if model_name in loaded_models:
#         return loaded_models[model_name]
#     if not os.path.exists(model_path):
#         print("yes")
#         s3.download_file(S3_BUCKET, "models/"+model_name, model_path)
#     model = joblib.load(model_path)
#     loaded_models[model_name] = model
#     return model
def load_model_from_s3(model_name):
    s3 = boto3.client("s3")
    model_path = os.path.join(MODEL_DIR, model_name)

    # Return cached model if already loaded
    if model_name in loaded_models:
        return loaded_models[model_name]

    # Only download if missing locally
    if not os.path.exists(model_path):
        retries = 3
        delay = 0.1  # 100 ms

        for attempt in range(1, retries + 1):
            try:
                print(f"Downloading {model_name} from S3... Attempt {attempt}")
                s3.download_file(S3_BUCKET, f"models/{model_name}", model_path)
                break  # Success - exit retry loop
            except Exception as err:
                print(f"S3 download error: {err}")
                if attempt == retries:
                    raise  # No more retries, re-raise error
                time.sleep(delay)

    # Load model locally
    model = joblib.load(model_path)
    loaded_models[model_name] = model
    return model
# ======= /predict ROUTE =======
@app.route("/predict", methods=["POST"])
def predict_url():
    start_time = time.time()
    data = request.json
    url = data.get("url")
    model_name = data.get("model", "forest_model.pkl")

    if not url:
        return jsonify({"error": "URL missing"}), 400

    request_id = str(uuid.uuid4())

    try:
    # ---- Check cache ----
        cached = cache_table.get_item(Key={"url": url})
        if "Item" in cached:
            is_phishing = cached["Item"]["is_phishing"]
            source = "cache"
        else:
            model = load_model_from_s3(model_name)
            features = featureExtraction(url)
            pred = model.predict([features])[0]
            print("/////////////",pred)
            is_phishing = bool(pred)
            source = "model"
            # save to cache
            cache_table.put_item(Item={"url": url, "is_phishing": is_phishing})

        latency_ms = int((time.time() - start_time) * 1000)

        # ---- Log API hit ----
        hits_table.put_item(Item={
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "ec2_instance_id": EC2_INSTANCE_ID,
            "url": url,
            "model_used": model_name,
            "is_phishing": is_phishing,
            "latency_ms": latency_ms,
            "source": source
        })

        return jsonify({
            "url": url,
            "model_used": model_name,
            "is_phishing": is_phishing,
            "source": source,
            "latency_ms": latency_ms,
            "request_id": request_id
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ======= /feedback ROUTE =======
@app.route("/feedback", methods=["POST"])
def feedback():
    data = request.json
    request_id = data.get("request_id")  # Use request_id from predict response
    feedback_value = data.get("feedback")  # 1 = thumbs up, 0 = thumbs down

    if not request_id or feedback_value is None:
        return jsonify({"error": "Missing request_id or feedback"}), 400

    try:
        hits_table.update_item(
            Key={"request_id": request_id},
            UpdateExpression="SET feedback = :f",
            ExpressionAttributeValues={":f": int(feedback_value)}
        )
        return jsonify({"message": "Feedback saved successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

from flask import Flask, request, jsonify, render_template
# ... your existing imports

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")  # Flask will look inside 'templates' folder




if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)