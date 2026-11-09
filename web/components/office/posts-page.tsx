"use client";

import { PostsLibrary, usePostCollection } from "./posts-library";

export function PostsPage() {
  const posts = usePostCollection(true);
  return <main id="main-content" className="office-page posts-page">
    <PostsLibrary inline open onClose={() => {}} {...posts} onRetry={posts.retry} />
  </main>;
}
