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
     if(j.background){
       var anchor=null;
       for(var k=0;k<work.layers.length;k++){
         var existing=work.layers[k];
         if(existing.name!='标题装饰线' && (existing.typename!='ArtLayer'||existing.kind!=LayerKind.TEXT)){anchor=existing;break;}
       }
       if(!anchor)throw Error("模板缺少背景层");
       var photo=app.open(new File(j.background)),layer;
       try{layer=photo.activeLayer.duplicate(work,ElementPlacement.PLACEATBEGINNING);}
       finally{photo.close(SaveOptions.DONOTSAVECHANGES);}
       app.activeDocument=work;layer.move(anchor,ElementPlacement.PLACEBEFORE);layer.name='自定义背景';
       var pos=bounds(layer);layer.translate(UnitValue(-pos[0],'px'),UnitValue(-pos[1],'px'));
     }
     var group=find(work,function(l){return l.name=='组别';}),mem=find(work,function(l){return l.name=='小组成员';});
     var body=find(work,function(l){return l.textItem.contents.indexOf('作品《')>=0;});
     var prize=find(work,function(l){return l.textItem.contents.indexOf('被评为')==0;});
     var date=find(work,function(l){return /\r\d{4}年/.test(l.textItem.contents);});
     group.textItem.contents=j.group+'：';group.name='组别';
     body.textItem.contents=body.textItem.contents.replace(/作品《[^》]*》/,function(){return '作品《'+j.title+'》';});fit(body,2895);body.name='活动正文';
     prize.textItem.contents='被评为“'+j.award+'”';fit(prize,2840);var b=bounds(prize);prize.translate(UnitValue(work.width.as('px')/2-(b[0]+b[2])/2,'px'),UnitValue(0,'px'));prize.name='奖项';
     date.textItem.contents=date.textItem.contents.split('\r')[0]+'\r'+j.date;date.name='落款日期';
     mem.textItem.contents=j.members;underline(work,mem);fit(mem,2770);mem.name='小组成员';
     var known={group:group,body:body,award:prize,members:mem,signature:date};
     if(j.map||j.layout){known.heading=find(work,function(l){return l.name=='荣誉证书';});known.note=find(work,function(l){return l.name=='名单排序说明';});}
     // Older bundled templates keep the title ornament inside the border group.
     var title=null,rule=null;
     try{title=work.artLayers.getByName('荣誉证书');}catch(noTitle){}
     if(title){
       try{rule=work.artLayers.getByName('标题装饰线');}catch(noRule){}
       if(!rule){
         try{
           var ornaments=work.layerSets.getByName('背景').artLayers;
           for(var oi=0;oi<ornaments.length;oi++){
             if(ornaments[oi].id==115 && ornaments[oi].name=='矢量智能对象'){rule=ornaments[oi];break;}
           }
         }catch(noBorder){}
       }
     }
     var originalTitle,originalRule;
     if(rule){
       var peers=rule.linkedLayers;
       for(var li=0;li<peers.length;li++){if(peers[li].id==title.id){rule.unlink();break;}}
       if(rule.parent.typename!='Document'){rule.move(title,ElementPlacement.PLACEAFTER);rule.name='标题装饰线';}
       originalTitle=bounds(title);originalRule=bounds(rule);
     }
     if(j.layout){
       var ls=j.layout.layers,W=work.width.as('px'),H=work.height.as('px');

       var tokens={'组号':String(j.n),'组别':j.group,'作品名':j.title,'奖项':j.award,'日期':j.date,
                   '组员':j.members.replace(/^小组成员：\s*/, '').replace(/\r +/g,'')};
       for(var key in ls){if(!ls.hasOwnProperty(key))continue;
         var cfg=ls[key],target=known[key];

         if(!target){target=group.duplicate();target.name='自定义文本 '+key;known[key]=target;}
         target.visible=cfg.visible;if(!cfg.visible)continue;
         var value=cfg.text.replace(/\{(组号|组别|作品名|奖项|日期|组员)\}/g,function(m,k){
           if(k=='组员'&&key=='members')return j.members.replace(/^小组成员：\s*/, '');
           return tokens[k];}).replace(/\r?\n/g,'\r');
         if(!value){target.visible=false;continue;}
         target.textItem.contents=value;
         target.textItem.size=UnitValue(cfg.pt,'pt');
         target.textItem.justification=cfg.align=='center'?Justification.CENTER:(cfg.align=='right'?Justification.RIGHT:Justification.LEFT);
         if(key=='members'&&value.indexOf('小组成员： ')==0)underline(work,target);
         fit(target,W*cfg.width/100);
         var bb=bounds(target),anchorX=cfg.align=='center'?(bb[0]+bb[2])/2:(cfg.align=='right'?bb[2]:bb[0]);
         target.translate(UnitValue(W*cfg.x/100-anchorX,'px'),UnitValue(H*cfg.y/100-bb[1],'px'));
       }
     }
     if(rule){
       if(!title.visible){rule.visible=false;}
       else if(j.layout && j.layout.layers.heading){
         var tb=bounds(title),rb=bounds(rule);
         // Preserve the original optical centering and gap below the lettering.
         var dx=(tb[0]+tb[2]-originalTitle[0]-originalTitle[2])/2+originalRule[0]-rb[0];
         var dy=tb[3]-originalTitle[3]+originalRule[1]-rb[1];
         if(dx || dy){
           rule.translate(UnitValue(dx,'px'),UnitValue(dy,'px'));
         }
       }
       rule.link(title);
     }
     if(j.map){
       var lines=[];for(var id in known){if(known.hasOwnProperty(id)&&known[id].visible){var box=bounds(known[id]);lines.push(id+','+box.join(','));}}
       write(j.map,work.width.as('px')+','+work.height.as('px')+'\n'+lines.join('\n'));
     }else{work.save();}
     if(j.jpg){work.flatten();work.convertProfile("sRGB IEC61966-2.1",Intent.RELATIVECOLORIMETRIC,true,false);var opt=new JPEGSaveOptions();opt.quality=12;work.saveAs(new File(j.jpg),opt,true,Extension.LOWERCASE);}
     work.close(SaveOptions.DONOTSAVECHANGES);work=null;
   }
   write(done,'OK');
 }catch(e){if(work)work.close(SaveOptions.DONOTSAVECHANGES);write(done,'第 '+(i+1)+' 张：'+e.toString()+' ('+e.line+')');}
 finally{app.displayDialogs=oldDialogs;app.preferences.rulerUnits=oldUnits;}
})();

