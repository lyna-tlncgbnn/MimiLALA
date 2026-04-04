import type { ReactNode } from "react";

export function extractTextContent(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") {
    return String(node);
  }

  if (Array.isArray(node)) {
    return node.map((child) => extractTextContent(child)).join("");
  }

  if (node && typeof node === "object" && "props" in node) {
    const props = (node as { props?: { children?: ReactNode } }).props;
    return extractTextContent(props?.children ?? "");
  }

  return "";
}

export function getCodeLanguage(className?: string) {
  if (!className) {
    return null;
  }

  const match = className.match(/language-([\w-]+)/i);
  return match?.[1]?.toLowerCase() ?? null;
}
