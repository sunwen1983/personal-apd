export interface Note {
  id: string;
  title: string;
  body: string;
  tags: string[];
  createdAt: number;
  updatedAt: number;
}

export type NotePatch = Partial<Pick<Note, 'title' | 'body' | 'tags'>>;
