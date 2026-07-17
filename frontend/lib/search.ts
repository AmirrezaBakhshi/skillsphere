import { api } from "@/lib/api";

export type ProjectSearchResult = {
  id: string;
  title: string;
  description: string;
  tags: string[];
  owner_username: string;
  score: number;
};

export type UserSearchResult = {
  id: string;
  username: string;
  bio: string;
  score: number;
};

export async function searchProjects(query: string): Promise<ProjectSearchResult[]> {
  if (!query.trim()) return [];
  const { data } = await api.get<ProjectSearchResult[]>("/search/projects/", {
    params: { q: query },
  });
  return data;
}

export async function searchUsers(query: string): Promise<UserSearchResult[]> {
  if (!query.trim()) return [];
  const { data } = await api.get<UserSearchResult[]>("/search/users/", {
    params: { q: query },
  });
  return data;
}
