import { create } from "zustand";

type UiState = {
  sidebarCollapsed: boolean;
  settingsOpen: boolean;
  renameTargetId: string | null;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebarCollapsed: () => void;
  setSettingsOpen: (open: boolean) => void;
  setRenameTargetId: (conversationId: string | null) => void;
};

export const useUiStore = create<UiState>((set) => ({
  sidebarCollapsed: false,
  settingsOpen: false,
  renameTargetId: null,
  setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),
  toggleSidebarCollapsed: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setSettingsOpen: (settingsOpen) => set({ settingsOpen }),
  setRenameTargetId: (renameTargetId) => set({ renameTargetId }),
}));
