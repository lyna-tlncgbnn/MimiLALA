import { create } from "zustand";
import { persist } from "zustand/middleware";

type UiState = {
  sidebarCollapsed: boolean;
  sidebarWidth: number;
  settingsOpen: boolean;
  renameTargetId: string | null;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setSidebarWidth: (width: number) => void;
  toggleSidebarCollapsed: () => void;
  setSettingsOpen: (open: boolean) => void;
  setRenameTargetId: (conversationId: string | null) => void;
};

const SIDEBAR_MIN_WIDTH = 220;
const SIDEBAR_MAX_WIDTH = 320;

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      sidebarWidth: 244,
      settingsOpen: false,
      renameTargetId: null,
      setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),
      setSidebarWidth: (sidebarWidth) =>
        set({
          sidebarWidth: Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, Math.round(sidebarWidth))),
        }),
      toggleSidebarCollapsed: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSettingsOpen: (settingsOpen) => set({ settingsOpen }),
      setRenameTargetId: (renameTargetId) => set({ renameTargetId }),
    }),
    {
      name: "agentbot-ui",
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        sidebarWidth: state.sidebarWidth,
      }),
    },
  ),
);

