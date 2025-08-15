# Congressional Data MCP Server - Deployment Guide

## Local Setup ✅ Complete

Your MCP server is now ready! The Congress.gov API is working perfectly, and the server is containerized with Docker.

## Claude Desktop Integration

To use this MCP server with Claude Desktop:

1. **Locate your Claude Desktop configuration file:**
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. **Add the MCP server configuration:**
   ```json
   {
     "mcpServers": {
       "congressional-data": {
         "command": "docker",
         "args": [
           "run",
           "--rm",
           "-i",
           "--env-file", "/Users/corytitus/Documents/GitHub/congress-mcp/congressional-data-mcp/.env",
           "congressional-data-mcp:latest",
           "python",
           "server.py"
         ]
       }
     }
   }
   ```

3. **Restart Claude Desktop** to load the new configuration.

## Cloud Deployment Options

### Option 1: Google Cloud Run (Recommended for Serverless)

1. **Build and push to Google Container Registry:**
   ```bash
   # Configure gcloud
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   
   # Build and push
   docker tag congressional-data-mcp:latest gcr.io/YOUR_PROJECT_ID/congressional-data-mcp
   docker push gcr.io/YOUR_PROJECT_ID/congressional-data-mcp
   ```

2. **Deploy to Cloud Run:**
   ```bash
   gcloud run deploy congressional-data-mcp \
     --image gcr.io/YOUR_PROJECT_ID/congressional-data-mcp \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars CONGRESS_GOV_API_KEY=YOUR_KEY,GOVINFO_API_KEY=YOUR_KEY
   ```

### Option 2: AWS ECS/Fargate

1. **Push to Amazon ECR:**
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ECR_URI
   docker tag congressional-data-mcp:latest YOUR_ECR_URI/congressional-data-mcp
   docker push YOUR_ECR_URI/congressional-data-mcp
   ```

2. **Create ECS task definition and service** (use AWS Console or Terraform)

### Option 3: Digital Ocean App Platform

1. **Push to Docker Hub:**
   ```bash
   docker tag congressional-data-mcp:latest YOUR_DOCKERHUB_USERNAME/congressional-data-mcp
   docker push YOUR_DOCKERHUB_USERNAME/congressional-data-mcp
   ```

2. **Create App in Digital Ocean:**
   - Use Docker Hub as source
   - Set environment variables
   - Configure health checks

### Option 4: Kubernetes (Any Cloud Provider)

1. **Create deployment.yaml:**
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: congressional-data-mcp
   spec:
     replicas: 2
     selector:
       matchLabels:
         app: congressional-data-mcp
     template:
       metadata:
         labels:
           app: congressional-data-mcp
       spec:
         containers:
         - name: mcp-server
           image: congressional-data-mcp:latest
           env:
           - name: CONGRESS_GOV_API_KEY
             valueFrom:
               secretKeyRef:
                 name: api-keys
                 key: congress
           - name: GOVINFO_API_KEY
             valueFrom:
               secretKeyRef:
                 name: api-keys
                 key: govinfo
   ```

## Environment Variables for Cloud

Make sure to set these in your cloud provider's secret management:

- `CONGRESS_GOV_API_KEY`: Your Congress.gov API key
- `GOVINFO_API_KEY`: Your GovInfo API key
- `REDIS_HOST`: (Optional) External Redis instance for caching
- `ENABLE_METRICS`: Set to "true" for monitoring

## Security Considerations

1. **Never commit API keys to version control**
2. **Use cloud provider's secret management** (AWS Secrets Manager, GCP Secret Manager, etc.)
3. **Enable authentication** for production deployments
4. **Set up rate limiting** to protect your API quotas
5. **Monitor usage** through the metrics endpoint

## Monitoring

The server exposes metrics at:
- Health check: `http://YOUR_HOST:8081/health`
- Prometheus metrics: `http://YOUR_HOST:9090`

## Support

For issues or questions, please open an issue on GitHub or contact the maintainer.