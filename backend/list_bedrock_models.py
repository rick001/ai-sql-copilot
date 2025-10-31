#!/usr/bin/env python3
"""
Standalone script to list all available AWS Bedrock models.
Shows which models you have access to and their details.

Usage:
    python list_bedrock_models.py
    # Or set environment variables:
    AWS_REGION=us-east-1 python list_bedrock_models.py
    
Note: Requires boto3. If running locally, install with:
    pip3 install boto3
Or run inside Docker container where dependencies are installed.
"""

import os
import sys

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    print("❌ Error: boto3 is not installed.", file=sys.stderr)
    print("", file=sys.stderr)
    print("Install it with:", file=sys.stderr)
    print("  pip3 install boto3", file=sys.stderr)
    print("", file=sys.stderr)
    print("Or run this script inside the Docker container:", file=sys.stderr)
    print("  docker compose -f infra/docker-compose.yml exec backend python3 list_bedrock_models.py", file=sys.stderr)
    sys.exit(1)

from typing import Dict, List, Optional

def load_settings():
    """Load settings from environment variables or .env file"""
    region = os.getenv("AWS_REGION", "us-east-1")
    return region

def list_bedrock_models(region: str = "us-east-1") -> List[Dict]:
    """
    List all available Bedrock foundation models.
    
    Args:
        region: AWS region to check
        
    Returns:
        List of model dictionaries with details
    """
    try:
        # Create Bedrock client (for listing models, we need bedrock service, not bedrock-runtime)
        bedrock = boto3.client(
            "bedrock",
            region_name=region,
            config=Config(retries={"max_attempts": 3})
        )
        
        # List foundation models
        response = bedrock.list_foundation_models()
        models = response.get("modelSummaries", [])
        
        # Filter and format model information
        formatted_models = []
        for model in models:
            formatted_models.append({
                "modelId": model.get("modelId", "N/A"),
                "modelName": model.get("modelName", "N/A"),
                "providerName": model.get("providerName", "N/A"),
                "inputModalities": model.get("inputModalities", []),
                "outputModalities": model.get("outputModalities", []),
                "inferenceTypesSupported": model.get("inferenceTypesSupported", []),
                "customizationsSupported": model.get("customizationsSupported", []),
                "lifecycleStatus": model.get("lifecycleStatus", "N/A"),
            })
        
        return formatted_models
        
    except NoCredentialsError:
        print("❌ Error: AWS credentials not found.", file=sys.stderr)
        print("   Please configure AWS credentials:", file=sys.stderr)
        print("   - Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables", file=sys.stderr)
        print("   - Or run 'aws configure'", file=sys.stderr)
        print("   - Or ensure your EC2 instance has an IAM role with Bedrock permissions", file=sys.stderr)
        sys.exit(1)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        
        if error_code == "AccessDeniedException":
            print(f"❌ Error: Access denied. {error_msg}", file=sys.stderr)
            print("   Your AWS credentials need 'bedrock:ListFoundationModels' permission.", file=sys.stderr)
        else:
            print(f"❌ AWS Error ({error_code}): {error_msg}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

def check_model_access(region: str = "us-east-1", model_id: Optional[str] = None) -> bool:
    """
    Check if we can access a specific model (or any model if model_id is None).
    
    Args:
        region: AWS region
        model_id: Optional model ID to test
        
    Returns:
        True if accessible, False otherwise
    """
    if not model_id:
        # Just check if we can list models
        try:
            bedrock = boto3.client("bedrock", region_name=region)
            bedrock.list_foundation_models()
            return True
        except:
            return False
    
    # Check specific model by trying to invoke it (dry run)
    try:
        bedrock_runtime = boto3.client("bedrock-runtime", region_name=region)
        # For Claude models, we can check model access via Converse API
        # But that's expensive, so we'll just check if it's in the list
        return True
    except:
        return False

def print_models_table(models: List[Dict], highlight_model: Optional[str] = None):
    """Print models in a nice table format"""
    if not models:
        print("No models found.")
        return
    
    print(f"\n{'='*100}")
    print(f"Available AWS Bedrock Models (Total: {len(models)})")
    print(f"{'='*100}\n")
    
    # Group by provider
    by_provider: Dict[str, List[Dict]] = {}
    for model in models:
        provider = model.get("providerName", "Unknown")
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(model)
    
    # Print by provider
    for provider in sorted(by_provider.keys()):
        provider_models = by_provider[provider]
        print(f"\n📦 {provider} ({len(provider_models)} models)")
        print("-" * 100)
        
        for model in provider_models:
            model_id = model.get("modelId", "N/A")
            model_name = model.get("modelName", "N/A")
            lifecycle = model.get("lifecycleStatus", "N/A")
            
            # Highlight if it matches configured model
            marker = " ⭐ " if highlight_model and highlight_model in model_id else "   "
            
            print(f"{marker}Model ID: {model_id}")
            print(f"   Name: {model_name}")
            print(f"   Status: {lifecycle}")
            
            # Show input/output modalities
            input_mods = model.get("inputModalities", [])
            output_mods = model.get("outputModalities", [])
            if input_mods or output_mods:
                mods = []
                if input_mods:
                    mods.append(f"Input: {', '.join(input_mods)}")
                if output_mods:
                    mods.append(f"Output: {', '.join(output_mods)}")
                print(f"   {' | '.join(mods)}")
            
            # Show inference types
            inference_types = model.get("inferenceTypesSupported", [])
            if inference_types:
                print(f"   Inference Types: {', '.join(inference_types)}")
            
            print()

def main():
    """Main function"""
    region = load_settings()
    
    print("🔍 Checking AWS Bedrock models...")
    print(f"   Region: {region}")
    
    # Get configured model ID from environment
    configured_model = os.getenv("BEDROCK_MODEL_ID", None)
    if configured_model:
        print(f"   Configured Model: {configured_model}")
    
    print()
    
    models = list_bedrock_models(region)
    
    if models:
        print_models_table(models, highlight_model=configured_model)
        
        # Summary
        print(f"\n{'='*100}")
        print("Summary:")
        print(f"  • Total models: {len(models)}")
        
        providers = set(m.get("providerName", "Unknown") for m in models)
        print(f"  • Providers: {', '.join(sorted(providers))}")
        
        # Find Claude models specifically
        claude_models = [m for m in models if "claude" in m.get("modelId", "").lower()]
        if claude_models:
            print(f"  • Claude models: {len(claude_models)}")
            print("    Recommended for this project:")
            for m in claude_models[:5]:  # Show first 5
                print(f"      - {m.get('modelId')}")
        
        # Check if configured model is available
        if configured_model:
            available = any(configured_model in m.get("modelId", "") for m in models)
            if available:
                print(f"\n✅ Configured model '{configured_model}' is available!")
            else:
                print(f"\n⚠️  Configured model '{configured_model}' not found in available models.")
                print("   You may need to request access in the AWS Bedrock console.")
    else:
        print("No models found. This might indicate:")
        print("  1. No AWS credentials configured")
        print("  2. No permissions to list Bedrock models")
        print("  3. No models available in your region/account")
        print("  4. Model access not enabled in Bedrock console")

if __name__ == "__main__":
    main()

