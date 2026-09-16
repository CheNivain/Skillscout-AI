import { createContext, useContext } from 'react';
import type { Course, Dashboard, Recommendation, Run, Saved, User } from './types';
export type Page =
  | 'overview'
  | 'explore'
  | 'plan'
  | 'trends'
  | 'agents'
  | 'settings'
  | 'organization';
export type Workspace = {
  user: User;
  dashboard: Dashboard;
  saved: Saved[];
  running: boolean;
  activeRun: Run | null;
  go: (page: Page) => void;
  refresh: () => Promise<void>;
  run: () => Promise<void>;
  selectCourse: (course: Course, rec?: Recommendation) => void;
  save: (course: Course, status?: Saved['status']) => Promise<void>;
  remove: (course: Course) => Promise<void>;
  toast: (message: string, error?: boolean) => void;
  openChat: () => void;
};
export const WorkspaceContext = createContext<Workspace | null>(null);
export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error('Workspace unavailable');
  return value;
}
