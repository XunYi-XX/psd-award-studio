from pathlib import Path
import argparse,csv,datetime,json,os,re,shutil,subprocess,sys,tempfile,time
from collections import defaultdict
from openpyxl import load_workbook
from pypinyin import lazy_pinyin
from reportlab.pdfgen.canvas import Canvas
from PIL import Image

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

def export(jobs,template,ps,destination):
    if not Path(ps).is_file() or Path(ps).name.lower()!='photoshop.exe':raise ValueError('请选择已安装的 Photoshop.exe')
    if not Path(template).is_file():raise ValueError('模板文件不存在')
    out=Path(destination)/datetime.datetime.now().strftime('奖状_%Y%m%d_%H%M%S_%f')
    out.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='award-studio-') as temp:
        tmp=Path(temp);pages=defaultdict(list);items=[]
        for i,j in enumerate(jobs,1):
            folder=out/f"第{j['n']}组";folder.mkdir(exist_ok=True)
            safe=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',j['award'])[:60]
            p=folder/f'{i:03}_{safe}.psd';shutil.copyfile(template,p)
            jpg=tmp/f'{i}.jpg';items.append(dict(j,file=p.as_posix(),jpg=jpg.as_posix()));pages[j['n']].append(jpg)
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
    import tkinter as tk
    from tkinter import ttk,filedialog as fd,messagebox as mb
    import threading,queue
    win=tk.Tk();win.title('分组奖状制作工具');win.geometry('1050x640')
    frame=ttk.Frame(win,padding=16);frame.pack(fill='both',expand=True)
    date=tk.StringVar(value=f'{datetime.date.today().year}年{datetime.date.today().month}月')
    ps=tk.StringVar(value=default_ps());template=tk.StringVar(value=str(ASSET));status=tk.StringVar(value='导入 Excel 或直接填写下方名单')
    def picker(var,ext):
        path=fd.askopenfilename(filetypes=[(ext,'*.'+ext)])
        if path:var.set(path)
    for label,var,ext in [('Photoshop',ps,'exe'),('PSD 模板',template,'psd'),('落款日期',date,None)]:
        row=ttk.Frame(frame);row.pack(fill='x',pady=2);ttk.Label(row,text=label,width=12).pack(side='left');ttk.Entry(row,textvariable=var).pack(side='left',fill='x',expand=True)
        if ext:ttk.Button(row,text='选择…',command=lambda v=var,e=ext:picker(v,e)).pack(side='left')
    bar=ttk.Frame(frame);bar.pack(fill='x',pady=10)
    ttk.Label(frame,text='每行一组，可直接修改。格式：组号 | 作品名 | 组员（顿号分隔） | 奖项（顿号分隔）。奖项留空则跳过该组。').pack(anchor='w')
    from tkinter.scrolledtext import ScrolledText
    edit=ScrolledText(frame,wrap='none',font=('Microsoft YaHei UI',11),undo=True);edit.pack(fill='both',expand=True)
    def read_editor():
        groups={};aw={}
        for line in edit.get('1.0','end').splitlines():
            if not line.strip():continue
            num,title,names,prizes=[x.strip() for x in line.split('|')]
            n=group(num)
            if not n or n in groups:raise ValueError('请检查组号：'+num)
            groups[n]=[title,parts(names)];aw[n]=parts(prizes)
        return groups,aw
    def put(groups,aw):
        edit.delete('1.0','end');edit.insert('1.0',text_rows(groups,aw))
        status.set(f'已载入 {len(groups)} 组，合计 {sum(map(len,aw.values()))} 张奖状')
    def load(mode,path=None):
        try:
            if not path:path=fd.askopenfilename(filetypes=[('名单或获奖表','*.xlsx *.csv')])
            if not path:return
            tables=sheets(path);groups,aw=read_editor()
            if mode=='roster':
                groups=roster(tables,{n:t for n,(t,_) in groups.items()})
                aw=awards(tables,groups)
            else:
                aw=awards(tables,groups)
                if not aw:raise ValueError('未识别到奖项，请使用“奖项 | 组别”或“奖项 | 作品1 | 作品2”')
            put(groups,aw)
        except Exception as e:mb.showerror('导入失败',str(e))
    ttk.Button(bar,text='导入分组名单 / 完整工作簿',command=lambda:load('roster')).pack(side='left')
    ttk.Button(bar,text='导入获奖表',command=lambda:load('awards')).pack(side='left',padx=8)
    preset=APP/'本届名单与奖项.xlsx'
    if preset.is_file():ttk.Button(bar,text='载入本届名单与奖项',command=lambda:load('roster',preset)).pack(side='left')
    events=queue.Queue()
    def start():
        try:
            jobs=plan(edit.get('1.0','end'),date.get().strip());args=(jobs,template.get(),ps.get());dest=fd.askdirectory(title='选择导出位置')
            if not dest:return
            go.state(['disabled']);status.set(f'Photoshop 正在制作 {len(jobs)} 张奖状…')
            def work():
                try:events.put((True,str(export(*args,dest))))
                except Exception as e:events.put((False,str(e)))
            threading.Thread(target=work,daemon=True).start()
        except Exception as e:mb.showerror('请检查输入',str(e))
    def poll():
        if not events.empty():
            ok,msg=events.get();go.state(['!disabled']);status.set(msg)
            if ok:mb.showinfo('导出完成',msg);os.startfile(msg)
            else:mb.showerror('导出失败',msg)
        win.after(250,poll)
    go=ttk.Button(bar,text='导出 PSD 和分组 PDF',command=start);go.pack(side='right')
    ttk.Label(frame,textvariable=status).pack(anchor='w',pady=5)
    win.protocol('WM_DELETE_WINDOW',lambda:None if go.instate(['disabled']) else win.destroy())
    if preset.is_file():load('roster',preset)
    poll();win.mainloop()

if __name__=='__main__':
    if len(sys.argv)==1:gui()
    else:
        a=argparse.ArgumentParser();a.add_argument('--workbook',required=True);a.add_argument('--awards');a.add_argument('--date',required=True);a.add_argument('--photoshop',default=default_ps());a.add_argument('--template',default=str(ASSET));a.add_argument('--output',required=True);args=a.parse_args()
        data=sheets(args.workbook);gs=roster(data);aw=awards(sheets(args.awards) if args.awards else data,gs)
        export(plan(text_rows(gs,aw),args.date),args.template,args.photoshop,args.output)
