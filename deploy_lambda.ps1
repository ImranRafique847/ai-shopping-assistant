# deploy_lambda.ps1 — Packages and deploys Lambda function
# Run this from Kiro terminal: .\deploy_lambda.ps1

$FUNCTION_NAME = "ai-shopping-assistant"
$REGION = "us-east-1"
$ROLE_ARN = "" # Will be filled after creating lambda-app-role

Write-Host "=== Step 1: Installing dependencies ===" -ForegroundColor Green
New-Item -ItemType Directory -Force -Path "lambda_package" | Out-Null
pip install boto3 faiss-cpu numpy --target lambda_package --quiet

Write-Host "=== Step 2: Copying function code ===" -ForegroundColor Green
Copy-Item "lambda_function.py" "lambda_package/"

Write-Host "=== Step 3: Creating zip package ===" -ForegroundColor Green
Compress-Archive -Path "lambda_package\*" -DestinationPath "lambda_package.zip" -Force

Write-Host "=== Step 4: Uploading to S3 ===" -ForegroundColor Green
aws s3 cp lambda_package.zip s3://ebay-restore-data/lambda/lambda_package.zip

Write-Host "=== Done! ===" -ForegroundColor Green
Write-Host "lambda_package.zip is ready and uploaded to S3"
Write-Host "Next: Create Lambda function in AWS Console"
