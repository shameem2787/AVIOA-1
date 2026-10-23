import os, json, uuid
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pypdf import PdfReader
from io import BytesIO
from .database import init_db, SessionLocal, InvestigationRecord, serialize_record
from .schemas import AnalyzeTextRequest, Investigation, ReviewRequest
from .ai_workflow import analyze_incident, _demo_extract

app=FastAPI(title="AIVOA.AI RCA API", version="1.0.0", description="AI-assisted pharmaceutical API manufacturing root cause analysis prototype")
origins=[x.strip() for x in os.getenv("CORS_ORIGINS","http://localhost:5173,http://127.0.0.1:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
@app.on_event("startup")
def startup(): init_db()
def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()
def now(): return datetime.now(timezone.utc).isoformat()
def prepare_payload(payload):
    payload.setdefault("title","AI-assisted API manufacturing deviation review")
    payload.setdefault("status","Draft"); payload.setdefault("evidence",[]); payload.setdefault("five_whys",[]); payload.setdefault("fishbone",{}); payload.setdefault("root_causes",[]); payload.setdefault("evidence_gaps",[]); payload.setdefault("capa_actions",[])
    payload.setdefault("created_at",now()); payload["updated_at"]=now()
    return payload

@app.get("/api/health")
def health(): return {"status":"ok","service":"AIVOA.AI RCA API","ai_provider":"Groq configured" if os.getenv("GROQ_API_KEY","").strip() else "Demo mode (no API key)","model":os.getenv("GROQ_MODEL","llama-3.3-70b-versatile")}
@app.get("/api/rca")
def list_rca(db:Session=Depends(get_db)):
    rows=db.query(InvestigationRecord).order_by(InvestigationRecord.updated_at.desc()).all()
    return [serialize_record(r) for r in rows]
@app.get("/api/rca/{record_id}")
def get_rca(record_id:int,db:Session=Depends(get_db)):
    row=db.get(InvestigationRecord,record_id)
    if not row: raise HTTPException(404,"Investigation not found")
    return serialize_record(row)
@app.post("/api/rca/analyze")
async def analyze_text(body:AnalyzeTextRequest):
    try: return prepare_payload(analyze_incident(body.text,body.source_name))
    except Exception as e: raise HTTPException(502,"Analysis failed: "+str(e)[:250])
@app.post("/api/rca/analyze-file")
async def analyze_file(file:UploadFile=File(...)):
    name=file.filename or "uploaded file"
    content=await file.read()
    if len(content)>12*1024*1024: raise HTTPException(413,"File exceeds 12 MB limit")
    ext=name.lower().rsplit(".",1)[-1] if "." in name else ""
    if ext=="pdf" or file.content_type=="application/pdf":
        try:
            reader=PdfReader(BytesIO(content)); text="\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception as e: raise HTTPException(400,"Could not read PDF: "+str(e)[:160])
        if not text.strip(): raise HTTPException(400,"No selectable text found. For scanned PDFs, paste OCR text instead.")
    elif ext in ("txt","eml","md","csv") or (file.content_type or "").startswith("text/"):
        text=content.decode("utf-8",errors="replace")
    else: raise HTTPException(415,"Supported files: text-based PDF, TXT, EML, MD, CSV")
    if len(text)>100000: text=text[:100000]
    try: return prepare_payload(analyze_incident(text,name))
    except Exception as e: raise HTTPException(502,"Analysis failed: "+str(e)[:250])
@app.post("/api/rca",status_code=201)
def create_rca(body:Investigation,db:Session=Depends(get_db)):
    data=body.model_dump(mode="json",exclude={"id","created_at","updated_at"})
    row=InvestigationRecord(title=data.get("title") or "Untitled investigation",status=data.get("status","Draft"),batch_number=data.get("batch_number", ""),product_name=data.get("product_name", ""),data_json=json.dumps(data),created_at=datetime.now(timezone.utc),updated_at=datetime.now(timezone.utc))
    db.add(row); db.commit(); db.refresh(row)
    return serialize_record(row)
@app.put("/api/rca/{record_id}")
def update_rca(record_id:int,body:Investigation,db:Session=Depends(get_db)):
    row=db.get(InvestigationRecord,record_id)
    if not row: raise HTTPException(404,"Investigation not found")
    data=body.model_dump(mode="json",exclude={"id","created_at","updated_at"})
    row.title=data.get("title") or row.title; row.status=data.get("status",row.status); row.batch_number=data.get("batch_number",""); row.product_name=data.get("product_name",""); row.data_json=json.dumps(data); row.updated_at=datetime.now(timezone.utc)
    db.commit(); db.refresh(row); return serialize_record(row)
@app.post("/api/rca/{record_id}/investigate")
def re_investigate(record_id:int,db:Session=Depends(get_db)):
    row=db.get(InvestigationRecord,record_id)
    if not row: raise HTTPException(404,"Investigation not found")
    data=json.loads(row.data_json); source="\n".join([data.get("description", ""),data.get("expected_result", ""),data.get("actual_result", ""),data.get("impact_assessment", "")])
    result=analyze_incident(source,"Saved investigation")
    for k in ("five_whys","fishbone","root_causes","evidence_gaps","capa_actions","ai_summary","ai_mode"): data[k]=result.get(k,data.get(k))
    row.data_json=json.dumps(data); row.updated_at=datetime.now(timezone.utc); db.commit(); db.refresh(row); return serialize_record(row)
@app.post("/api/rca/{record_id}/capa")
def regenerate_capa(record_id:int,db:Session=Depends(get_db)):
    row=db.get(InvestigationRecord,record_id)
    if not row: raise HTTPException(404,"Investigation not found")
    data=json.loads(row.data_json); source="\n".join([data.get("description", ""),json.dumps(data.get("root_causes",[])),json.dumps(data.get("evidence_gaps",[]))])
    result=analyze_incident(source,"CAPA recommendation context")
    data["capa_actions"]=result.get("capa_actions",data.get("capa_actions",[])); row.data_json=json.dumps(data); row.updated_at=datetime.now(timezone.utc); db.commit(); db.refresh(row); return serialize_record(row)
@app.post("/api/rca/{record_id}/review")
def review_rca(record_id:int,body:ReviewRequest,db:Session=Depends(get_db)):
    row=db.get(InvestigationRecord,record_id)
    if not row: raise HTTPException(404,"Investigation not found")
    data=json.loads(row.data_json); data["reviewer"]=body.reviewer; data["review_notes"]=body.notes; data["status"]=body.decision; data.setdefault("review_events",[]).append({"reviewer":body.reviewer,"decision":body.decision,"notes":body.notes,"timestamp":now()})
    row.status=body.decision; row.data_json=json.dumps(data); row.updated_at=datetime.now(timezone.utc); db.commit(); db.refresh(row); return serialize_record(row)
