import Editor,{loader} from '@monaco-editor/react';
import {useEffect,useRef} from 'react';
import * as monaco from 'monaco-editor';
import EditorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';
import JsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker';
import TsWorker from 'monaco-editor/esm/vs/language/typescript/ts.worker?worker';
// Bundle workers locally; no CDN requests or repository code sent to an editor service.
(self as unknown as {MonacoEnvironment:unknown}).MonacoEnvironment={getWorker(_:string,label:string){return label==='json'?new JsonWorker():['typescript','javascript'].includes(label)?new TsWorker():new EditorWorker();}};
loader.config({monaco});
const options={readOnly:true,minimap:{enabled:false},fontSize:13,padding:{top:16},scrollBeyondLastLine:false,automaticLayout:true};
export function CodeEditor({path,content}:{path:string;content:string}){return <Editor height="520px" theme="vs-dark" path={path} value={content} options={options}/>;}
export function CodeDiff({original,modified}:{original:string;modified:string}){
 const host=useRef<HTMLDivElement>(null);
 const models=useRef<{original:monaco.editor.ITextModel;modified:monaco.editor.ITextModel}|null>(null);
 useEffect(()=>{
   const editor=monaco.editor.createDiffEditor(host.current!,{...options,theme:'vs-dark',renderSideBySide:true});
   const pair={original:monaco.editor.createModel(''),modified:monaco.editor.createModel('')};
   models.current=pair;editor.setModel(pair);
   return()=>{editor.setModel(null);editor.dispose();pair.original.dispose();pair.modified.dispose();models.current=null;};
 },[]);
 useEffect(()=>{models.current?.original.setValue(original);models.current?.modified.setValue(modified)},[original,modified]);
 return <div ref={host} style={{height:420}} aria-label="Patch comparison"/>;
}
