set -x

# Create Data Bucket (matches env.example S3_BUCKET_NAME)
DATA_BUCKET="crypto-dashboard-data"
awslocal s3api create-bucket --bucket $DATA_BUCKET

if [ -f "/etc/localstack/init/ready.d/cors-config.json" ]; then
    echo "CORS config file found, applying configuration..."
    awslocal s3api put-bucket-cors --bucket $DATA_BUCKET --cors-configuration file:///etc/localstack/init/ready.d/cors-config.json
else
    echo "CORS config file not found at expected location"
    ls -la /etc/localstack/init/ready.d/
fi

# Create Athena Results Bucket
ATHENA_BUCKET="crypto-athena-results"
awslocal s3api create-bucket --bucket $ATHENA_BUCKET

# Setup Athena
# Create database
echo "Creating Athena database..."
awslocal athena start-query-execution \
    --query-string "CREATE DATABASE IF NOT EXISTS crypto_archive" \
    --result-configuration "OutputLocation=s3://$ATHENA_BUCKET"

# Verify Buckets
echo "Verifying buckets:"
awslocal s3 ls

set +x
