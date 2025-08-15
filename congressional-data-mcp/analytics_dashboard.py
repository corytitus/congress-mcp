#!/usr/bin/env python3
"""
Token Analytics Dashboard
Web-based dashboard for viewing token usage analytics and system health
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import asyncio

from fastapi import FastAPI, HTTPException, Depends, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from token_manager import get_token_manager
from token_models import TokenPermission

# Initialize token manager
token_manager = get_token_manager()

# Create FastAPI app for dashboard
dashboard_app = FastAPI(
    title="EnactAI Token Analytics Dashboard",
    version="1.0.0",
    description="Web dashboard for monitoring token usage and system health"
)

# Set up templates (we'll create simple embedded HTML)
templates = Jinja2Templates(directory="templates") if os.path.exists("templates") else None


class DashboardAuth:
    """Simple authentication for dashboard access."""
    
    @staticmethod
    async def verify_admin_token(request: Request):
        """Verify that the request has a valid admin token."""
        auth_header = request.headers.get("authorization")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        # Use token manager to verify admin access
        is_valid, message, token_data = token_manager.authenticate_token(
            authorization_header=auth_header,
            tool_name="dashboard",
            ip_address=request.client.host if request.client else None
        )
        
        if not is_valid:
            raise HTTPException(status_code=401, detail=message)
        
        if token_data.metadata.permissions != TokenPermission.ADMIN:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        return token_data


class AnalyticsEngine:
    """Analytics engine for generating insights from usage data."""
    
    def __init__(self):
        self.manager = token_manager
    
    def get_system_overview(self, hours: int = 24) -> Dict[str, Any]:
        """Get high-level system overview."""
        tokens = self.manager.list_tokens(include_inactive=True)
        analytics = self.manager.get_analytics(hours=hours)
        
        active_tokens = [t for t in tokens if t['is_active']]
        inactive_tokens = [t for t in tokens if not t['is_active']]
        
        # Calculate health metrics
        total_requests = analytics.get('total_requests', 0)
        error_rate = 0
        avg_response_time = 0
        
        # Get error rates from recent usage
        if total_requests > 0:
            error_count = 0
            total_response_time = 0
            response_count = 0
            
            for token in active_tokens:
                stats = self.manager.db.get_usage_stats(token['id'], hours)
                if stats and not stats.get('error'):
                    error_count += stats['total_requests'] - stats['successful_requests']
                    if stats['avg_response_time_ms']:
                        total_response_time += stats['avg_response_time_ms']
                        response_count += 1
            
            error_rate = error_count / total_requests if total_requests > 0 else 0
            avg_response_time = total_response_time / response_count if response_count > 0 else 0
        
        return {
            "period_hours": hours,
            "tokens": {
                "total": len(tokens),
                "active": len(active_tokens),
                "inactive": len(inactive_tokens),
                "revoked": len([t for t in inactive_tokens if t.get('revoked_at')])
            },
            "usage": {
                "total_requests": total_requests,
                "error_rate": error_rate,
                "avg_response_time_ms": avg_response_time
            },
            "top_tokens": analytics.get('recent_usage', [])[:5]
        }
    
    def get_token_details(self, token_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get detailed analytics for a specific token."""
        token_info = self.manager.get_token_info(token_id)
        if not token_info or 'error' in token_info:
            return {"error": "Token not found"}
        
        usage_stats = self.manager.db.get_usage_stats(token_id, hours)
        
        # Get usage timeline (hourly breakdown)
        timeline = self._get_usage_timeline(token_id, hours)
        
        return {
            "token_info": token_info,
            "usage_stats": usage_stats,
            "timeline": timeline
        }
    
    def _get_usage_timeline(self, token_id: str, hours: int) -> List[Dict[str, Any]]:
        """Get hourly usage timeline for a token."""
        # This would require more sophisticated database queries
        # For now, return a simplified version
        timeline = []
        current_time = datetime.now()
        
        for i in range(hours):
            hour_start = current_time - timedelta(hours=i+1)
            hour_end = current_time - timedelta(hours=i)
            
            # In a real implementation, we'd query the database for this specific hour
            # For now, simulate some data
            timeline.append({
                "hour": hour_start.strftime("%Y-%m-%d %H:00"),
                "requests": 0,  # Would be calculated from database
                "errors": 0,
                "avg_response_time": 0
            })
        
        return list(reversed(timeline))
    
    def get_security_alerts(self) -> List[Dict[str, Any]]:
        """Get security alerts and warnings."""
        alerts = []
        tokens = self.manager.list_tokens(include_inactive=False)
        
        # Check for tokens without expiration
        never_expire = [t for t in tokens if not t.get('expires_at')]
        if never_expire:
            alerts.append({
                "type": "warning",
                "title": "Tokens Without Expiration",
                "message": f"{len(never_expire)} tokens have no expiration date",
                "tokens": [t['name'] for t in never_expire[:5]]
            })
        
        # Check for unused tokens
        unused = [t for t in tokens if not t.get('last_used_at')]
        if unused:
            alerts.append({
                "type": "info",
                "title": "Unused Tokens",
                "message": f"{len(unused)} tokens have never been used",
                "tokens": [t['name'] for t in unused[:5]]
            })
        
        # Check for high-usage tokens
        analytics = self.manager.get_analytics(hours=24)
        high_usage = [t for t in analytics.get('recent_usage', []) if t['requests'] > 1000]
        if high_usage:
            alerts.append({
                "type": "info",
                "title": "High Usage Tokens",
                "message": f"{len(high_usage)} tokens exceeded 1000 requests in 24h",
                "tokens": [t['token_name'] for t in high_usage]
            })
        
        return alerts


# Initialize analytics engine
analytics_engine = AnalyticsEngine()


# Dashboard API endpoints

@dashboard_app.get("/")
async def dashboard_home():
    """Dashboard home page."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>EnactAI Token Analytics Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .metric { text-align: center; padding: 20px; border-radius: 8px; background: #f8f9fa; }
            .metric-value { font-size: 2em; font-weight: bold; color: #007bff; }
            .metric-label { color: #666; margin-top: 5px; }
            .alert { padding: 15px; border-radius: 5px; margin-bottom: 15px; }
            .alert-warning { background-color: #fff3cd; border-left: 4px solid #ffc107; }
            .alert-info { background-color: #d1ecf1; border-left: 4px solid #17a2b8; }
            .table { width: 100%; border-collapse: collapse; }
            .table th, .table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            .table th { background-color: #f8f9fa; }
            .btn { display: inline-block; padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
            .nav { display: flex; gap: 20px; margin-bottom: 20px; }
            .nav a { color: #007bff; text-decoration: none; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>EnactAI Token Analytics Dashboard</h1>
                <div class="nav">
                    <a href="/">Overview</a>
                    <a href="/api/tokens">Token Management</a>
                    <a href="/api/analytics">Analytics API</a>
                    <a href="/security">Security Alerts</a>
                </div>
            </div>
            
            <div class="card">
                <h2>System Overview</h2>
                <p>Welcome to the EnactAI Token Management Dashboard. Use the API endpoints below to access detailed analytics.</p>
                
                <h3>Available Endpoints</h3>
                <ul>
                    <li><strong>GET /api/overview</strong> - System overview metrics</li>
                    <li><strong>GET /api/tokens</strong> - List all tokens</li>
                    <li><strong>GET /api/tokens/{token_id}</strong> - Token details</li>
                    <li><strong>GET /api/analytics</strong> - Usage analytics</li>
                    <li><strong>GET /api/security</strong> - Security alerts</li>
                </ul>
                
                <h3>Authentication</h3>
                <p>All API endpoints require an admin token passed in the Authorization header:</p>
                <code>Authorization: Bearer your_admin_token_here</code>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@dashboard_app.get("/api/overview")
async def get_overview(
    hours: int = Query(24, description="Time period in hours"),
    auth_data = Depends(DashboardAuth.verify_admin_token)
):
    """Get system overview metrics."""
    overview = analytics_engine.get_system_overview(hours)
    return overview


@dashboard_app.get("/api/tokens")
async def get_tokens(
    include_inactive: bool = Query(False, description="Include inactive tokens"),
    auth_data = Depends(DashboardAuth.verify_admin_token)
):
    """Get list of all tokens."""
    tokens = token_manager.list_tokens(include_inactive=include_inactive)
    return {"tokens": tokens}


@dashboard_app.get("/api/tokens/{token_id}")
async def get_token_details(
    token_id: str,
    hours: int = Query(24, description="Time period for analytics"),
    auth_data = Depends(DashboardAuth.verify_admin_token)
):
    """Get detailed information about a specific token."""
    details = analytics_engine.get_token_details(token_id, hours)
    if "error" in details:
        raise HTTPException(status_code=404, detail=details["error"])
    return details


@dashboard_app.get("/api/analytics")
async def get_analytics(
    hours: int = Query(24, description="Time period in hours"),
    auth_data = Depends(DashboardAuth.verify_admin_token)
):
    """Get system-wide analytics."""
    analytics = token_manager.get_analytics(hours)
    return analytics


@dashboard_app.get("/api/security")
async def get_security_alerts(auth_data = Depends(DashboardAuth.verify_admin_token)):
    """Get security alerts and recommendations."""
    alerts = analytics_engine.get_security_alerts()
    return {"alerts": alerts}


@dashboard_app.post("/api/tokens/{token_id}/revoke")
async def revoke_token_endpoint(
    token_id: str,
    reason: str = Query("Revoked via dashboard"),
    auth_data = Depends(DashboardAuth.verify_admin_token)
):
    """Revoke a token."""
    success, message = token_manager.revoke_token(
        token_id, 
        revoked_by=f"dashboard-{auth_data.metadata.name}",
        reason=reason
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"success": True, "message": message}


@dashboard_app.get("/health")
async def dashboard_health():
    """Dashboard health check."""
    return {
        "status": "healthy",
        "service": "token-analytics-dashboard",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


# Utility function to run dashboard
def run_dashboard(host: str = "0.0.0.0", port: int = 8083):
    """Run the analytics dashboard."""
    print(f"Starting Token Analytics Dashboard on {host}:{port}")
    print(f"Dashboard URL: http://{host}:{port}")
    print("Note: Admin token required for API access")
    
    uvicorn.run(dashboard_app, host=host, port=port)


if __name__ == "__main__":
    # Run the dashboard
    port = int(os.getenv("DASHBOARD_PORT", "8083"))
    run_dashboard(port=port)