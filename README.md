# PSD Award Studio · 分组奖状制作工具

从 Excel 分组名单与获奖表批量制作可编辑的 PSD 奖状，并为每组生成 PDF。附开源调用的 Codex Skill 和已替换真实姓名的分层根模板。

Generate editable Photoshop certificates and group PDFs from Excel rosters and award tables. The repository is a standalone Codex skill with a layered PSD template and a Windows desktop app.

## 使用 / Usage

Windows + Adobe Photoshop desktop. Install Python 3.11+ and run:

    python -m pip install -r requirements.txt
    python scripts/studio.py

使用“导入分组名单”载入 XLSX 或 CSV，再导入获奖表。也可将两个表放在同一工作簿。每行可修改组号、片名、成员及奖项，落款支持年月或年月日。无需生成的组将奖项留空。源文件不带片名时，先在界面填入或载入已知对应关系。组织及活动文字随 PSD 模板设定。

Roster columns: 组别 (group), 作品名称 (film), 组员1… (members). Award columns: 奖项 (award) plus group number or film titles. Edit the matched rows and date before exporting. Outputs retain editable PSD text layers and include one PDF per awarded group.

Build the Windows executable with PowerShell: ./build.ps1. After building, open dist/AwardStudio.exe. The executable bundles the template and Python dependencies; desktop Photoshop and the template fonts must be installed separately. Choose Photoshop.exe on first use if it is not found. An optional photoshop-path.txt beside the executable can store its full path.

Install the Skill by copying this repository to ~/.codex/skills/psd-award-studio. See [SKILL.md](SKILL.md) for command-line use; [layered PSD](assets/template.psd), [sample roster](assets/roster.csv), [sample awards](assets/awards.csv).

## Version history / 版本记录

### 1.3.2

移动证书标题时，标题装饰线随之移动。导出的 PSD 保留 Photoshop 图层链接。
The title ornament follows the heading in previews and exports. The editable PSD preserves their Photoshop layer link.

### 1.3.1

内置模板以【主办单位】、【活动名称】、【发证单位】作为占位符。用[通用奖状方案](examples/通用奖状方案.json)和[制作单](examples/方案制作单.md)准备新方案。
The bundled PSD uses generic organizer, event and issuer placeholders. A reusable layout and production brief are included in examples/.

### 1.3.0
预览与导出共享 Photoshop 排版和合成结果，拖动框取自 PSD 实际图层边界。无边框窗口，全部七个证书文字层可编辑。支持拖动排版、精确坐标、字号、对齐、显隐、新增文本和 JSON 布局方案。
Photoshop-rendered previews and layer bounds; frameless window and full certificate text editor with drag placement, date and roster variables, custom text blocks and portable JSON layouts (--layout).

### 1.2.0
本地 Qt WebEngine 工作台，内置 Three.js 空间背景、减少动态效果选项、搜索与表单反馈。新图标用于桌面程序、窗口和品牌标识。首次启动需解压内置界面引擎。
Offline Qt WebEngine workspace with a bundled Three.js scene, reduced-motion support, accessible controls and a multi-size application icon. The renderer is bundled with the executable.

### 1.1.0
映印工作台：双击表格编辑分组，右侧可切换奖项、查看布局示意并设置日期；Photoshop 路径和自定义 PSD 在“导出设置”中。
New desktop workspace with a group editor, live layout preview and export settings.
模板已内置。可导入独立背景图片，按画布比例居中裁切铺满，透明区域衬白，导出为独立图层。
Bundled PSD with optional center-cropped image backgrounds. CLI: --background path/to/image.png.

### 1.0.0
首次发布：名单与奖项识别、可编辑核对、日期设置、PSD 副本与分组 PDF。
Initial release: roster and award matching, editable review, configurable dates, PSD copies and group PDFs.

