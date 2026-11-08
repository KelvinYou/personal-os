"use client";

import { buttonClass } from "@/components/ui/button";
import { useMemo, useRef, useState, useEffect } from "react";
import Link from "next/link";
import { Canvas, useThree } from "@react-three/fiber";
import { ContactShadows, OrbitControls } from "@react-three/drei";
import { type OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { Select } from "@/components/shared/select";
import { characterWardrobe } from "@/lib/office-character";
import type { OfficeSkill } from "@/lib/office-room";
import { OfficePerson } from "./office-character-model";

type Sample = { id: string; label: string; host?: boolean };
const samples: Sample[] = [{ id: 'coach-planner', label: 'Coach' }, { id: 'git-commit', label: 'Maker' }, { id: 'learning-agent', label: 'Study' }, { id: 'wealth-manager', label: 'Wealth' }, { id: 'travel-plan', label: 'Travel' }, { id: 'kelvin.ai', label: 'Host', host: true }];
function PreviewCamera({ yaw, count }: { yaw: number; count: number }) {
  const { camera, size, invalidate } = useThree();
  const controls = useRef<OrbitControlsImpl>(null);
  const zoom = Math.min(size.width / (count === 1 ? 4.3 : 15.5), size.height / 3.6);
  useEffect(() => { camera.position.set(Math.sin(yaw) * 12, 2.9, Math.cos(yaw) * 12); camera.zoom = zoom; camera.updateProjectionMatrix(); controls.current?.target.set(0, 1.15, 0); controls.current?.update(); invalidate(); }, [camera, zoom, yaw, invalidate]);
  return <OrbitControls ref={controls} target={[0, 1.15, 0]} minZoom={zoom * .7} maxZoom={zoom * 3} minPolarAngle={.4} maxPolarAngle={Math.PI / 2.1} enableDamping={false} />;
}
export default function CharacterPreview({ roster }: { roster: OfficeSkill[] }) {
  const [selected, setSelected] = useState(() => typeof window !== 'undefined' && window.innerWidth < 760 ? 'coach-planner' : 'all'), [pose, setPose] = useState<'standing' | 'seated'>('standing'), [yaw, setYaw] = useState(0);
  const figures = useMemo(() => selected === 'all' ? samples.filter(item => item.host || roster.some(skill=>skill.id===item.id)) : [{ id: selected, label: roster.find(skill=>skill.id===selected)?.name ?? 'Host', host: selected === 'kelvin.ai' }], [selected, roster]);
  return <main className="office-character-page" id="main-content">
    <header className="office-character-heading"><div><p className="office-eyebrow">GARDEN VILLAGE / THE CAST</p><h1>A wardrobe for every role.</h1><p>Training clothes, studio layers and everyday details. The same characters you meet in the village.</p></div><Link href="/office" className={buttonClass({ variant: "outline" })}>Back to office ↗</Link></header>
    <section className="office-character-controls" aria-label="Character preview controls">
      <div><label htmlFor="character-choice">Character</label><Select id="character-choice" value={selected} onValueChange={setSelected} options={[{ value:'all', label:'Compare role styles' },...roster.map(skill=>({value:skill.id,label:skill.name})),{value:'kelvin.ai',label:'kelvin.ai · Host'}]} /></div>
      <div className="office-character-switch" aria-label="Preview pose">{(['standing','seated'] as const).map(value=><button key={value} aria-pressed={pose===value} onClick={()=>setPose(value)}>{value==='standing'?'Standing':'Seated'}</button>)}</div>
      <div className="office-character-switch" aria-label="Preview angle">{[{v:0,label:'Front'},{v:Math.PI/2,label:'Side'},{v:Math.PI,label:'Back'}].map(item=><button key={item.label} aria-pressed={yaw===item.v} onClick={()=>setYaw(item.v)}>{item.label}</button>)}</div>
    </section>
    <section className="office-character-stage" aria-label="3D character wardrobe preview">
      <Canvas orthographic camera={{position:[0,2.9,12],zoom:70,near:.1,far:100}} dpr={[1,1.5]} frameloop="demand" shadows>
        <color attach="background" args={['#eee9de']} /><ambientLight intensity={.8} /><hemisphereLight args={['#fff5de','#c0b39b',1]} /><directionalLight position={[-4,8,6]} intensity={2.3} castShadow shadow-mapSize={[1024,1024]} shadow-camera-left={-9} shadow-camera-right={9} shadow-camera-top={5} shadow-camera-bottom={-5}/>
        {figures.map((item,index)=>{const x=figures.length===1?0:(index-(figures.length-1)/2)*2.3;return <group key={item.id} position={[x,0,0]}>
          <OfficePerson session={{session_id:item.host?'kelvin.ai':`skill:${item.id}`,state:'idle'}} skillId={item.host?undefined:item.id} host={item.host} preview={pose} at={[0,pose==='standing'?.82:.62,0]} selected={false} animate={false} onSelect={()=>{}} />
          {pose==='seated'&&<group><mesh position={[0,.76,-.02]} castShadow><boxGeometry args={[.8,.12,.7]}/><meshStandardMaterial color="#a0ad94"/></mesh><mesh position={[0,1.15,-.34]} castShadow><boxGeometry args={[.8,.7,.1]}/><meshStandardMaterial color="#a0ad94"/></mesh>{[-.3,.3].flatMap(a=>[-.26,.26].map(b=><mesh key={`${a}:${b}`} position={[a,.36,b]}><boxGeometry args={[.06,.72,.06]}/><meshStandardMaterial color="#9e886b"/></mesh>))}</group>}
        </group>})}
        <ContactShadows position={[0,0,0]} opacity={.25} scale={18} blur={2.4} far={3} frames={1}/><PreviewCamera yaw={yaw} count={figures.length}/>
      </Canvas>
    </section>
    <section className="office-character-captions" aria-label="Wardrobe styles">{figures.map(item=><div key={item.id}><h2>{item.label}</h2><p>{characterWardrobe(item.host?'kelvin.ai':`skill:${item.id}`,item.host?undefined:item.id,!!item.host).label}</p></div>)}</section>
    <p className="office-character-note">Appearance preview only. Drag to orbit and scroll to zoom. Clothing does not indicate live work or activity.</p>
  </main>;
}
