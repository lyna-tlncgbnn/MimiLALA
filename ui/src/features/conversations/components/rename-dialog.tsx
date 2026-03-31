import { useEffect, useState } from "react";

import { Button } from "@/shared/ui/button";
import { Dialog, DialogContent } from "@/shared/ui/dialog";

export function RenameDialog({
  open,
  initialName,
  onOpenChange,
  onSubmit,
}: {
  open: boolean;
  initialName: string;
  onOpenChange: (open: boolean) => void;
  onSubmit: (name: string) => Promise<void> | void;
}) {
  const [value, setValue] = useState(initialName);

  useEffect(() => {
    if (open) {
      setValue(initialName);
    }
  }, [initialName, open]);

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent>
        <h2 className="text-[18px] font-semibold text-foreground">重命名会话</h2>
        <p className="mt-1 text-[13px] text-muted-foreground">修改左侧会话列表中的显示名称。</p>

        <input
          className="mt-5 h-11 w-full rounded-[14px] border border-border bg-[rgba(255,255,255,0.88)] px-4 text-[14px] text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring"
          onChange={(event) => setValue(event.target.value)}
          placeholder="输入会话名称"
          value={value}
        />

        <div className="mt-5 flex justify-end gap-2">
          <Button onClick={() => onOpenChange(false)} variant="secondary">
            取消
          </Button>
          <Button
            disabled={!value.trim()}
            onClick={async () => {
              await onSubmit(value.trim());
              onOpenChange(false);
            }}
          >
            保存
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
