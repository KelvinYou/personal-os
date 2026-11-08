import path from 'node:path';
import Link from 'next/link';
import { loadOfficeSkills } from '@/lib/office-skills';
import { CharacterPreviewLoader } from '@/components/office/character-preview-loader';
import { DataState } from '@/components/shared/data-state';
import '../office.css';
export const dynamic='force-dynamic';
export const metadata={title:'The cast · Personal OS',description:'Close-up role wardrobes for the garden village.'};
export default function CharactersPage(){
 try{return <CharacterPreviewLoader roster={loadOfficeSkills(path.resolve(process.cwd(),'..'))}/>;}
 catch{return <main id="main-content"><DataState state="error" title="Character roster unavailable" description="The skill catalog could not be read."/><Link href="/office">Back to office</Link></main>;}
}
