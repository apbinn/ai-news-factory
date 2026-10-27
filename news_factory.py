#!/usr/bin/env python3
"""Muse JSON -> SQLite -> review -> draft -> optional FFmpeg demo; no paid API."""
import argparse, datetime, html, json, pathlib, re, shutil, sqlite3, subprocess
from urllib.parse import urlsplit
ROOT=pathlib.Path(__file__).parent
DB=ROOT/"data"/"news.db"
OUT=ROOT/"output"

def read(path):
    data=json.loads(pathlib.Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data,dict): raise ValueError("JSON 根节点必须为对象")
    day=data.get("report_date",data.get("date"))
    datetime.date.fromisoformat(day)
    items=data.get("news",data.get("items"))
    if not isinstance(items,list): raise ValueError("news/items 必须是数组")
    ids=set()
    for it in items:
        if not isinstance(it,dict): raise ValueError("新闻必须是对象")
        nid=it.get("news_id");title=it.get("title");url=it.get("source_url")
        if not nid or not isinstance(nid,str) or nid in ids: raise ValueError("新闻 ID 缺失或重复")
        ids.add(nid)
        if not isinstance(title,str) or not title.strip(): raise ValueError(nid+": 缺标题")
        if not isinstance(url,str) or urlsplit(url).scheme not in ("http","https") or not urlsplit(url).netloc:
            raise ValueError(nid+": 来源 URL 不合法")
        for link in it.get("evidence_urls",[]):
            if not isinstance(link,str) or urlsplit(link).scheme not in ("http","https") or not urlsplit(link).netloc:
                raise ValueError(nid+": 证据 URL 不合法")
    return day,items

def connect(path):
    path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(path);con.row_factory=sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS news (
        news_id TEXT PRIMARY KEY, day TEXT NOT NULL, title TEXT NOT NULL,
        category TEXT, summary TEXT, source_url TEXT NOT NULL,
        source_name TEXT, evidence TEXT, verification TEXT,
        review TEXT NOT NULL DEFAULT 'needs_review', note TEXT,
        raw TEXT NOT NULL)""")
    return con

def ingest(path,db):
    day,items=read(path)
    counts={"new":0,"changed":0,"unchanged":0}
    with connect(db) as con:
        for it in items:
            raw=json.dumps(it,ensure_ascii=False,sort_keys=True)
            old=con.execute("SELECT raw FROM news WHERE news_id=?",(it["news_id"],)).fetchone()
            if old and old["raw"]==raw: counts["unchanged"]+=1;continue
            verification=it.get("verification_status",it.get("verification","unverified"))
            con.execute("""INSERT INTO news(news_id,day,title,category,summary,source_url,source_name,evidence,verification,review,note,raw)
                VALUES(?,?,?,?,?,?,?,?,?,'needs_review',NULL,?)
                ON CONFLICT(news_id) DO UPDATE SET day=excluded.day,title=excluded.title,
                category=excluded.category,summary=excluded.summary,source_url=excluded.source_url,
                source_name=excluded.source_name,evidence=excluded.evidence,
                verification=excluded.verification,review='needs_review',note=NULL,raw=excluded.raw""",
                (it["news_id"],day,it["title"],it.get("category",""),
                 it.get("summary_zh",it.get("summary","")),it["source_url"],
                 it.get("source_name",""),json.dumps(it.get("evidence_urls",[]),ensure_ascii=False),
                 verification,raw))
            counts["changed" if old else "new"]+=1
    print("导入结果",counts,"（默认全部待人工审核）")

def rows(db,day,approved=False):
    with connect(db) as con:
        q="SELECT * FROM news WHERE day=?"
        if approved:q+=" AND review='approved'"
        return [dict(x) for x in con.execute(q+" ORDER BY news_id",(day,)).fetchall()]

def report(db,day):
    records=rows(db,day)
    if not records:raise ValueError("指定日期无记录，先 import")
    dest=OUT/day;dest.mkdir(parents=True,exist_ok=True)
    parts=['<!doctype html><html lang="zh"><meta charset="utf-8"><title>审核预览</title>',
           '<style>body{font:16px Arial, sans-serif;max-width:900px;margin:40px auto;padding:20px;line-height:1.6}article{border:1px solid #bbb;border-radius:10px;padding:16px;margin:16px 0}small{color:#666}</style>',
           '<h1>AI 资讯审核预览 '+html.escape(day)+'</h1><p>只读预览，所有信息发布前需独立核实。</p>']
    for r in records:
        e=lambda x:html.escape(str(x or ""),quote=True)
        parts+=['<article><h2>'+e(r["title"])+'</h2><small>'+e(r["category"])+' · Muse:'+e(r["verification"])+' · 审核:'+e(r["review"])+'</small>',
                '<p>'+e(r["summary"])+'</p><a target="_blank" rel="noopener noreferrer" href="'+e(r["source_url"])+'">打开原始来源</a></article>']
    (dest/"review.html").write_text("\n".join(parts+["</html>"]),encoding="utf-8")
    print("已生成",dest/"review.html")

def decision(db,nid,status,checked,note,override):
    if status=="approved" and not checked:raise ValueError("批准时必须声明 --checked")
    with connect(db) as con:
        r=con.execute("SELECT * FROM news WHERE news_id=?",(nid,)).fetchone()
        if not r:raise ValueError("新闻 ID 不存在")
        if status=="approved" and r["verification"] not in ("verified",) and not override:
            raise ValueError("Muse 未核实新闻需额外 --override-pending，并先找到独立证据")
        con.execute("UPDATE news SET review=?,note=? WHERE news_id=?",(status,note,nid))
    print(nid,status)

def draft(db,day):
    data=rows(db,day,True)
    if not data:raise ValueError("没有人工批准的新闻，禁止生成正式稿")
    dest=OUT/day;dest.mkdir(parents=True,exist_ok=True)
    s=["# AI 每日情报｜"+day,"","**编辑草稿：发布前仍需最终事实核实**",""]
    for i,r in enumerate(data,1):
        s.extend([f"## {i}. {r['title']}",r["summary"],"来源："+r["source_url"],""])
    (dest/"article_draft.md").write_text("\n".join(s),encoding="utf-8")
    print("已生成",dest/"article_draft.md")

def render(db,day,demo):
    if not shutil.which("ffmpeg"):raise ValueError("未找到 FFmpeg")
    data=rows(db,day,not demo)
    if not data:raise ValueError("没有可用于渲染的新闻")
    try:from PIL import Image,ImageDraw,ImageFont
    except ImportError:raise ValueError("请 pip install -r requirements.txt")
    font=next((p for p in [r"C:\Windows\Fonts\msyh.ttc",r"C:\Windows\Fonts\simhei.ttf"] if pathlib.Path(p).exists()),None)
    if not font:raise ValueError("需要 Windows 中文字体")
    dest=OUT/day/("demo_video" if demo else "production_video");dest.mkdir(parents=True,exist_ok=True)
    paths=[]
    for i,r in enumerate(data[:3],1):
        im=Image.new("RGB",(540,960),(14,28,48));d=ImageDraw.Draw(im)
        title=ImageFont.truetype(font,32);small=ImageFont.truetype(font,24)
        d.text((45,65),"AI NEWS",font=title,fill="cyan")
        txt=r["title"];lines=[];line=""
        for ch in txt:
            if d.textbbox((0,0),line+ch,font=title)[2]>450:lines.append(line);line=ch
            else:line+=ch
        lines.append(line)
        for j,l in enumerate(lines[:8]):d.text((45,175+52*j),l,font=title,fill="white")
        d.text((45,760),"未审核 · 禁止发布" if demo else "人工已批准 · 尚需终审",font=small,fill="orange")
        p=dest/f"slide_{i:02d}.png";im.save(p);paths.append(p)
    manifest=[]
    for p in paths:
        manifest.extend(["file '"+p.resolve().as_posix()+"'","duration 4"])
    manifest.append("file '"+paths[-1].resolve().as_posix()+"'")
    (dest/"slides.txt").write_text("\n".join(manifest)+"\n",encoding="utf-8")
    target=dest/("DEMO_NOT_FOR_PUBLICATION.mp4" if demo else "news_video_draft.mp4")
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",
         str(dest/"slides.txt"),"-t",str(4*len(paths)),"-r","24","-c:v","libx264",
         "-pix_fmt","yuv420p","-movflags","+faststart",str(target)],check=True)
    print("无配音测试视频:",target)

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="cmd",required=True)
    s=sub.add_parser("check");s.add_argument("file")
    s=sub.add_parser("import");s.add_argument("file");s.add_argument("--db",default=str(DB))
    for c in ("report","draft","render"):
        s=sub.add_parser(c);s.add_argument("--date",required=True);s.add_argument("--db",default=str(DB))
        if c=="render":s.add_argument("--demo",action="store_true")
    for c in ("approve","reject"):
        s=sub.add_parser(c);s.add_argument("news_id");s.add_argument("--db",default=str(DB))
        s.add_argument("--checked",action="store_true");s.add_argument("--note",default="")
        s.add_argument("--override-pending",action="store_true")
    a=p.parse_args()
    if a.cmd=="check":
        day,items=read(a.file);print("格式通过",day,len(items),"条（不代表事实已核实）")
    elif a.cmd=="import":ingest(a.file,a.db)
    elif a.cmd=="report":report(a.db,a.date)
    elif a.cmd=="draft":draft(a.db,a.date)
    elif a.cmd=="render":render(a.db,a.date,a.demo)
    else:decision(a.db,a.news_id,"approved" if a.cmd=="approve" else "rejected",
                  a.checked,a.note,a.override_pending)
if __name__=="__main__":
    try:main()
    except (ValueError,KeyError,subprocess.CalledProcessError) as ex:
        print("错误:",str(ex));raise SystemExit(2)
