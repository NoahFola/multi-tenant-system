from google.cloud import firestore

def create_project(db, tenant_id: str, name: str, created_by: str) -> str:
    ref = db.collection("projects").document()
    ref.set({
        "tenant_id": tenant_id,
        "name": name,
        "created_by": created_by,
        "created_at": firestore.SERVER_TIMESTAMP,
    })
    return ref.id

def list_projects(db, tenant_id: str) -> list[dict]:
    docs = (
        db.collection("projects")
          .where(filter=firestore.FieldFilter("tenant_id", "==", tenant_id))
          .stream()
    )
    return [{"id": d.id, **d.to_dict()} for d in docs]
