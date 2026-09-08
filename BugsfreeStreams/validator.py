"""Fast unified stream health validator."""
from __future__ import annotations
import concurrent.futures,json,os,re,threading,time
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import parse_qsl,urlencode,urljoin,urlparse,urlunparse
import requests
ROOT=Path("LiveTV");OUT=Path("BugsfreeStreams/Output")
TIMEOUT=float(os.getenv("STREAM_TIMEOUT","6"));HEAD_TIMEOUT=float(os.getenv("STREAM_HEAD_TIMEOUT","4"));WORKERS=int(os.getenv("STREAM_WORKERS","32"));RETRIES=int(os.getenv("STREAM_RETRIES","1"));MAX_PER_HOST=int(os.getenv("STREAM_MAX_PER_HOST","8"));SKIP_HEAD_MEDIA=os.getenv("STREAM_SKIP_HEAD_FOR_MEDIA","0") in {"1","true","yes"}
HEADERS={"User-Agent":"LiveTVCollector-Health/2.0","Accept":"*/*"};TRACKING_PARAMS={"utm_source","utm_medium","utm_campaign","utm_content","utm_term"};TRANSIENT_STATUSES={408,425,429,500,502,503,504}
_tls=threading.local();_gates={};_gate_lock=threading.Lock()
def session():
 s=getattr(_tls,"session",None)
 if s is None:
  s=requests.Session();s.headers.update(HEADERS);a=requests.adapters.HTTPAdapter(pool_connections=8,pool_maxsize=8,max_retries=0);s.mount("http://",a);s.mount("https://",a);_tls.session=s
 return s
def _gate(url):
 host=(urlparse(url).hostname or "").lower()
 with _gate_lock:
  if host not in _gates:_gates[host]=threading.BoundedSemaphore(MAX_PER_HOST)
  return _gates[host]
def _request(method,url,**kwargs):
 with _gate(url):
  last=None
  for attempt in range(RETRIES+1):
   try:
    fn=session().head if method=="head" else session().get
    return fn(url,**kwargs),None
   except requests.RequestException as e:
    last=e
    if attempt<RETRIES:time.sleep(.1*(attempt+1))
  return None,last
def normalize_url(url):
 url=str(url).strip();p=urlparse(url)
 if not p.scheme or not p.netloc:return url
 q=[(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if k.lower() not in TRACKING_PARAMS]
 return urlunparse((p.scheme.lower(),p.netloc.lower(),p.path,p.params,urlencode(q),""))
def protocol(url,content_type=""):
 v=normalize_url(url).lower().split("?",1)[0];ct=content_type.lower()
 if v.endswith((".m3u8",".m3u")) or "mpegurl" in ct or "vnd.apple.mpegurl" in ct:return "hls"
 if v.endswith(".mpd") or "dash+xml" in ct:return "dash"
 if v.endswith((".mp4",".ts",".mkv",".webm",".avi",".flv",".mov",".m4v")):return "media"
 return "unknown"
def score(status,proto,redirected=False,segment_ok=None):
 if status=="active":return max(0,(100 if proto in {"hls","dash","media"} else 80)-(35 if segment_ok is False else 0)-(5 if redirected else 0))
 if status=="geo_or_restricted":return 25
 if status=="timeout":return 10
 if status in {"down","invalid"}:return 0
 return 15
def _prefix(r,limit=65536):
 try:return next(r.iter_content(chunk_size=min(limit,16384)),b"")[:limit]
 finally:r.close()
def probe_hls(response):
 try:
  lines=[]
  for raw in response.iter_lines():
   if raw:lines.append(raw)
   if len(lines)>=64:break
  if b"#EXTM3U" not in b"\n".join(lines).upper():return False,None
  for raw in lines:
   line=raw.decode("utf-8","ignore").strip()
   if line and not line.startswith("#"):return True,urljoin(response.url,line)
  return True,None
 except requests.RequestException:return False,None
def probe_segment(url):
 if not url:return False
 r,e=_request("get",url,timeout=TIMEOUT,allow_redirects=True,stream=True)
 if r is None:return False
 try:
  if r.status_code>=400:return False
  return bool(next(r.iter_content(chunk_size=2048),b""))
 finally:r.close()
def probe_hls_sample(url,depth=0):
 if not url:return False
 r,e=_request("get",url,timeout=TIMEOUT,allow_redirects=True,stream=True)
 if r is None:return False
 try:
  if r.status_code>=400:return False
  if depth>1:return bool(next(r.iter_content(chunk_size=2048),b""))
  proto=protocol(r.url,r.headers.get("content-type",""))
  if proto!="hls":return bool(next(r.iter_content(chunk_size=2048),b""))
  ok,child=probe_hls(r)
 finally:
  try:r.close()
  except Exception:pass
 if not ok:return False
 return probe_hls_sample(child,depth+1) if child else True
def _apply(result,r):
 result.update(http_status=r.status_code,final_url=normalize_url(r.url),redirected=normalize_url(r.url)!=result["url"],protocol=protocol(r.url,r.headers.get("content-type","")))
def probe(channel):
 url=normalize_url(channel.get("url",""));result={"name":channel.get("name","Unnamed Channel"),"url":url,"country":channel.get("country",""),"group":channel.get("group","Uncategorized"),"logo":channel.get("logo",""),"source":channel.get("source",""),"status":"unknown","protocol":protocol(url),"http_status":None,"final_url":url,"redirected":False,"score":0}
 if not url.startswith(("http://","https://")):result["status"]="invalid";return result
 known=result["protocol"] in {"hls","dash","media"}
 if not (SKIP_HEAD_MEDIA and known):
  r,e=_request("head",url,timeout=HEAD_TIMEOUT,allow_redirects=True)
  if r is not None:
   _apply(result,r);r.close()
   if result["http_status"] in (401,403,451):result["status"]="geo_or_restricted";result["score"]=25;return result
   if 200<=result["http_status"]<400 and result["protocol"] not in {"hls","dash","media"}:result["status"]="active";result["score"]=score("active",result["protocol"],result["redirected"]);return result
 for attempt in range(RETRIES+1):
  r,e=_request("get",url,timeout=TIMEOUT,allow_redirects=True,stream=True)
  if r is None:
   if isinstance(e,requests.Timeout) and attempt<RETRIES:continue
   result["status"]="timeout" if isinstance(e,requests.Timeout) else "down";break
  try:
   _apply(result,r);code=r.status_code
   if code in (401,403,451):result["status"]="geo_or_restricted"
   elif code in TRANSIENT_STATUSES and attempt<RETRIES:continue
   elif 200<=code<400:
    if result["protocol"]=="hls":
     ok,sample=probe_hls(r);result["manifest_ok"]=ok;result["sample_segment"]=sample
     result["segment_ok"]=probe_hls_sample(sample) if ok and sample else None
     result["status"]="active" if ok and (result["segment_ok"] is not False) else "unknown"
    elif result["protocol"]=="dash":
     result["manifest_ok"]=b"<mpd" in _prefix(r).lower();result["status"]="active" if result["manifest_ok"] else "unknown"
    else:
     chunk=_prefix(r,2048);ct=r.headers.get("content-type","").lower();html="text/html" in ct or chunk.lstrip().lower().startswith((b"<!doctype html",b"<html"));result["status"]="active" if chunk and not html else "unknown"
   else:result["status"]="down"
  finally:
   try:r.close()
   except Exception:pass
  break
 result["score"]=score(result["status"],result["protocol"],result["redirected"],result.get("segment_ok"));return result
def load_channels():
 out=[]
 for path in ROOT.glob("*/LiveTV.json"):
  try:
   data=json.loads(path.read_text(encoding="utf-8"));grouped=data.get("channels",[]) if isinstance(data,dict) else data
   if isinstance(grouped,dict):items=[x for values in grouped.values() for x in values if isinstance(x,dict)]
   elif isinstance(grouped,list):items=[x for x in grouped if isinstance(x,dict)]
   else:continue
   country=data.get("country",path.parent.name) if isinstance(data,dict) else path.parent.name
   for item in items:
    row=dict(item);row.setdefault("country",country);out.append(row)
  except (OSError,json.JSONDecodeError):pass
 return out
def compact_channel(item):return {"name":item.get("name","Unnamed Channel"),"url":item.get("final_url") or item.get("url",""),"logo":item.get("logo",""),"group":item.get("group","Uncategorized"),"country":item.get("country",""),"type":item.get("protocol","unknown"),"score":item.get("score",0)}
def _safe(name,used):
 base=re.sub(r"[^A-Za-z0-9._-]+","_",name).strip("._") or "Unknown";x=base;i=2
 while x in used:x=f"{base}_{i}";i+=1
 used.add(x);return x
def _write_m3u(path,channels):
 with path.open("w",encoding="utf-8") as f:
  f.write("#EXTM3U\n")
  for x in channels:f.write(f'#EXTINF:-1 tvg-logo="{x.get("logo","").replace(chr(34),"&quot;")}" group-title="{x.get("group","").replace(chr(34),"&quot;")}",{x.get("name","").replace(chr(10)," ").replace(chr(13)," ")}\n{x["url"]}\n')
def write_app_exports(results,checked_at):
 OUT.mkdir(parents=True,exist_ok=True);active=[compact_channel(x) for x in results if x["status"]=="active"]; (OUT/"active.json").write_text(json.dumps({"version":1,"updated":checked_at,"count":len(active),"channels":active},ensure_ascii=False,indent=2),encoding="utf-8");_write_m3u(OUT/"active.m3u",active)
 cd=OUT/"countries";cd.mkdir(exist_ok=True);[p.unlink() for p in cd.glob("*.json")];[p.unlink() for p in cd.glob("*.m3u")];by=defaultdict(list);[by[x.get("country","Unknown")].append(x) for x in results];countries={};used=set()
 for country,items in sorted(by.items()):
  c=Counter(x.get("status","unknown") for x in items);summary={"total":len(items),"active":c["active"],"geo_or_restricted":c["geo_or_restricted"],"down":c["down"],"timeout":c["timeout"],"unknown":c["unknown"],"invalid":c["invalid"],"average_score":round(sum(x.get("score",0) for x in items)/len(items),2) if items else 0};countries[country]=summary;safe=_safe(country,used);rows=[compact_channel(x) for x in items if x.get("status")=="active"];(cd/f"{safe}.json").write_text(json.dumps({"version":1,"updated":checked_at,"country":country,"count":len(rows),"health":summary,"channels":rows},ensure_ascii=False,indent=2),encoding="utf-8");_write_m3u(cd/f"{safe}.m3u",rows)
 (OUT/"countries.json").write_text(json.dumps({"version":1,"updated":checked_at,"countries":countries},ensure_ascii=False,indent=2),encoding="utf-8");(OUT/"manifest.json").write_text(json.dumps({"version":1,"updated":checked_at,"endpoints":{"all_active_json":"active.json","all_active_m3u":"active.m3u","country_summary":"countries.json","country_directory":"countries/","full_health":"health.json"}},ensure_ascii=False,indent=2),encoding="utf-8")
def main():
 unique={}
 for ch in load_channels():
  u=normalize_url(ch.get("url",""))
  if u and u not in unique:row=dict(ch);row["url"]=u;unique[u]=row
 with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:results=list(pool.map(probe,unique.values()))
 checked=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z");summary=Counter(x["status"] for x in results);payload={"updated":checked,"total_unique_streams":len(results),"summary":dict(summary),"active_streams":summary["active"],"average_score":round(sum(x["score"] for x in results)/len(results),2) if results else 0,"streams":results};OUT.mkdir(parents=True,exist_ok=True);(OUT/"health.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8");write_app_exports(results,checked);print(f"Validated {len(results)} unique streams: {dict(summary)}")
if __name__=="__main__":main()
