export interface PostSummary {
  id: string;
  title: string;
  /** Date from the source folder, never a publication claim. */
  date: string;
  imageCount: number;
  cover: string | null;
}
export interface PostDetail extends PostSummary {
  images: { name: string; url: string }[];
  copy: string | null;
  notes: string;
  verification: string | null;
}
export interface PostCollection { posts: PostSummary[]; partial: boolean }
