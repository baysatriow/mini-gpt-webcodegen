export function getShareablePreviewUrl(src: string, pageUrl: string): string {
  const url = new URL(src, pageUrl);
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error("Preview links must use HTTP or HTTPS");
  }
  return url.href;
}
