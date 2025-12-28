/**
 * Utility functions for date formatting
 */

export const formatDate = (dateString: string | undefined): string => {
  if (!dateString) return 'N/A';
  
  try {
    // Handle the specific format from DataForSEO: "2025-05-26 14:38:20 +00:00"
    // Convert to ISO format for better parsing
    const isoDate = dateString.replace(' +00:00', 'Z');
    const date = new Date(isoDate);
    
    // Check if the date is valid
    if (isNaN(date.getTime())) {
      return 'Invalid Date';
    }
    
    return date.toLocaleDateString();
  } catch (error) {
    console.error('Date parsing error:', error, 'for date:', dateString);
    return 'Invalid Date';
  }
};

export const formatDateTime = (dateString: string | undefined): string => {
  if (!dateString) return 'N/A';
  
  try {
    // Handle the specific format from DataForSEO: "2025-05-26 14:38:20 +00:00"
    // Convert to ISO format for better parsing
    const isoDate = dateString.replace(' +00:00', 'Z');
    const date = new Date(isoDate);
    
    // Check if the date is valid
    if (isNaN(date.getTime())) {
      return 'Invalid Date';
    }
    
    return date.toLocaleString();
  } catch (error) {
    console.error('Date parsing error:', error, 'for date:', dateString);
    return 'Invalid Date';
  }
};


