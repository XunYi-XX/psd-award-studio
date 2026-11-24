"""Native file dialogs and Photoshop bridge for the local WebEngine workspace."""
import base64
import datetime
import io
import json
import os
import threading
from pathlib import Path

from PIL import Image, ImageOps
from PySide6.QtCore import QObject, QUrl, Signal, Slot, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings

class Bridge(QObject):
    result = Signal(str)
    proof = Signal(str)

    def __init__(self, core, parent):
        super().__init__(parent)
        self.core, self.host = core, parent
        self.render_lock=threading.Lock()
        self.template, self.background = core.ASSET, ''
        self.ps, self.output, self.busy = core.default_ps(), '', False

    def load(self, path, mode, rows):
        data = self.core.sheets(path)
        groups = {r['n']: [r['title'], r['names']] for r in rows}
        if mode == 'roster':
            groups = self.core.roster(data, {n: info[0] for n, info in groups.items()})
        awards = self.core.awards(data, groups)
        if mode == 'awards' and not awards:
            raise ValueError('未识别到奖项，请核对表头和作品名。')
        return [dict(n=n, title=t, names=m, awards=awards.get(n, [])) for n,(t,m) in sorted(groups.items())]

    @Slot(str, str, result=str)
    def call(self, action, payload):
        try:
            body = json.loads(payload)
            if action == 'init':
                preset = self.core.APP/'本届名单与奖项.xlsx'
                now = datetime.date.today()
                value = dict(rows=self.load(preset,'roster',[]) if preset.is_file() else [],
                             date=f'{now.year}年{now.month}月', ps=self.ps)
            elif action in ('saveLayout','loadLayout'):
                from layout_spec import validate, read
                if action=='saveLayout':
                    layout=validate(body)
                    path,_=QFileDialog.getSaveFileName(self.host,'保存证书布局','证书布局.json','布局文件 (*.json)')
                    if not path:return 'null'
                    Path(path).write_text(json.dumps(layout,ensure_ascii=False,indent=2),encoding='utf8')
                    value=True
                else:
                    path,_=QFileDialog.getOpenFileName(self.host,'载入证书布局','','布局文件 (*.json)')
                    if not path:return 'null'
                    value=read(path)
            elif action == 'window':
                command=body['command']
                if command=='minimize':self.host.showMinimized()
                elif command=='fullscreen':
                    if self.host.isFullScreen():self.host.showNormal()
                    else:self.host.showFullScreen()
                elif command=='restore' and self.host.isFullScreen():self.host.showNormal()
                elif command=='move' and not self.host.isFullScreen():self.host.windowHandle().startSystemMove()
                elif command=='close':
                    if self.busy:raise ValueError('请等待当前奖状导出完成后关闭。')
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(50,self.host.close)
                value=self.host.isFullScreen()
            elif action == 'openOutput':
                if self.output: os.startfile(self.output)
                value = True
            elif action == 'preview':
                import tempfile
                r=body['row'];n=r['n'];g={n:[r['title'],r['names']]};a={n:[body['award'] or '待填写奖项']}
                jobs=self.core.plan(self.core.text_rows(g,a),body['date'])
                args=self.template,self.ps,self.background,body.get('layout')
                ticket=body['ticket']
                def proof():
                    try:
                        template,ps,bg,layout=args
                        with self.render_lock,tempfile.TemporaryDirectory(prefix='award-proof-') as tmp:
                            v=self.core.export(jobs,template,ps,tmp,bg,layout,preview=True)
                    except Exception as error:v=dict(error=str(error))
                    self.proof.emit(json.dumps(dict(ticket=ticket,**v)))
                threading.Thread(target=proof,daemon=True).start()
                value=True
            elif action == 'export':
                if self.busy: raise ValueError('正在导出')
                rows = body['rows']
                if len({r['n'] for r in rows}) != len(rows): raise ValueError('组号重复')
                groups = {r['n']:[r['title'],r['names']] for r in rows}
                awards = {r['n']:r['awards'] for r in rows}
                jobs = self.core.plan(self.core.text_rows(groups,awards),body['date'])
                if not Path(self.ps).is_file(): raise ValueError('请先在设置中选择 Photoshop.exe')
                dest = QFileDialog.getExistingDirectory(self.host,'选择输出文件夹')
                if not dest:return 'null'
                self.busy = True
                args = jobs,self.template,self.ps,dest,self.background,body.get("layout")
                def run():
                    try:
                        with self.render_lock:self.output = str(self.core.export(*args))
                        message = dict(ok=True, path=self.output)
                    except Exception as error:
                        message = dict(error=str(error))
                    self.busy = False
                    self.result.emit(json.dumps(message))
                threading.Thread(target=run,daemon=True).start()
                value = True
            elif action == 'reset':
                self.background='';value=True
            else:
                filters={'ps':'Photoshop (Photoshop.exe)','template':'PSD (*.psd)','background':'背景图片 (*.jpg *.jpeg *.png *.webp *.tif *.tiff *.bmp)','roster':'表格 (*.xlsx *.csv)','awards':'表格 (*.xlsx *.csv)'}
                path,_ = QFileDialog.getOpenFileName(self.host,'选择文件','',filters[action])
                if not path:return 'null'
                if action in ('roster','awards'):value=self.load(path,action,body['rows'])
                elif action=='background':
                    with Image.open(path) as src:
                        img=ImageOps.fit(ImageOps.exif_transpose(src).convert('RGBA'),(840,594))
                        paper=Image.new('RGB',img.size,'white');paper.paste(img,mask=img.getchannel('A'))
                        buf=io.BytesIO();paper.save(buf,'JPEG',quality=90)
                    self.background=path
                    value=dict(name=Path(path).name,url='data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode())
                elif action=='ps':self.ps=path;value=path
                else:self.template=Path(path);value=path
            return json.dumps(value,ensure_ascii=False)
        except Exception as error:return json.dumps(dict(error=str(error)),ensure_ascii=False)

def launch(core):
    app=QApplication.instance() or QApplication([])
    app.setWindowIcon(QIcon(str(core.ROOT/'assets/awardstudio.ico')))
    class Window(QMainWindow):
        def closeEvent(self,event):
            if bridge.busy:event.ignore()
            else:event.accept()
    win=Window();win.setWindowTitle('映印 · 奖状工作台')
    win.setWindowFlag(Qt.WindowType.FramelessWindowHint,True)
    view=QWebEngineView();win.setCentralWidget(view)
    view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
    view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,False)
    channel=QWebChannel(view.page());bridge=Bridge(core,win)
    channel.registerObject('studio',bridge);view.page().setWebChannel(channel)
    view.load(QUrl.fromLocalFile(str(core.ROOT/'web/index.html')))
    size=app.primaryScreen().availableGeometry();win.resize(min(1320,size.width()-30),min(840,size.height()-25))
    win.show();app.exec()

