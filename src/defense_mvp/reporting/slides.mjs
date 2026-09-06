// Bundled Artifact Tool authoring and final-PPTX reimport rendering.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';

const [dataPath, root, modules, skill, python] = process.argv.slice(2);
process.env.RUNTIME_NODE_MODULES=modules;
process.env.RUNTIME_NODE=process.execPath;
process.env.RUNTIME_PYTHON=python;
const {Presentation, PresentationFile, FileBlob} = await import(pathToFileURL(path.join(modules,'@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const {finalizePresentation} = await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const data = JSON.parse(await fs.readFile(dataPath,'utf8'));
const cfg=data.config, font=cfg.font_family;
const presentation=Presentation.create({slideSize:{width:1280,height:720}});
const finalPath=path.join(root,'slides/DEFENSE_MVP_D5_DRAFT.pptx');
const build=path.join(root,'build');
await fs.mkdir(build,{recursive:true});
await fs.mkdir(path.dirname(finalPath),{recursive:true});
await fs.mkdir(path.join(root,'slides/rendered'),{recursive:true});
const placements=[];
function text(slide,value,x,y,w,h,size=28,bold=false,color='#172B3A') {
  const shape=slide.shapes.add({geometry:'textbox',name:`text-${placements.length}`,position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  shape.text=value;
  shape.text.style={typeface:font,fontSize:size,bold,color,autoFit:'none',wrap:true};
  placements.push({slide:data.slides.indexOf(slide)+1,text:value,x,y,w,h});
  return shape;
}
function line(slide,x,y,w,color='#A5B3BF') {
  return slide.shapes.add({geometry:'line',position:{left:x,top:y,width:w,height:0},fill:'none',line:{fill:color,width:1.5}});
}
async function picture(slide,relative,x,y,w,h,alt) {
  slide.images.add({blob:new Uint8Array(await fs.readFile(path.join(root,relative))),contentType:'image/png',alt,fit:'contain',position:{left:x,top:y,width:w,height:h}});
}
for (const d of data.slides) {
  const slide=presentation.slides.add(); slide.background.fill='#FFFFFF';
  if(d.index===1) {
    text(slide,'Defense MVP / D5 初稿',72,64,1100,45,24,false,'#526778');
    text(slide,d.lead,72,170,1120,190,54,true);
    d.body.forEach((v,i)=>text(slide,v,76,421+i*58,1120,50,31,false));
  } else {
    text(slide,d.title,64,40,1150,72,42,true);
    if(d.kind==='scope') {
      text(slide,d.lead,72,164,1120,80,54,true,'#006B9E');
      text(slide,d.body[0],72,292,710,58,38,true);
      text(slide,d.body[1],72,390,710,58,38,true);
      text(slide,d.body[2],850,300,350,66,28);
      text(slide,d.body[3],850,398,350,66,28);
      text(slide,'主表严格保留定量范围',72,520,1120,60,30);
    } else if(d.kind==='system') {
      const positions=[[72,182],[370,182],[685,182],[1000,182],[940,345],[555,345],[120,345]];
      d.flow.forEach((v,i)=>{const [x,y]=positions[i];text(slide,v,x,y,215,90,28,true);if(i<3)text(slide,'→',[295,610,915][i],y,55,55,32);});
      text(slide,'↓',1060,275,70,65,34);text(slide,'←',810,345,70,65,34);text(slide,'←',395,345,70,65,34);
      d.body.forEach((v,i)=>text(slide,i===2?v.replace('，','，\n'):v,72+i*390,520,365,85,26));
    } else if(d.kind==='metrics') {
      d.metrics.forEach((v,i)=>{
        const y=153+i*117;
        text(slide,v[0],70,y,285,58,31,true,'#006B9E');
        text(slide,v[1],363,y,820,52,27);
        text(slide,v[2],363,y+53,820,47,25,false,'#526778');
      });
    } else if(d.kind==='selection') {
      text(slide,d.lead,72,162,535,155,38,true,'#006B9E');
      d.body.forEach((v,i)=>text(slide,v,650,170+i*92,545,76,29));
      text(slide,'N=1 baseline\nEqual-linear N=4\nConstrained Pareto/max-min N=4',75,377,535,180,28);
    } else if(d.kind==='blind') {
      text(slide,d.lead,72,154,1140,80,42,true,'#006B9E');
      d.body.forEach((v,i)=>text(slide,v,85,290+i*72,1110,60,30));
    } else if(d.kind==='results') {
      await picture(slide,'report/figures/overall-ci.png',30,151,820,462,'描述性总体偏好与95% CI');
      for(let i=0;i<2;i++) {
        const row=data.main.filter(r=>r.field==='overall')[i];const y=197+i*208;
        text(slide,i===0?'对 N=1 baseline':'对 Linear N=4',880,y,350,46,29,true);
        text(slide,`W/L/T/U  ${row.wins}/${row.losses}/${row.ties}/${row.uncertain}`,880,y+56,350,46,28);
        text(slide,`n=${row.total}    tie-aware ${Number(row.tie_aware_win_rate).toFixed(3)}`,880,y+110,350,65,26);
      }
    } else if(d.kind==='cases') {
      for(let i=0;i<3;i++) {
        const x=48+i*408;
        text(slide,d.case_labels[i],x,153,390,55,32,true);
        await picture(slide,`report/cases/media/case-${i+1}-sheet.png`,x,221,386,290,d.case_labels[i]+'：输入/Proposed/对照，各四帧');
        text(slide,'由上至下：输入 / Proposed / 对照',x,527,390,55,21,false,'#526778');
      }
      text(slide,d.body[0],65,591,1130,46,26);
    } else if(d.kind==='limitations') {
      await picture(slide,'report/figures/agreement.png',24,157,764,430,'五字段agreement与kappa，manual n=32');
      d.body.forEach((v,i)=>text(slide,v,820,184+i*103,400,92,27,i===0));
    } else if(d.kind==='next') {
      text(slide,d.lead,72,157,1110,75,44,true,'#006B9E');
      d.body.forEach((v,i)=>text(slide,v,85,298+i*77,1120,66,30));
    }
  }
  line(slide,64,651,1150);
  text(slide,d.footer,68,668,1138,38,19,false,'#526778');
  slide.speakerNotes.textFrame.setText(d.notes+'\n来源：D5 report-data.json 与 slide-data.json；D4 verified analysis，D2 frozen artifacts。');
}
const candidatePath=path.join(build,'candidate.pptx');
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
const validation=await finalizePresentation({
  workspaceDir:path.resolve(root),candidatePath,finalPath,pythonExecutable:path.resolve(python),
  integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],
  explicitTotalSlideCount:10,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],
  fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,
  receiptPath:path.join(build,'presentation-validation.json'),
});
const finalDeck=await PresentationFile.importPptx(await FileBlob.load(finalPath));
const inspection=await finalDeck.inspect({kind:'slide,textbox,image,shape,layout',maxChars:200000});
await fs.writeFile(path.join(build,'presentation-inspect.ndjson'),inspection.ndjson);
const hashes={};
for(let i=0;i<10;i++) {
  const slide=finalDeck.slides.items[i];
  const png=await finalDeck.export({slide,format:'png',scale:1});
  const bytes=new Uint8Array(await png.arrayBuffer());
  const name=`slide-${String(i+1).padStart(2,'0')}.png`;
  await fs.writeFile(path.join(root,'slides/rendered',name),bytes);
  hashes[name]=createHash('sha256').update(bytes).digest('hex');
  const layout=await slide.export({format:'layout'});
  await fs.writeFile(path.join(build,`slide-${String(i+1).padStart(2,'0')}.layout.json`),await layout.text());
}
const packageData=JSON.parse(await fs.readFile(path.join(modules,'@oai/artifact-tool/package.json'),'utf8'));
const receipt={status:'rendered-awaiting-visual-review',page_count:10,renderer:'@oai/artifact-tool final PPTX reimport',
  artifact_tool:packageData.version,node:process.version,font_family:font,slide_data_sha256:createHash('sha256').update(await fs.readFile(dataPath)).digest('hex'),
  pptx_sha256:createHash('sha256').update(await fs.readFile(finalPath)).digest('hex'),render_sha256:hashes,
  reproducibility:'semantic inputs and actual SHA; PPTX bytes may include unstable internal timestamps',
  validation_receipt:'../build/presentation-validation.json',validation_status:validation.status??'completed'};
await fs.writeFile(path.join(root,'slides/slides-receipt.json'),JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify({status:'rendered',pages:10,pptx_sha256:receipt.pptx_sha256}));
// Parent verifies all completed output hashes, then terminates this idle renderer.
// Keeping the event loop alive avoids the bundled Windows canvas destructor crash.
setInterval(()=>{},60000);
