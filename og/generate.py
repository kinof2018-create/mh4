#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
카톡 미리보기 자동 생성기
- share/미리보기문구.txt 를 읽어
  1) share/og-image.png (미리보기 이미지, 아래로 갈수록 페이드) 를 다시 만들고
  2) index.html 의 og:title / og:description 을 갱신합니다.
GitHub Actions 에서 Push 시 자동 실행됩니다.
"""
import os, re, glob, html
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT    = os.path.join(ROOT, "share", "미리보기문구.txt")
OUT    = os.path.join(ROOT, "share", "og-image.png")
INDEX  = os.path.join(ROOT, "index.html")
LOGO   = os.path.join(ROOT, "og", "logo-source.png")

CAT_COLOR = {"안전":"#D64545","총무":"#1B63D6","교육":"#2E9E5B","인사":"#8A5AD6","일반":"#5A5F6E"}

def find_font():
    cands = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    ]
    for p in cands:
        if os.path.exists(p): return p
    for pat in ["/usr/share/fonts/**/NotoSansCJK*Bold*.*",
                "/usr/share/fonts/**/NotoSansCJK*.*",
                "/usr/share/fonts/**/NanumGothic*.*",
                "/usr/share/fonts/**/*CJK*.*"]:
        g = glob.glob(pat, recursive=True)
        if g: return sorted(g)[0]
    raise RuntimeError("한글 폰트를 찾지 못했습니다 (fonts-noto-cjk 설치 필요)")

FONT = find_font()
def F(sz):
    try:    return ImageFont.truetype(FONT, sz, index=0)
    except: return ImageFont.truetype(FONT, sz)

def parse_txt():
    cat, title, body = "안전", "", []
    mode_body = False
    with open(TXT, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            s = line.strip()
            if s.startswith("#"): continue
            if not mode_body:
                m = re.match(r"^\s*(카테고리|분류)\s*[:：]\s*(.*)$", line)
                if m: cat = m.group(2).strip() or cat; continue
                m = re.match(r"^\s*(제목|title)\s*[:：]\s*(.*)$", line, re.I)
                if m: title = m.group(2).strip(); continue
                m = re.match(r"^\s*(내용|본문|content)\s*[:：]\s*(.*)$", line, re.I)
                if m:
                    mode_body = True
                    if m.group(2).strip(): body.append(m.group(2).strip())
                    continue
                if title and s: body.append(s)
            else:
                if s: body.append(s)
    if cat not in CAT_COLOR: cat = "일반"
    return cat, (title or "사내 공지"), body

def make_white_logo():
    im = Image.open(LOGO).convert("RGB")
    a = np.asarray(im).astype(np.int16); r,g,b = a[...,0],a[...,1],a[...,2]
    bright = np.maximum(np.maximum(r,g),b); minc = np.minimum(np.minimum(r,g),b); sat = bright-minc
    o = np.zeros((a.shape[0],a.shape[1],4), dtype=np.uint8); colored = sat>=45
    o[...,0]=np.where(colored,r,255); o[...,1]=np.where(colored,g,255); o[...,2]=np.where(colored,b,255)
    o[...,3]=np.where(colored,np.clip(sat*4,0,255),np.clip(255-bright,0,255)).astype(np.uint8)
    lg = Image.fromarray(o,"RGBA"); return lg.crop(lg.getbbox())

def draw_image(cat, title, body):
    SS=2; W,H=1200*SS,630*SS
    top=(10,23,88); bot=(20,40,160)
    def bgcol(y):
        t=y/H; return (int(top[0]+(bot[0]-top[0])*t),int(top[1]+(bot[1]-top[1])*t),int(top[2]+(bot[2]-top[2])*t))
    img=Image.new("RGB",(W,H),"#0A1758"); d=ImageDraw.Draw(img)
    for y in range(H): d.line([(0,y),(W,y)],fill=bgcol(y))
    d.ellipse([W-240*SS,-260*SS,W+220*SS,200*SS],fill=(38,69,176))
    logo=make_white_logo(); lh=104*SS; lw=int(logo.size[0]*lh/logo.size[1])
    L=logo.resize((lw,lh),Image.LANCZOS); img.paste(L,(80*SS,74*SS),L)
    d.rounded_rectangle([84*SS,198*SS,150*SS,214*SS],radius=8*SS,fill="#4ADE80")
    d.text((166*SS,188*SS),"사내 안내문  ·  NOTICE BOARD",font=F(34*SS),fill=(205,214,240))
    # 카테고리 칩 + 제목
    col=CAT_COLOR.get(cat,"#5A5F6E")
    cw=int(d.textlength(cat,font=F(24*SS)))+44*SS
    d.rounded_rectangle([84*SS,250*SS,84*SS+cw,290*SS],radius=20*SS,fill=col)
    d.text((84*SS+22*SS,256*SS),cat,font=F(24*SS),fill="#FFFFFF")
    d.text((84*SS+cw+16*SS,252*SS),title,font=F(34*SS),fill="#FFFFFF")
    # 본문 (아래로 갈수록 페이드)
    y=320*SS
    for i,ln in enumerate(body[:5]):
        shade=[255,(235,240,252),(225,232,248),(210,218,240),(196,206,232)][min(i,4)]
        fill=(255,255,255) if shade==255 else shade
        d.text((84*SS,y),ln,font=F(30*SS),fill=fill)
        y+=52*SS
    # 페이드 음영
    arr=np.asarray(img).astype(np.float32)
    y0,y1=300*SS,566*SS
    for yy in range(y0,y1):
        f=min(1.0,((yy-y0)/(y1-y0))**1.35*1.05)
        c=np.array(bgcol(yy),dtype=np.float32)
        arr[yy]=arr[yy]*(1-f)+c*f
    img=Image.fromarray(np.clip(arr,0,255).astype(np.uint8),"RGB")
    img=img.resize((1200,630),Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.4,percent=115,threshold=2))
    img.save(OUT,"PNG")

def update_index(title, body):
    if not os.path.exists(INDEX): return
    s=open(INDEX,encoding="utf-8").read()
    og_title = html.escape("📢 [삼화당피앤티] "+title, quote=True)
    og_desc  = html.escape(" ".join(body[:2])[:120], quote=True)
    s=re.sub(r'(<meta property="og:title" content=")[^"]*(")',      lambda m:m.group(1)+og_title+m.group(2), s, count=1)
    s=re.sub(r'(<meta property="og:description" content=")[^"]*(")',lambda m:m.group(1)+og_desc +m.group(2), s, count=1)
    open(INDEX,"w",encoding="utf-8").write(s)

if __name__ == "__main__":
    cat,title,body = parse_txt()
    draw_image(cat,title,body)
    update_index(title,body)
    print("OG 미리보기 생성 완료:", title)
