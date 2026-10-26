type ClipboardWriter = Pick<Clipboard, "writeText">;

function getClipboard(): ClipboardWriter | null {
  if (typeof navigator === "undefined" || !navigator.clipboard) return null;
  return navigator.clipboard;
}

export async function copyTextToClipboard(
  text: string,
  clipboard: ClipboardWriter | null = getClipboard(),
): Promise<boolean> {
  if (!text || !clipboard) return false;

  try {
    await clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
