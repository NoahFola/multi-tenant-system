import json
import yaml
from pathlib import Path
import sys

# Add services to path since they have hyphens in their directory names
sys.path.append(str(Path(__file__).parent.parent / "services" / "auth-service"))
from app.main import app as auth_app

sys.path.append(str(Path(__file__).parent.parent / "services" / "tenant-user-service"))
from app.main import app as tenant_app

def generate_openapi():
    # 1. Get the OpenAPI schema from the auth service
    openapi_schema = auth_app.openapi()
    
    # 2. Add some metadata for the unified platform
    openapi_schema["info"]["title"] = "Multi-Tenant Workflow Platform API"
    openapi_schema["info"]["version"] = "1.0.0"
    openapi_schema["info"]["description"] = "Unified OpenAPI specification for all microservices."
    
    # In the future, as we build tenant-user-service, workflow-service, etc.
    # we will merge their paths and components into this single schema.
    
    tenant_schema = tenant_app.openapi()
    # Merge paths
    if "paths" in tenant_schema:
        openapi_schema.setdefault("paths", {}).update(tenant_schema["paths"])
    # Merge components (like schemas)
    if "components" in tenant_schema and "schemas" in tenant_schema["components"]:
        openapi_schema.setdefault("components", {}).setdefault("schemas", {}).update(tenant_schema["components"]["schemas"])

    # 3. Write it out to docs/openapi.json
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)
    
    output_path_json = docs_dir / "openapi.json"
    with open(output_path_json, "w") as f:
        json.dump(openapi_schema, f, indent=2)
        
    # Also write yaml version just in case
    output_path_yaml = docs_dir / "openapi.yaml"
    with open(output_path_yaml, "w") as f:
        yaml.dump(openapi_schema, f, sort_keys=False)
        
    print(f"✅ Successfully generated {output_path_json} and {output_path_yaml}")

if __name__ == "__main__":
    generate_openapi()
