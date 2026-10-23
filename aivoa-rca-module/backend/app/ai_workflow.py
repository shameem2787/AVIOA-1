import os, json, re, uuid
from typing import TypedDict, Any
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

def _demo_extract(text: str, source_name: str):
    low=text.lower()
    batch=re.search(r"(?:batch(?:\s*(?:no|number|#))?\s*[:#-]?\s*)([A-Z0-9/-]{3,})", text, re.I)
    product=re.search(r"(?:product|api)\s*[:=-]\s*([^\n.;]+)", text, re.I)
    actual="Out-of-trend process result reported" if any(x in low for x in ["out of specification","oos","excursion","deviation","failed","outside limit"]) else "Observed result requires confirmation from source records"
    desc=text.strip()[:1400]
    return {
      "title":"AI-assisted API manufacturing deviation review",
      "deviation_id":"DEV-"+uuid.uuid4().hex[:6].upper(),
      "batch_number":batch.group(1).strip(".,;:") if batch else "Not provided",
      "product_name":product.group(1).strip() if product else "API product — confirm",
      "process_step":"Not explicitly identified — confirm",
      "incident_date":"Not provided",
      "severity":"Major",
      "description":desc,
      "expected_result":"Applicable approved specification / process parameter not included in source; verify against controlled record.",
      "actual_result":actual,
      "immediate_actions":"Confirm batch status and apply site-approved containment procedures; document actions already taken. Do not infer actions were completed.",
      "impact_assessment":"Potential batch/product impact cannot be concluded from the supplied information. Assess affected batch, adjacent batches, downstream processing, and patient/product quality risk.",
      "timeline":"Build a verified timeline from batch records, equipment logs, laboratory records, and operator entries.",
      "evidence":[{"id":"E1","label":source_name or "Incident report","excerpt":text.strip()[:650],"source":source_name or "Incident report","page":None,"relevance":"Primary source"}],
      "ai_summary":"Demo-mode extraction: review all fields and provide supporting records before concluding the investigation. No root cause is confirmed.",
    }

def _json_from_text(content):
    if isinstance(content, list): content="".join(str(x) for x in content)
    s=str(content).strip()
    s=re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.I)
    try: return json.loads(s)
    except Exception:
        m=re.search(r"\{.*\}",s,re.S)
        if m: return json.loads(m.group(0))
        raise ValueError("The AI response was not valid JSON")

def _call_json(system, user):
    key=os.getenv("GROQ_API_KEY", "").strip()
    if not key: return None
    llm=ChatGroq(api_key=key, model=MODEL, temperature=0.1, max_tokens=4500)
    msg=llm.invoke([SystemMessage(content=system),HumanMessage(content=user)])
    return _json_from_text(msg.content)

class RCAState(TypedDict, total=False):
    text: str; source_name: str; extracted: dict; analysis: dict; capa: dict; mode: str

def extract_node(state: RCAState):
    system="""You are an assistant to qualified pharmaceutical API quality investigators. Extract only facts supported by source text. Never invent dates, batch IDs, values, completed actions, or conclusions. Use 'Not provided' when absent. Return ONLY valid JSON with keys: title,deviation_id,batch_number,product_name,process_step,incident_date,severity,description,expected_result,actual_result,immediate_actions,impact_assessment,timeline,evidence,ai_summary. evidence is an array of {id,label,excerpt,source,page,relevance}. Keep uncertainty explicit. severity one of Critical, Major, Minor, To be assessed. Do not claim a root cause."""
    try:
        result=_call_json(system, f"Source name: {state.get('source_name','Incident report')}\nIncident material:\n{state['text']}")
        if result is None:
            result=_demo_extract(state['text'],state.get('source_name','Incident report')); mode="demo"
        else:
            result.setdefault("evidence",[])
            if not result["evidence"]: result["evidence"]=[{"id":"E1","label":state.get('source_name','Incident report'),"excerpt":state['text'][:650],"source":state.get('source_name','Incident report'),"page":None,"relevance":"Primary source"}]
            mode="groq"
    except Exception as e:
        result=_demo_extract(state['text'],state.get('source_name','Incident report'))
        result["ai_summary"]="AI provider was unavailable or returned an invalid response; deterministic demo extraction used. Review all fields. Details: "+str(e)[:180]
        mode="fallback"
    return {"extracted":result,"mode":mode}

def investigate_node(state: RCAState):
    base={"five_whys":[],"fishbone":{"People":[],"Method":[],"Machine":[],"Material":[],"Measurement":[],"Environment":[]},"root_causes":[],"evidence_gaps":["Approved batch manufacturing record and actual parameter values","Relevant equipment calibration / maintenance records","Raw-material identity, lot, and certificate-of-analysis records where applicable","Analytical chromatograms / laboratory raw data and system suitability where applicable","Operator interview and contemporaneous entries","Impact assessment for other batches and downstream operations"],"investigation_method":"5 Whys"}
    try:
        result=_call_json("""You support a pharmaceutical API quality investigator. Use only evidence in the supplied incident. Return JSON keys five_whys (up to 5 objects {question,answer,evidence_ids}), fishbone (People,Method,Machine,Material,Measurement,Environment arrays), root_causes (array of {id,category,cause,rationale,evidence_ids,confidence,status}), evidence_gaps (array of specific missing evidence), investigation_method. Every cause is a hypothesis unless directly evidenced; set status to Hypothesis and confidence Low/Medium/High. Never invent facts. If evidence is insufficient, say so. Five Whys may stop early rather than fabricate causal links.""", json.dumps(state.get("extracted",{})))
        if result: base.update(result)
    except Exception: pass
    if not base["five_whys"]:
        base["five_whys"]=[{"question":"Why was a deviation recorded?","answer":"The source describes an observed event or result requiring investigation; verify the exact event against the original record.","evidence_ids":["E1"]},{"question":"Why did the event occur?","answer":"Not established from the supplied evidence. Review contemporaneous process and equipment records.","evidence_ids":[]},{"question":"What system condition may have contributed?","answer":"Undetermined; evaluate procedure, equipment, material, measurement, people, and environment without presuming a cause.","evidence_ids":[] }]
        base["root_causes"]=[{"id":"RC1","category":"Method","cause":"Potential gap in execution or control of the approved process (unconfirmed)","rationale":"A hypothesis to evaluate only if batch records, interviews, or procedure review support it.","evidence_ids":[],"confidence":"Low","status":"Hypothesis"}]
    if not base.get("evidence_gaps"): base["evidence_gaps"]=[]
    return {"analysis":base}

def capa_node(state: RCAState):
    fallback={"capa_actions":[{"id":"CAPA1","type":"Corrective","action":"Document immediate containment and verify current batch status under approved site procedures.","rationale":"Protects product and preserves an auditable response while the investigation proceeds.","owner":"Quality Assurance","due_date":"","status":"Proposed","success_criteria":"Containment decision and batch status documented and reviewed."},{"id":"CAPA2","type":"Preventive","action":"After root cause confirmation, implement a risk-proportionate control or process improvement linked to the verified cause.","rationale":"Prevention must address the confirmed cause rather than an unsupported assumption.","owner":"Process owner","due_date":"","status":"Proposed","success_criteria":"Approved change implemented with training / documentation where applicable."},{"id":"CAPA3","type":"Effectiveness check","action":"Define an effectiveness check using an approved period or number of subsequent batches after implementation.","rationale":"Verifies that recurrence has been reduced and the action is effective.","owner":"Quality Assurance","due_date":"","status":"Proposed","success_criteria":"Predefined acceptance criteria met and evidence reviewed."}]}
    try:
        result=_call_json("""You support a pharmaceutical API quality investigator. Return JSON {capa_actions:[{id,type,action,rationale,owner,due_date,status,success_criteria}]}. Provide 2-4 risk-proportionate suggestions. Types: Corrective, Preventive, Effectiveness check. Do not invent a confirmed root cause, specific due dates, or claim an action has happened. Leave due_date blank if unknown and status Proposed. Recommendations require qualified human review.""", json.dumps({"extracted":state.get("extracted"),"analysis":state.get("analysis")}))
        if result and result.get("capa_actions"): return {"capa":result}
    except Exception: pass
    return {"capa":fallback}

def build_graph():
    g=StateGraph(RCAState)
    g.add_node("extract",extract_node); g.add_node("investigate",investigate_node); g.add_node("capa",capa_node)
    g.set_entry_point("extract"); g.add_edge("extract","investigate"); g.add_edge("investigate","capa"); g.add_edge("capa",END)
    return g.compile()

workflow=build_graph()
def analyze_incident(text: str, source_name: str="Incident report") -> dict:
    result=workflow.invoke({"text":text,"source_name":source_name})
    extracted=result.get("extracted",{})
    extracted.update(result.get("analysis",{}))
    extracted.update(result.get("capa",{}))
    extracted["ai_mode"]=result.get("mode","groq" if os.getenv("GROQ_API_KEY") else "demo")
    return extracted
