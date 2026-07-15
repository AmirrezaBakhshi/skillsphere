"use client";

import { Download, FileText, Loader2, UploadCloud } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { downloadProject, fetchMyProjects, Project, uploadProject } from "@/lib/projects";
import { useAuthStore } from "@/store/authStore";

const STATUS_STYLES: Record<Project["status"], string> = {
  pending: "bg-graphite/10 text-graphite",
  processing: "bg-amber-100 text-amber-700",
  ready: "bg-signal_dim text-signal",
  rejected: "bg-red-100 text-red-700",
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ProjectsPage() {
  const router = useRouter();
  const { user } = useAuthStore();
  const [projects, setProjects] = useState<Project[]>([]);
  const [title, setTitle] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProjects = useCallback(() => {
    fetchMyProjects().then(setProjects).catch(() => setError("Couldn't load your projects."));
  }, []);

  useEffect(() => {
    if (!user) {
      router.replace("/login");
      return;
    }
    loadProjects();
  }, [user, router, loadProjects]);

  async function handleFile(file: File) {
    setError(null);
    setIsUploading(true);
    try {
      await uploadProject({ title: title || file.name, file });
      setTitle("");
      loadProjects();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Upload failed - check the file type and size.");
    } finally {
      setIsUploading(false);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  if (!user) return null;

  return (
    <AppShell>
      <h1 className="font-display text-2xl font-semibold text-ink dark:text-paper">Projects</h1>
      <p className="mt-1 text-sm text-graphite dark:text-paper/60">
        Upload something you built. PDF, ZIP, PNG, or JPEG, up to 25 MB.
      </p>

      <input
        type="text"
        placeholder="Project title (optional - defaults to file name)"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        className="focus-ring mt-6 w-full max-w-md rounded border border-line px-3 py-2 text-sm dark:border-white/10 dark:bg-white/5 dark:text-paper"
      />

      <label
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`mt-3 flex max-w-md cursor-pointer flex-col items-center justify-center gap-2 rounded border-2 border-dashed px-6 py-10 text-center transition ${
          isDragging
            ? "border-signal bg-signal_dim/40"
            : "border-line hover:border-graphite dark:border-white/15"
        }`}
      >
        {isUploading ? (
          <Loader2 className="animate-spin text-graphite" size={22} />
        ) : (
          <UploadCloud className="text-graphite dark:text-paper/50" size={22} />
        )}
        <p className="text-sm text-graphite dark:text-paper/60">
          {isUploading ? "Uploading…" : "Drag a file here, or click to choose one"}
        </p>
        <input
          type="file"
          className="hidden"
          disabled={isUploading}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
            e.target.value = "";
          }}
        />
      </label>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      <div className="mt-10 space-y-2">
        {projects.map((project) => (
          <div
            key={project.id}
            className="flex items-center justify-between rounded border border-line bg-white p-4 dark:border-white/10 dark:bg-white/5"
          >
            <div className="flex items-center gap-3">
              <FileText className="text-graphite dark:text-paper/50" size={18} />
              <div>
                <p className="text-sm font-medium text-ink dark:text-paper">{project.title}</p>
                <p className="text-xs text-graphite dark:text-paper/50">
                  {formatBytes(project.file_size)} · {project.download_count} download
                  {project.download_count === 1 ? "" : "s"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span
                className={`rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_STYLES[project.status]}`}
              >
                {project.status}
              </span>
              {project.status === "ready" && (
                <button
                  onClick={() => downloadProject(project)}
                  className="focus-ring rounded p-1.5 text-graphite transition hover:bg-signal_dim hover:text-signal dark:text-paper/60"
                  aria-label={`Download ${project.title}`}
                >
                  <Download size={16} />
                </button>
              )}
            </div>
          </div>
        ))}

        {projects.length === 0 && (
          <p className="text-sm text-graphite dark:text-paper/50">
            No projects yet - upload your first one above.
          </p>
        )}
      </div>
    </AppShell>
  );
}
