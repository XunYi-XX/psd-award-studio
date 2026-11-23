#target photoshop
(function () {
 var oldDialogs=app.displayDialogs, oldUnits=app.preferences.rulerUnits, work=null;
 function find(doc, test) {
   for(var i=0;i<doc.artLayers.length;i++){var l=doc.artLayers[i];if(l.kind==LayerKind.TEXT && test(l))return l;}
   throw Error("模板缺少必需文字层");
 }
 function write(file,body){var f=new File(file);f.encoding='UTF8';f.open('w');f.write(body);f.close();}
 function bounds(l){var b=l.bounds;return [b[0].as('px'),b[1].as('px'),b[2].as('px'),b[3].as('px')];}
 function fit(l,limit){var b=bounds(l);if(b[2]-b[0]>limit){l.textItem.horizontalScale=l.textItem.horizontalScale*limit/(b[2]-b[0]);}}
 function underline(doc,l){
   var s=stringIDToTypeID,r=new ActionReference();r.putProperty(s('property'),s('textKey'));r.putIdentifier(s('layer'),l.id);
   var td=executeActionGet(r).getObjectValue(s('textKey')),base=td.getList(s('textStyleRange')).getObjectValue(0),arr=new ActionList(),str=l.textItem.contents;
   function add(a,z,line){if(a>=z)return;var d=new ActionDescriptor(),style=base.getObjectValue(s('textStyle'));style.putEnumerated(s('underline'),s('underline'),s(line?'underlineOnLeftInVertical':'underlineOff'));d.putInteger(s('from'),a);d.putInteger(s('to'),z);d.putObject(s('textStyle'),s('textStyle'),style);arr.putObject(s('textStyleRange'),d);}
   var first=str.indexOf('：')+2,split=str.indexOf('\r');
   add(0,first,false);if(split<0)add(first,str.length,true);else{add(first,split,true);add(split,split+12,false);add(split+12,str.length,true);}
   td.putList(s('textStyleRange'),arr);var cmd=new ActionDescriptor(),ref=new ActionReference();ref.putIdentifier(s('textLayer'),l.id);cmd.putReference(s('null'),ref);cmd.putObject(s('to'),s('textLayer'),td);executeAction(s('set'),cmd,DialogModes.NO);
 }
 try {
   app.displayDialogs=DialogModes.NO;app.preferences.rulerUnits=Units.PIXELS;
   for(var i=0;i<jobs.length;i++){
     var j=jobs[i];work=app.open(new File(j.file));
     var group=find(work,function(l){return l.name=='组别';}),mem=find(work,function(l){return l.name=='小组成员';});
     var body=find(work,function(l){return l.textItem.contents.indexOf('作品《')>=0;});
     var prize=find(work,function(l){return l.textItem.contents.indexOf('被评为')==0;});
     var date=find(work,function(l){return /\r\d{4}年/.test(l.textItem.contents);});
     group.textItem.contents=j.group+'：';group.name='组别';
     body.textItem.contents=body.textItem.contents.replace(/作品《[^》]*》/,function(){return '作品《'+j.title+'》';});fit(body,2895);body.name='活动正文';
     prize.textItem.contents='被评为“'+j.award+'”';fit(prize,2840);var b=bounds(prize);prize.translate(UnitValue(work.width.as('px')/2-(b[0]+b[2])/2,'px'),UnitValue(0,'px'));prize.name='奖项';
     date.textItem.contents=date.textItem.contents.split('\r')[0]+'\r'+j.date;date.name='落款日期';
     mem.textItem.contents=j.members;underline(work,mem);fit(mem,2770);mem.name='小组成员';
     work.save();
     if(j.jpg){var opt=new JPEGSaveOptions();opt.quality=12;work.saveAs(new File(j.jpg),opt,true,Extension.LOWERCASE);}
     work.close(SaveOptions.DONOTSAVECHANGES);work=null;
   }
   write(done,'OK');
 }catch(e){if(work)work.close(SaveOptions.DONOTSAVECHANGES);write(done,'第 '+(i+1)+' 张：'+e.toString()+' ('+e.line+')');}
 finally{app.displayDialogs=oldDialogs;app.preferences.rulerUnits=oldUnits;}
})();
