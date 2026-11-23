"""Desktop workspace for reviewing certificate data before Photoshop export."""
import datetime
import os
import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk

INK='#243731'
GREEN='#193C34'
ACCENT='#B8975E'
PAPER='#F3F2EC'
WHITE='#FCFBF7'
MUTED='#596961'
LINE='#DADDD4'
FONT='Microsoft YaHei UI'

def launch(core):
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    win=tk.Tk();win.title('映印 · 分组奖状制作');win.configure(bg=PAPER)
    width=min(1250,win.winfo_screenwidth()-40);height=min(800,win.winfo_screenheight()-75)
    win.geometry(f'{width}x{height}');win.minsize(min(920,width),min(620,height))
    win.option_add('*Font',(FONT,10))
    groups={};prizes={};events=queue.Queue();busy=False;background='';template=core.ASSET
    ps=core.default_ps();status=tk.StringVar(value='导入名单后，双击分组即可编辑。')
    today=datetime.date.today();date=tk.StringVar(value=f'{today.year}年{today.month}月')
    def panel(parent,color,**opts):return tk.Frame(parent,bg=color,**opts)
    def label(parent,text='',size=10,color=INK,bg=WHITE,bold=False,**opts):
        return tk.Label(parent,text=text,font=(FONT,size,'bold' if bold else 'normal'),fg=color,bg=bg,anchor='w',**opts)
    def button(parent,text,cmd,primary=False):
        return tk.Button(parent,text=text,command=cmd,font=(FONT,10,'bold' if primary else 'normal'),bg=GREEN if primary else WHITE,fg='white' if primary else INK,activebackground='#315749' if primary else '#E6E9DF',activeforeground='white' if primary else INK,relief='flat',bd=0,padx=13,pady=6,cursor='hand2',highlightthickness=0)
    def field(parent,var):
        return tk.Entry(parent,textvariable=var,font=(FONT,11),bg='white',fg=INK,insertbackground=GREEN,relief='solid',bd=1,highlightthickness=0)
    head=panel(win,GREEN,padx=23,pady=12);head.pack(fill='x')
    label(head,'映印',20,'#FBF8ED',GREEN,True).pack(side='left')
    label(head,'  /  分组奖状工作台',11,'#D9DCCF',GREEN).pack(side='left',padx=10)
    def settings():
        nonlocal ps,template
        top=tk.Toplevel(win);top.title('导出设置');top.configure(bg=WHITE,padx=20,pady=18);top.transient(win);top.grab_set()
        pv=tk.StringVar(value=ps);tv=tk.StringVar(value='' if template==core.ASSET else str(template))
        def pick(var,ext):
            p=filedialog.askopenfilename(parent=top,filetypes=[(ext,'*.'+ext)])
            if p:var.set(p)
        for name,var,ext in [('Photoshop 程序',pv,'exe'),('自定义 PSD（留空使用内置模板）',tv,'psd')]:
            label(top,name).pack(anchor='w');r=panel(top,WHITE);r.pack(fill='x',pady=(4,12));e=field(r,var);e.config(width=46);e.pack(side='left');button(r,'浏览',lambda v=var,x=ext:pick(v,x)).pack(side='left')
        def apply():
            nonlocal ps,template
            ps=pv.get().strip();template=Path(tv.get()) if tv.get().strip() else core.ASSET;top.destroy();preview()
        button(top,'保存设置',apply,True).pack(anchor='e')
    button(head,'导出设置',settings).pack(side='right')
    body=panel(win,PAPER,padx=18,pady=15);body.pack(fill='both',expand=True)
    body.grid_columnconfigure(0,weight=5);body.grid_columnconfigure(1,weight=4);body.grid_rowconfigure(0,weight=1)
    left=panel(body,WHITE,padx=15,pady=13);left.grid(row=0,column=0,sticky='nsew',padx=(0,12))
    right=panel(body,WHITE,padx=15,pady=13);right.grid(row=0,column=1,sticky='nsew')
    titlebar=panel(left,WHITE);titlebar.pack(fill='x')
    label(titlebar,'分组与获奖名单',16,bold=True).pack(side='left')
    counts=label(titlebar,'',9,MUTED);counts.pack(side='right')
    tools=panel(left,WHITE);tools.pack(fill='x',pady=(12,10))
    style=ttk.Style(win);style.theme_use('clam')
    style.configure('Award.Treeview',rowheight=38,font=(FONT,10),background=WHITE,fieldbackground=WHITE,foreground=INK,borderwidth=0)
    style.configure('Award.Treeview.Heading',background='#E8ECE3',foreground=GREEN,font=(FONT,10,'bold'),relief='flat',padding=(6,6))
    style.map('Award.Treeview',background=[('selected','#D8E5D8')],foreground=[('selected',GREEN)])
    grid=panel(left,WHITE);grid.pack(fill='both',expand=True)
    tree=ttk.Treeview(grid,columns=('group','title','people','award'),show='headings',style='Award.Treeview',selectmode='browse')
    for key,name,w in [('group','组别',62),('title','作品',130),('people','人数',44),('award','奖项',180)]:
        tree.heading(key,text=name,anchor='w');tree.column(key,width=w,minwidth=35,stretch=key in ('title','award'),anchor='w')
    scroll=ttk.Scrollbar(grid,command=tree.yview);scroll.pack(side='right',fill='y');tree.configure(yscrollcommand=scroll.set);tree.pack(fill='both',expand=True)
    people=label(left,'',10,MUTED,wraplength=440,justify='left');people.pack(fill='x',pady=(10,2))
    label(right,'奖状预览',16,bold=True).pack(anchor='w')
    tk.Label(right,text='布局示意 · 成品由 Photoshop 排版',fg=MUTED,bg=WHITE,font=(FONT,9)).pack(anchor='w',pady=(2,4))
    canvas=tk.Canvas(right,bg='#E7E8DF',highlightthickness=0,height=190,width=280);canvas.pack(fill='both',expand=True,pady=(5,9))
    choice=tk.StringVar();combo=ttk.Combobox(right,textvariable=choice,state='readonly');combo.pack(fill='x',pady=(0,6))
    def current():
        sel=tree.selection();return int(sel[0]) if sel else None
    def preview(*_):
        n=current();w=800;h=566
        paper=Path(background) if background else core.ROOT/'assets/paper.jpg'
        try:
            with Image.open(paper) as src:
                photo=ImageOps.fit(ImageOps.exif_transpose(src).convert('RGBA'),(w,h))
            im=Image.new('RGB',(w,h),'white');im.paste(photo,mask=photo.getchannel('A'))
        except Exception:im=Image.new('RGB',(w,h),'#FAF6EC')
        draw=ImageDraw.Draw(im);color='#592B1C'
        def txt(x,y,text,size,anchor='mm'):
            font=ImageFont.truetype('C:/Windows/Fonts/simsun.ttc',size)
            while len(text)>1 and draw.textlength(text,font=font)>w*.85 and size>10:
                size-=1;font=ImageFont.truetype('C:/Windows/Fonts/simsun.ttc',size)
            draw.text((x,y),text,font=font,fill=color,anchor=anchor)
        txt(400,99,'荣 誉 证 书',48)
        if n:
            title,names=groups[n];txt(85,170,f'第{core.chinese(n)}小组：',27,'lm')
            txt(400,235,'作品《'+title+'》',27);txt(400,322,choice.get() or '待填写奖项',37)
            ordered=sorted(names,key=core.lazy_pinyin);cut=(len(ordered)+1)//2
            txt(400,398,'小组成员：'+'、'.join(ordered[:cut]),18);txt(400,432,'、'.join(ordered[cut:]),18)
            people.config(text=f'第 {n} 组成员  ·  '+'、'.join(names))
        else:people.config(text='');txt(400,305,'导入名单以预览奖状',23)
        txt(615,490,date.get(),18)
        im.thumbnail((max(10,canvas.winfo_width()-16),max(10,canvas.winfo_height()-16)),Image.Resampling.LANCZOS)
        canvas.photo=ImageTk.PhotoImage(im);canvas.delete('all');canvas.create_image(canvas.winfo_width()/2,canvas.winfo_height()/2,image=canvas.photo)
    def select(*_):
        values=prizes.get(current(),[]);combo.configure(values=values);choice.set(values[0] if values else '');preview()
    def refresh(select_id=None):
        tree.delete(*tree.get_children())
        for n,(title,names) in sorted(groups.items()):tree.insert('', 'end',iid=str(n),values=(f'第{n}组',title,len(names),'、'.join(prizes.get(n,[])) or '—'),tags=('odd' if n%2 else 'even',))
        tree.tag_configure('even',background='#F5F5EF');counts.config(text=f'{len(groups)} 组  /  {sum(map(len,prizes.values()))} 张')
        if groups:
            n=select_id if select_id in groups else min(groups);tree.selection_set(str(n));tree.see(str(n))
        select()
    def load(kind,path=None):
        nonlocal groups,prizes
        try:
            if not path:path=filedialog.askopenfilename(filetypes=[('Excel / CSV','*.xlsx *.csv')])
            if not path:return
            tables=core.sheets(path)
            if kind=='roster':
                new=core.roster(tables,{n:t for n,(t,_) in groups.items()});mapping=core.awards(tables,new);groups,prizes=new,mapping
            else:
                mapping=core.awards(tables,groups)
                if not mapping:raise ValueError('未识别到获奖记录，请先导入名单并核对作品。')
                prizes=mapping
            refresh();status.set('已导入 '+Path(path).name)
        except Exception as e:messagebox.showerror('导入失败',str(e))
    def edit(new=False):
        n=None if new else current()
        if not new and n is None:return
        top=tk.Toplevel(win);top.title('新增分组' if new else f'编辑第 {n} 组');top.transient(win);top.grab_set();top.configure(bg=WHITE,padx=22,pady=16)
        title,names=groups.get(n,('',[]));vs=[]
        for heading,value in [('组号',str(n or max(groups,default=0)+1)),('作品名称',title),('组员（顿号分隔）','、'.join(names)),('奖项（留空跳过此组）','、'.join(prizes.get(n,[])))]:
            label(top,heading).pack(anchor='w');v=tk.StringVar(value=value);vs.append(v);e=field(top,v);e.configure(width=48);e.pack(fill='x',pady=(3,10))
        def save():
            number=core.group(vs[0].get());title=vs[1].get().strip();names=core.parts(vs[2].get())
            if not number or (number!=n and number in groups) or not title or not names or len(names)!=len(set(names)):return messagebox.showerror('检查分组','请填写唯一组号、作品名和不重复的组员。',parent=top)
            if n and n!=number:del groups[n];prizes.pop(n,None)
            groups[number]=[title,names];prizes[number]=list(dict.fromkeys(core.parts(vs[3].get())));top.destroy();refresh(number)
        button(top,'保存分组',save,True).pack(anchor='e')
    for name,cmd in [('导入名单',lambda:load('roster')),('导入获奖表',lambda:load('awards')),('新增分组',lambda:edit(True)),('编辑分组',edit)]:button(tools,name,cmd,name=='导入名单').pack(side='left',padx=(0,3))
    tree.bind('<<TreeviewSelect>>',select);tree.bind('<Double-1>',lambda e:edit());combo.bind('<<ComboboxSelected>>',preview)
    canvas.bind('<Configure>',preview);date.trace_add('write',preview)
    bgname=tk.StringVar(value='内置奖状底图')
    row=panel(right,WHITE);row.pack(fill='x')
    def pick_bg(reset=False):
        nonlocal background
        path='' if reset else filedialog.askopenfilename(filetypes=[('背景图片','*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff')])
        if not reset and not path:return
        if path:
            try:
                with Image.open(path) as im:im.verify()
            except Exception as e:return messagebox.showerror('无法读取背景',str(e))
        background=path;bgname.set(Path(path).name if path else '内置奖状底图');preview()
    button(row,'导入背景',pick_bg).pack(side='left');button(row,'恢复原背景',lambda:pick_bg(True)).pack(side='right')
    tk.Label(right,textvariable=bgname,bg=WHITE,fg=MUTED,anchor='w',font=(FONT,9)).pack(fill='x')
    label(right,'落款日期',10,bold=True).pack(anchor='w',pady=(7,2));field(right,date).pack(fill='x',ipady=4)
    def start():
        nonlocal busy
        try:
            jobs=core.plan(core.text_rows(groups,prizes),date.get().strip())
            dest=filedialog.askdirectory(title='选择奖状输出位置')
            if not dest:return
            args=(jobs,template,ps,dest,background);busy=True;go.config(state='disabled');status.set(f'正在用 Photoshop 制作 {len(jobs)} 张奖状…')
            def work():
                try:events.put((True,str(core.export(*args))))
                except Exception as e:events.put((False,str(e)))
            threading.Thread(target=work,daemon=True).start()
        except Exception as e:messagebox.showerror('检查导出内容',str(e))
    go=button(right,'导出 PSD 与分组 PDF',start,True);go.pack(fill='x',pady=(11,0))
    foot=panel(win,'#E6E9DF',padx=20,pady=5);foot.pack(fill='x')
    tk.Label(foot,textvariable=status,bg='#E6E9DF',fg=GREEN,font=(FONT,9)).pack(side='left')
    def poll():
        nonlocal busy
        if not events.empty():
            ok,msg=events.get();busy=False;go.config(state='normal');status.set(msg)
            if ok:os.startfile(msg)
            else:messagebox.showerror('导出失败',msg)
        win.after(250,poll)
    win.protocol('WM_DELETE_WINDOW',lambda:None if busy else win.destroy())
    preset=core.APP/'本届名单与奖项.xlsx'
    if preset.is_file():load('roster',preset)
    else:refresh()
    poll();win.mainloop()
