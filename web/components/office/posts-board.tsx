"use client";

import { useEffect, useState } from "react";
import { useThree } from "@react-three/fiber";
import { SRGBColorSpace, TextureLoader, type Texture } from "three";
import { amenities } from "@/lib/office-layout";
import type { PostSummary } from "@/lib/office-posts-contract";

function Cover({ post, index }: { post?: PostSummary; index: number }) {
  const [texture, setTexture] = useState<Texture | null>(null);
  const invalidate = useThree(state => state.invalidate);
  useEffect(() => {
    if (!post?.cover) return;
    let disposed = false;
    const value = new TextureLoader().load(post.cover, loaded => {
      if (disposed) { loaded.dispose(); return; }
      loaded.colorSpace = SRGBColorSpace; setTexture(loaded); invalidate();
    }, undefined, () => { if (!disposed) { setTexture(null); invalidate(); } });
    return () => { disposed = true; value.dispose(); setTexture(null); };
  }, [post?.cover, invalidate]);
  return <mesh position={[-1.35 + index * 1.35, 0, .13]}>
    <boxGeometry args={[texture ? .7 : 1, texture ? .94 : .75, .02]} />
    <meshStandardMaterial key={texture?.uuid ?? "placeholder"} color={texture ? "white" : ["#b8c3a2", "#d5bd96", "#b4c7bf"][index]} map={texture} roughness={.9} />
  </mesh>;
}

/** Reuses the existing library board footprint; +Z faces the library interior. */
export function PostsBoard({ posts, onOpen }: { posts: PostSummary[]; onOpen?: () => void }) {
  const board = amenities.dailyBoard;
  return <group name="office-posts-board" position={[board.x, 2, -13.85]} onClick={onOpen ? event => { event.stopPropagation(); onOpen(); } : undefined}>
    <mesh castShadow receiveShadow><boxGeometry args={[5, 1.6, .12]} /><meshStandardMaterial color="#b89e79" roughness={.8} /></mesh>
    <mesh position={[0, 0, .08]}><boxGeometry args={[4.8, 1.4, .04]} /><meshStandardMaterial color="#e9e2cb" roughness={.8} /></mesh>
    {[0, 1, 2].map(index => <Cover key={index} index={index} post={onOpen ? posts[index] : undefined} />)}
  </group>;
}
