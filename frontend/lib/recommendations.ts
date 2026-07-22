import { api } from "@/lib/api";

export type ProjectRecommendation = {
  project_id: string;
  title: string;
  owner_username: string;
  shared_tags: string[];
  score: number;
  reason: string;
};

export async function fetchRecommendations(): Promise<ProjectRecommendation[]> {
  const { data } = await api.get<ProjectRecommendation[]>("/recommendations/projects/");
  return data;
}
