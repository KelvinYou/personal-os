"use client";
import dynamic from 'next/dynamic';
import type { OfficeSkill } from '@/lib/office-room';
const Preview=dynamic(()=>import('./character-preview'),{ssr:false,loading:()=> <p>Opening character preview…</p>});
export function CharacterPreviewLoader({roster}:{roster:OfficeSkill[]}){return <Preview roster={roster}/>;}
