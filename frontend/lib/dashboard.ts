import { api } from "@/lib/api";

export type DailyCount = { date: string; count: number };

export type UserDashboard = {
  total_projects: number;
  projects_ready: number;
  projects_processing: number;
  projects_rejected: number;
  total_downloads: number;
  unread_notifications: number;
  activity_last_14_days: DailyCount[];
};

export async function fetchMyDashboard(): Promise<UserDashboard> {
  const { data } = await api.get<UserDashboard>("/dashboard/me/");
  return data;
}
