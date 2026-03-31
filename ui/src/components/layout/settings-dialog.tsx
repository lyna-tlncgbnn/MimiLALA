import { Settings2 } from "lucide-react";

import { Dialog, DialogContent } from "@/components/ui/dialog";

export function SettingsDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent>
        <div className="flex items-center gap-3">
          <div className="rounded-[14px] bg-panel-strong p-3 text-accent">
            <Settings2 className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-[18px] font-semibold text-foreground">设置</h2>
            <p className="mt-1 text-[13px] text-muted-foreground">
              首版桌面端先保留一个最小入口，后续再扩展模型、路径和调试设置。
            </p>
          </div>
        </div>

        <div className="mt-5 space-y-3 rounded-[18px] border border-border bg-[rgba(255,255,255,0.92)] p-4">
          <div>
            <div className="text-[12px] font-medium text-foreground">后端服务</div>
            <div className="mt-1 text-[12px] text-muted-foreground">本地 FastAPI 服务地址固定为 `127.0.0.1:8000`。</div>
          </div>
          <div>
            <div className="text-[12px] font-medium text-foreground">当前目标</div>
            <div className="mt-1 text-[12px] text-muted-foreground">先打通会话列表、历史查看和发送消息链路。</div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
