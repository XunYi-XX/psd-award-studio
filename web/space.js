'use strict';
(()=>{
const holder=document.querySelector('#space'),button=document.querySelector('#motion'),pref=matchMedia('(prefers-reduced-motion: reduce)');
let enabled=!pref.matches,renderer,frame=0,elapsed=0,previous=0,px=0,py=0;
let render=()=>{};
try{
 const T=THREE,scene=new T.Scene(),camera=new T.PerspectiveCamera(37,1,.1,100);
 renderer=new T.WebGLRenderer({alpha:true,antialias:true,powerPreference:'low-power'});renderer.setPixelRatio(Math.min(1.5,devicePixelRatio));holder.append(renderer.domElement);camera.position.z=8;
 const sculpture=new T.Group();scene.add(sculpture);
 [0,1,2,3].forEach((i)=>{const geo=new T.TorusGeometry(1.27+i*.075,.014+i*.003,8,100);
 const ring=new T.Mesh(geo,new T.MeshStandardMaterial({color:i%2?0xb79256:0xe0c795,metalness:.72,roughness:.35}));ring.rotation.set(.65+i*.18,.5+i*.19,i*.22);sculpture.add(ring)});
 const facet=new T.Mesh(new T.IcosahedronGeometry(.53,0),new T.MeshBasicMaterial({color:0xaac6a4,wireframe:true,transparent:true,opacity:.6}));sculpture.add(facet);
 scene.add(new T.HemisphereLight(0xffeace,0x56736d,2));const light=new T.DirectionalLight(0xffddb0,3);light.position.set(4,5,7);scene.add(light);
 const dots=new Float32Array(140*3);for(let i=0;i<dots.length;i+=3){dots[i]=(Math.random()-.5)*26;dots[i+1]=(Math.random()-.5)*7;dots[i+2]=-Math.random()*4}
 const geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.BufferAttribute(dots,3));const stars=new T.Points(geometry,new T.PointsMaterial({size:.024,color:0xe4d1a6,transparent:true,opacity:.66}));scene.add(stars);
 function resize(){const w=holder.clientWidth,h=holder.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();sculpture.position.set(camera.aspect*1.4,.53,-.3);renderer.render(scene,camera)}new ResizeObserver(resize).observe(holder);
 addEventListener('pointermove',e=>{px=(e.clientX/innerWidth-.5)*.24;py=(e.clientY/innerHeight-.5)*.15},{passive:true});
 render=(t)=>{sculpture.rotation.set(.12+py,Math.sin(t*.19)*.28+px,-.2+t*.05);facet.rotation.y=t*.25;stars.rotation.z=Math.sin(t*.11)*.012;renderer.render(scene,camera)};
}catch(e){holder.hidden=true}
function tick(now){if(!enabled||document.hidden||!renderer)return;if(now-previous>=32){elapsed+=Math.min((now-previous)/1000,.08);previous=now;render(elapsed)}frame=requestAnimationFrame(tick)}
function apply(){cancelAnimationFrame(frame);document.body.classList.toggle('still',!enabled);button.textContent='空间动效 · '+(enabled?'开':'关');button.setAttribute('aria-pressed',String(enabled));previous=performance.now();if(enabled)tick(previous);else render(elapsed)}
button.onclick=()=>{enabled=!enabled;apply()};pref.onchange=()=>{enabled=!pref.matches;apply()};document.addEventListener('visibilitychange',apply);apply();
const observer=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('revealed');observer.unobserve(e.target)}}));document.querySelectorAll('.glass,.intro').forEach(el=>observer.observe(el))
})();
