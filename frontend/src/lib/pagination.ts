export const archivePageSize = 100;

export function archivePageCount(resultCount: number) {
  return Math.max(1, Math.ceil(resultCount / archivePageSize));
}
