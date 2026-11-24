from pathlib import Path
import argparse,csv,datetime,json,os,re,shutil,subprocess,sys,tempfile,time
from collections import defaultdict
from openpyxl import load_workbook
from pypinyin import lazy_pinyin
from reportlab.pdfgen.canvas import Canvas
from PIL import Image, ImageOps

ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))
APP=Path(sys.executable).parent if getattr(sys,'frozen',False) else ROOT.parent
ASSET=ROOT/'assets/template.psd'
DIGITS='零一二三四五六七八九'
def chinese(n):
    if n<10:return DIGITS[n]
    if n<100:return (DIGITS[n//10] if n>=20 else '')+'十'+(DIGITS[n%10] if n%10 else '')
    return str(n)

def group(value):
    s=re.sub(r'^(?:第)|(?:小组|组)$','',value.strip())
    if s.isdigit() and 0<int(s)<1000:return int(s)
    return next((i for i in range(1,100) if chinese(i)==s),None)

def parts(value):
    return [s for s in re.split(r'[、，,；;\s]+',value.strip()) if s]

def sheets(path):
    p=Path(path)
    if p.suffix.lower()=='.csv':
        for enc in ('utf-8-sig','gb18030'):
            try:return [list(csv.reader(p.read_text(encoding=enc).splitlines()))]
            except UnicodeDecodeError:pass
        raise ValueError('CSV 编码无法识别')
    w=load_workbook(p,read_only=True,data_only=True)
    try:return [[[str(c).strip() if c is not None else '' for c in row] for row in s.values] for s in w if s.sheet_state=='visible']
    finally:w.close()

def roster(tables,hints=None):
    result={}
    for rows in tables:
        for i,h in enumerate(rows):
            m=[k for k,v in enumerate(h) if re.fullmatch(r'(组员|成员)(名单|姓名|\d*)',v)]
            if not m:continue
            gi=next((k for k,v in enumerate(h) if v in ('组别','组号','组','小组')),None)
            ti=next((k for k,v in enumerate(h) if v in ('作品','作品名','作品名称','片名')),None)
            for row in rows[i+1:]:
                row=row+['']*max(0,len(h)-len(row))
                if not any(row):continue
                n=group(row[gi]) if gi is not None else len(result)+1
                if not n or n in result:raise ValueError('组号无效或重复：'+' / '.join(row[:3]))
                cols=m+[k for k in range(max(m)+1,len(row)) if k>=len(h) or not h[k]]
                names=[name for k in cols for name in parts(row[k])]
                result[n]=[(row[ti].strip('《》') if ti is not None else '') or (hints or {}).get(n,''),names]
            break
    if not result:raise ValueError('找不到“组员1”或“组员名单”等列')
    return result

def awards(tables,groups):
    result=defaultdict(list)
    for rows in tables:
        if any(any(re.fullmatch(r'组员\d*|成员名单',v) for v in r) for r in rows):continue
        header=next(((i,h) for i,h in enumerate(rows) if any(v in ('奖项','奖项名称','奖名') for v in h)),None)
        if header:
            i,h=header; ai=next(k for k,v in enumerate(h) if v in ('奖项','奖项名称','奖名')); data=rows[i+1:]
        else:ai=0;data=[r for r in rows if r and r[0].startswith('最佳')]
        for row in data:
            if not any(row):continue
            award=row[ai]
            if not award:raise ValueError('获奖表含空奖项')
            targets=[v.strip('《》') for k,v in enumerate(row) if k!=ai and v]
            if not targets:raise ValueError(award+' 缺少组号或作品')
            for v in targets:
                n=group(v)
                if n is None:
                    found=[g for g,(title,_) in groups.items() if title==v]
                    if len(found)!=1:raise ValueError('作品无法唯一匹配组号：'+v)
                    n=found[0]
                if n not in groups:raise ValueError(f'{award}：没有第{n}组名单')
                if award not in result[n]:result[n].append(award)
    return result

def plan(lines,date):
    if not re.fullmatch(r'\d{4}年(?:[1-9]|1[0-2])月(?:\d{1,2}日)?',date):raise ValueError('日期格式示例：2026年11月 或 2026年11月23日')
    datetime.datetime.strptime(date,'%Y年%m月%d日' if date.endswith('日') else '%Y年%m月')
    jobs=[];seen=set()
    for line in lines.splitlines():
        if not line.strip():continue
        fields=[s.strip() for s in line.split('|')]
        if len(fields)!=4:raise ValueError('每行需要四栏，以 | 分隔：'+line)
        number,title,raw,prizes=fields;n=group(number)
        if not n or n in seen:raise ValueError('组号无效或重复：'+number)
        seen.add(n)
        if not prizes:continue
        names=parts(raw)
        if not title or not names or len(names)!=len(set(names)):raise ValueError(f'请检查第{n}组的作品、缺失或重复姓名')
        names=sorted(names,key=lambda x:lazy_pinyin(x))
        names=['　'.join(x) if len(x)==2 else x for x in names]
        cut=(len(names)+1)//2
        members='小组成员： '+'、'.join(names[:cut])
        if cut<len(names):members+='、\r           '+'、'.join(names[cut:])
        for award in dict.fromkeys(parts(prizes)):
            jobs.append(dict(n=n,group=f'第{chinese(n)}小组',title=title,members=members,date=date,award=award))
    if not jobs:raise ValueError('至少填写一个获奖组及奖项')
    return jobs

def default_ps():
    import winreg
    local=APP/'photoshop-path.txt'
    if local.is_file():
        candidate=Path(local.read_text(encoding='utf-8-sig').strip())
        if candidate.is_file() and candidate.name.lower()=='photoshop.exe':return str(candidate)
    for key in (winreg.HKEY_LOCAL_MACHINE,winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(key,r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Photoshop.exe') as k:
                p=Path(winreg.QueryValueEx(k,'')[0].strip('"'))
                if p.is_file():return str(p)
        except OSError:pass
    paths=sorted((Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Adobe').glob('Adobe Photoshop */Photoshop.exe'),reverse=True)
    return str(paths[0]) if paths else ''

def export(jobs,template,ps,destination,background=None,layout=None,*,preview=False):
    if layout is not None:
        from layout_spec import validate
        validate(layout)
    if not Path(ps).is_file() or Path(ps).name.lower()!='photoshop.exe':raise ValueError('请选择已安装的 Photoshop.exe')
    if not Path(template).is_file():raise ValueError('模板文件不存在')
    out=Path(destination)/datetime.datetime.now().strftime('奖状_%Y%m%d_%H%M%S_%f')
    out.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='award-studio-') as temp:
        tmp=Path(temp);pages=defaultdict(list);items=[]
        backdrop=''
        if background:
            with Image.open(template) as base, Image.open(background) as src:
                image=ImageOps.exif_transpose(src).convert('RGBA')
                image=ImageOps.fit(image,base.size,method=Image.Resampling.LANCZOS)
                paper=Image.new('RGB',base.size,'white')
                paper.paste(image,mask=image.getchannel('A'))
                backdrop=(tmp/'background.png').as_posix()
                paper.save(backdrop)
        for i,j in enumerate(jobs,1):
            folder=out/f"第{j['n']}组";folder.mkdir(exist_ok=True)
            safe=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',j['award'])[:60]
            p=folder/f'{i:03}_{safe}.psd';shutil.copyfile(template,p)
            jpg=tmp/f'{i}.jpg';items.append(dict(j,map=(tmp/"layers.csv").as_posix() if preview else "",layout=layout,background=backdrop,file=p.as_posix(),jpg=jpg.as_posix()));pages[j['n']].append(jpg)
        done=tmp/'result.txt';jsx=tmp/'render.jsx'
        engine=(ROOT/'scripts/render.jsx').read_text(encoding='utf-8-sig')
        jsx.write_text('#target photoshop\nvar jobs='+json.dumps(items,ensure_ascii=True)+';var done='+json.dumps(done.as_posix())+';\n'+engine.split('\n',1)[1],encoding='utf-8-sig')
        subprocess.Popen([ps,'-r',str(jsx)])
        deadline=time.monotonic()+180+len(jobs)*45
        while not done.is_file() or not done.stat().st_size:
            if time.monotonic()>deadline:raise TimeoutError('Photoshop 未完成。请检查是否有弹窗。副本目录：'+str(out))
            time.sleep(.5)
        status=done.read_text(encoding='utf-8-sig')
        if status!='OK':raise RuntimeError(status+'；副本目录：'+str(out))
        if preview:
            import base64,io
            lines=(tmp/'layers.csv').read_text(encoding='utf-8-sig').splitlines()
            w,h=map(float,lines[0].split(','))
            rects={}
            for line in lines[1:]:
                key,*coords=line.split(',');rects[key]=list(map(float,coords))
            with Image.open(Path(items[0]['jpg'])) as image:
                image.thumbnail((1500,1061),Image.Resampling.LANCZOS)
                buf=io.BytesIO();image.save(buf,format='PNG')
            return dict(width=w,height=h,rects=rects,url='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode())
        for n,images in pages.items():
            pdf=Canvas(str(out/f'第{n}组奖状.pdf'))
            for img in images:
                with Image.open(img) as im:w,h=[v*72/300 for v in im.size]
                pdf.setPageSize((w,h));pdf.drawImage(str(img),0,0,width=w,height=h);pdf.showPage()
            pdf.save()
    return out

def text_rows(groups,mapping):
    return '\n'.join(f"{n} | {title} | {'、'.join(names)} | {'、'.join(mapping.get(n,[]))}" for n,(title,names) in sorted(groups.items()))

def gui():
    from workspace_ui import launch
    launch(sys.modules[__name__])

if __name__=='__main__':
    if len(sys.argv)==1:gui()
    else:
        a=argparse.ArgumentParser();a.add_argument('--workbook',required=True);a.add_argument('--awards');a.add_argument('--date',required=True);a.add_argument('--photoshop',default=default_ps());a.add_argument('--template',default=str(ASSET));a.add_argument('--output',required=True);a.add_argument('--background');a.add_argument('--layout',help='映印布局 JSON');args=a.parse_args()
        data=sheets(args.workbook);gs=roster(data);aw=awards(sheets(args.awards) if args.awards else data,gs)
        from layout_spec import read
        export(plan(text_rows(gs,aw),args.date),args.template,args.photoshop,args.output,args.background,read(args.layout) if args.layout else None)

