from google.cloud import firestore

def create_tenant(db, name: str, batch=None) -> str:
    """Create a TENANTS document; return tenant_id."""
    doc_ref = db.collection("tenants").document()
    data = {
        "name": name,
        "status": "active",
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    if batch:
        batch.set(doc_ref, data)
    else:
        doc_ref.set(data)
    return doc_ref.id

def seed_roles(db, tenant_id: str, batch=None) -> dict[str, str]:
    """
    Create the three system roles for a new tenant.
    Returns {"employee": role_id, "manager": role_id, "admin": role_id}.
    Permissions:
      employee: ["workflow:submit"]
      manager:  ["workflow:submit", "workflow:review",
                 "workflow:approve", "workflow:reject"]
      admin:    all of the above plus ["user:invite", "user:list",
                "user:role_change", "user:disable"]
    """
    roles_ref = db.collection("roles")
    
    roles_data = {
        "employee": {
            "tenant_id": tenant_id,
            "name": "employee",
            "permissions": ["workflow:submit"],
            "is_system": True,
        },
        "manager": {
            "tenant_id": tenant_id,
            "name": "manager",
            "permissions": ["workflow:submit", "workflow:review", "workflow:approve", "workflow:reject"],
            "is_system": True,
        },
        "admin": {
            "tenant_id": tenant_id,
            "name": "admin",
            "permissions": ["workflow:submit", "workflow:review", "workflow:approve", "workflow:reject",
                            "user:invite", "user:list", "user:role_change", "user:disable"],
            "is_system": True,
        }
    }
    
    role_ids = {}
    local_batch = batch if batch else db.batch()
    
    for role_name, data in roles_data.items():
        doc_ref = roles_ref.document()
        local_batch.set(doc_ref, data)
        role_ids[role_name] = doc_ref.id
        
    if not batch:
        local_batch.commit()
    return role_ids
