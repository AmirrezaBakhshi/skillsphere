import { api } from "@/lib/api";

export type Project = {
  id: string;
  title: string;
  description: string;
  file_name: string;
  file_size: number;
  content_type: string;
  status: "pending" | "processing" | "ready" | "rejected";
  download_count: number;
  created_at: string;
};

export async function fetchMyProjects(): Promise<Project[]> {
  const { data } = await api.get<Project[]>("/projects/mine/");
  return data;
}

export async function uploadProject(payload: {
  title: string;
  description?: string;
  file: File;
}): Promise<Project> {
  const form = new FormData();
  form.append("title", payload.title);
  if (payload.description) form.append("description", payload.description);
  form.append("file", payload.file);

  const { data } = await api.post<Project>("/projects/upload/", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function downloadProject(project: Project): Promise<void> {
  const response = await api.get(`/projects/${project.id}/download/`, {
    responseType: "blob",
  });
  const blobUrl = window.URL.createObjectURL(response.data as Blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = project.file_name || project.title;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(blobUrl);
}
