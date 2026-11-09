// Cosmetic identities only. Never infer a role, person or parent from a nickname.
// User-selected Malaysian Chinese office cast; this is an art preset, not source identity.
const firstNames = ["Jun Wei", "Mei Lin", "Wen Kai", "Xin Yi", "Zhi Hao", "Jia Yi", "Yi Chen", "Yu Ting", "Wei Jie", "Pei Shan", "Jun Hao", "Li Wen", "Yi Fan", "Hui Wen", "Ming Han", "Yi Xuan"];
const lastNames = ["Tan", "Lim", "Lee", "Wong", "Ng", "Chan", "Lau", "Chong", "Teoh", "Goh", "Yap", "Chin", "Loo", "Koh", "Chew", "Low"];
export function characterProfile(id: string) {
  let seed = 2166136261;
  for (const char of id) seed = Math.imul(seed ^ char.charCodeAt(0), 16777619) >>> 0;
  const feminine = seed % 2 === 1 || ((seed >>> 10) & 1) === 1;
  const nameIndex = feminine ? (seed % 16) | 1 : seed % 16;
  return {
    feminine,
    name: `${lastNames[(seed >>> 8) % 16]} ${firstNames[nameIndex]}`,
    skin: ["#edc5a5", "#e0b58f", "#d5a17b", "#f0ceb0"][(seed >>> 4) % 4],
    hair: ["#2f2b2a", "#43342d", "#2b3130", "#54433a"][(seed >>> 6) % 4],
    shirt: ["#677c98", "#bc805e", "#739485", "#ad8ca4", "#d1b581", "#718b9c"][(seed >>> 12) % 6],
    style: (seed >>> 16) % 4,
    glasses: (seed >>> 20) % 3 === 0,
  };
}

export type WardrobeFamily = 'athletic' | 'creative' | 'study' | 'business' | 'travel' | 'host' | 'casual';
export type CharacterWardrobe = {
  family: WardrobeFamily;
  /** Official Kenney Mini Characters asset; legacy garment fields are selection metadata only. */
  asset: string;
  outfit: 'athletic' | 'hoodie' | 'overshirt' | 'cardigan' | 'knit' | 'blazer' | 'utility';
  label: string;
  shirt: string; inner: string; pants: string; accent: string; shoe: string;
  bottom: 'shorts' | 'trousers'; shoes: 'trainers' | 'sneakers' | 'loafers';
  accessory: 'watch' | 'headphones' | 'backpack' | 'none';
  haircut: 'crop' | 'parted' | 'bob' | 'ponytail' | 'bun' | 'waves';
};
type RoleStyle = Pick<CharacterWardrobe, 'family' | 'outfit' | 'shirt' | 'accent' | 'accessory'>;
// This registry owns costumes only. Repository skills still own employee membership.
const roleStyles: Record<string, RoleStyle> = {
  'coach-planner': { family: 'athletic', outfit: 'athletic', shirt: '#75947d', accent: '#d9e5c8', accessory: 'watch' },
  'design-doc': { family: 'creative', outfit: 'overshirt', shirt: '#628d91', accent: '#d6bb83', accessory: 'none' },
  'diagram-flow': { family: 'creative', outfit: 'knit', shirt: '#b17e61', accent: '#e9cf9e', accessory: 'headphones' },
  'skill-creator': { family: 'creative', outfit: 'hoodie', shirt: '#b49b61', accent: '#dcd9be', accessory: 'headphones' },
  'contract-guardian': { family: 'creative', outfit: 'overshirt', shirt: '#7b748a', accent: '#c5bca5', accessory: 'none' },
  'repo-orchestrator': { family: 'creative', outfit: 'utility', shirt: '#7b8c6b', accent: '#c8b58c', accessory: 'headphones' },
  'git-commit': { family: 'creative', outfit: 'hoodie', shirt: '#63879c', accent: '#bcd2d0', accessory: 'headphones' },
  'learning-agent': { family: 'study', outfit: 'cardigan', shirt: '#9e826c', accent: '#c8b37c', accessory: 'none' },
  'profile-optimizer': { family: 'study', outfit: 'overshirt', shirt: '#8c9c9c', accent: '#d6b791', accessory: 'none' },
  'daily-report': { family: 'study', outfit: 'knit', shirt: '#bba888', accent: '#8c9d87', accessory: 'none' },
  'weekly-review': { family: 'study', outfit: 'cardigan', shirt: '#658b83', accent: '#d5c29a', accessory: 'none' },
  'decision-log': { family: 'study', outfit: 'overshirt', shirt: '#b08e66', accent: '#b6c6ae', accessory: 'none' },
  'decision-review': { family: 'study', outfit: 'cardigan', shirt: '#9d7883', accent: '#d5c3a9', accessory: 'none' },
  'identity-audit': { family: 'study', outfit: 'cardigan', shirt: '#9c91ac', accent: '#d9c4a9', accessory: 'none' },
  'meta-coach': { family: 'study', outfit: 'knit', shirt: '#90a185', accent: '#c8b88e', accessory: 'none' },
  'wealth-manager': { family: 'business', outfit: 'blazer', shirt: '#586671', accent: '#bc9e6b', accessory: 'watch' },
  'quant-backtest-review': { family: 'business', outfit: 'blazer', shirt: '#657b8c', accent: '#abb9ba', accessory: 'none' },
  'travel-plan': { family: 'travel', outfit: 'utility', shirt: '#b49a6c', accent: '#7a9584', accessory: 'backpack' },
};
export function characterWardrobe(id: string, skillId?: string, host = false): CharacterWardrobe {
  const identity = characterProfile(id);
  const style: RoleStyle = host
    ? { family: 'host', outfit: 'overshirt', shirt: '#53657d', accent: '#c5a777', accessory: 'watch' }
    : (skillId && Object.hasOwn(roleStyles, skillId) ? roleStyles[skillId] : undefined) ?? { family: 'casual', outfit: 'knit', shirt: identity.shirt, accent: '#b5c4ae', accessory: 'none' };
  const athletic = style.family === 'athletic';
  const labels: Record<WardrobeFamily, string> = { athletic: 'Mini Characters · active', creative: 'Mini Characters · makers', study: 'Mini Characters · thinkers', business: 'Mini Characters · analysts', travel: 'Mini Characters · explorers', host: 'Mini Characters · host', casual: 'Mini Characters · teammates' };
  const variant: Record<WardrobeFamily, string> = { athletic: 'g', creative: 'b', study: 'c', business: 'd', travel: 'e', host: 'a', casual: String.fromCharCode(97 + identity.style % 6) };
  const feminine = identity.feminine && !host;
  const letter = feminine && variant[style.family] === 'g' ? 'b' : variant[style.family];
  return {
    ...style, label: labels[style.family],
    asset: `character-${feminine ? 'female' : 'male'}-${letter}`,
    inner: athletic ? '#e1ead4' : '#e2dccb',
    pants: athletic ? '#3f5049' : ({ business: '#4e555d', travel: '#6b7358', study: '#8b8270', creative: '#5d6a73', casual: '#7a7468', host: '#bda985' } as Record<string, string>)[style.family] ?? '#656c75',
    bottom: athletic ? 'shorts' : 'trousers', shoes: athletic ? 'trainers' : style.family === 'business' ? 'loafers' : 'sneakers',
    shoe: style.family === 'business' ? '#6c5e50' : '#e7e3d7',
    haircut: identity.feminine && !host ? athletic ? 'ponytail' : (['bob', 'ponytail', 'bun', 'waves'] as const)[identity.style] : identity.style % 2 ? 'parted' : 'crop',
  };
}
