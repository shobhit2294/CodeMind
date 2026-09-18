type Node={id:string;path:string;kind:string};
type Edge={source:string;target:string;kind:string};
export default function Graph({graph,onOpen}:{graph:{nodes:Node[];edges:Edge[]};onOpen:(p:string)=>void}){
 const files=graph.nodes.filter(n=>n.kind==='file').slice(0,24);
 const cols=3,rows=Math.max(1,Math.ceil(files.length/cols));
 const positions=Object.fromEntries(files.map((n,i)=>[n.id,{x:24+(i%cols)*280,y:30+Math.floor(i/cols)*90}]));
 return <div className="graph"><div className="graph-note">FILE DEPENDENCIES <span>Click a module to inspect · first 24 files</span></div><svg viewBox={`0 0 840 ${rows*90+30}`} role="img" aria-label="Repository import graph">
 {graph.edges.filter(e=>e.kind==='IMPORTS'&&positions[e.source]&&positions[e.target]).map((e,i)=>{const a=positions[e.source],b=positions[e.target];return <path key={i} d={`M ${a.x+125} ${a.y+24} C ${a.x+125} ${a.y+80},${b.x+125} ${b.y-40},${b.x+125} ${b.y+24}`} fill="none" stroke="#419387" strokeWidth="2"/>})}
 {files.map(n=>{const p=positions[n.id];return <g key={n.id} transform={`translate(${p.x},${p.y})`} role="button" tabIndex={0} onClick={()=>onOpen(n.path)} onKeyDown={e=>{if(e.key==='Enter')onOpen(n.path)}}><rect width="245" height="48" rx="8" fill="#1c2b2d" stroke="#3f595a"/><circle cx="16" cy="24" r="4" fill="#76e5cd"/><text x="29" y="29" fill="#d8e5e4" fontSize="12">{n.path.length>28?'…'+n.path.slice(-27):n.path}</text><title>{n.path}</title></g>})}
 </svg>{!graph.edges.some(e=>e.kind==='IMPORTS')&&<p className="muted">No resolvable file imports in this snapshot.</p>}</div>
}
