/**
 * CSV Export utilities
 */

export interface BacklinkExportData {
  domain: string;
  domain_rank: number;
  anchor_text: string | null;
  backlinks_count: number;
  first_seen: string;
  last_seen: string;
  // Additional comprehensive fields
  url_from: string;
  url_to: string;
  link_type: string;
  link_attributes: string;
  page_from_title: string;
  page_from_rank: number;
  page_from_internal_links_count: number;
  page_from_external_links_count: number;
  page_from_rank_absolute: number;
  // Additional useful fields
  dofollow: boolean;
  is_new: boolean;
  is_lost: boolean;
  is_broken: boolean;
  url_from_https: boolean;
  url_to_https: boolean;
  page_from_status_code: number;
  url_to_status_code: number;
  backlink_spam_score: number;
  url_to_spam_score: number;
  page_from_size: number;
  page_from_encoding: string;
  page_from_language: string;
  domain_from_ip: string;
  domain_from_country: string;
  domain_from_platform_type: string[];
  semantic_location: string;
  alt: string;
  image_url: string;
  text_pre: string;
  text_post: string;
  tld_from: string;
  domain_to: string;
  is_indirect_link: boolean;
  indirect_link_path: string;
  url_to_redirect_target: string;
  prev_seen: string;
  group_count: number;
  original: boolean;
  item_type: string;
  domain_from_is_ip: boolean;
}

export interface KeywordExportData {
  keyword?: string;
  rank?: number;
  search_volume?: number;
  traffic_share?: number;
  cpc?: number;
  competition?: number;
  etv?: number;
  url?: string;
  title?: string;
  description?: string;
  keyword_difficulty?: number;
}

/**
 * Convert array of objects to CSV string
 */
export function arrayToCSV<T extends Record<string, any>>(
  data: T[],
  headers: string[]
): string {
  if (data.length === 0) {
    return headers.join(',') + '\n';
  }

  // Create CSV header
  const csvHeader = headers.join(',') + '\n';

  // Create CSV rows
  const csvRows = data.map(row => {
    return headers.map(header => {
      const value = row[header];
      // Handle values that might contain commas, quotes, or newlines
      if (value === null || value === undefined) {
        return '';
      }
      const stringValue = String(value);
      // Escape quotes and wrap in quotes if contains comma, quote, or newline
      if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
        return `"${stringValue.replace(/"/g, '""')}"`;
      }
      return stringValue;
    }).join(',');
  });

  return csvHeader + csvRows.join('\n');
}

/**
 * Export backlinks data to CSV
 */
export function exportBacklinksToCSV(backlinks: BacklinkExportData[], domain: string): void {
  const headers = [
    'domain',
    'domain_rank',
    'anchor_text',
    'backlinks_count',
    'first_seen',
    'last_seen',
    'url_from',
    'url_to',
    'link_type',
    'link_attributes',
    'page_from_title',
    'page_from_rank',
    'page_from_internal_links_count',
    'page_from_external_links_count',
    'page_from_rank_absolute',
    'dofollow',
    'is_new',
    'is_lost',
    'is_broken',
    'url_from_https',
    'url_to_https',
    'page_from_status_code',
    'url_to_status_code',
    'backlink_spam_score',
    'url_to_spam_score',
    'page_from_size',
    'page_from_encoding',
    'page_from_language',
    'domain_from_ip',
    'domain_from_country',
    'domain_from_platform_type',
    'semantic_location',
    'alt',
    'image_url',
    'text_pre',
    'text_post',
    'tld_from',
    'domain_to',
    'is_indirect_link',
    'indirect_link_path',
    'url_to_redirect_target',
    'prev_seen',
    'group_count',
    'original',
    'item_type',
    'domain_from_is_ip'
  ];

  const csvContent = arrayToCSV(backlinks, headers);
  downloadCSV(csvContent, `${domain}-backlinks.csv`);
}

/**
 * Export keywords data to CSV
 */
export function exportKeywordsToCSV(keywords: KeywordExportData[], domain: string): void {
  const headers = [
    'keyword',
    'rank',
    'search_volume',
    'traffic_share',
    'cpc',
    'competition',
    'etv',
    'url',
    'title',
    'description',
    'keyword_difficulty'
  ];

  const csvContent = arrayToCSV(keywords, headers);
  downloadCSV(csvContent, `${domain}-keywords.csv`);
}

/**
 * Download CSV file
 */
function downloadCSV(csvContent: string, filename: string): void {
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  
  if (link.download !== undefined) {
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }
}
