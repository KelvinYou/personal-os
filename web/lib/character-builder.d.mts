import type { Group, Object3D } from "three";
export const FIGURE_FOOT_OFFSET: number;
export interface CharacterParts { legLeft?: Group; legRight?: Group; arm: Group; leftArm: Group; head: Group }
export interface BuiltCharacter { group: Group; parts: CharacterParts; dispose: () => void }
export function buildCharacter(lib: { T: any; RoundedBoxGeometry: any }, options: { profile: any; look: any; roaming?: boolean; mug?: boolean; bowl?: boolean; laptop?: boolean; armPitch?: number }): BuiltCharacter;
export function walkPose(parts: Partial<CharacterParts>, time: number, stride: number): number;
export type { Object3D };
