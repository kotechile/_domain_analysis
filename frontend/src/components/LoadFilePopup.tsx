import React, { useState, useEffect, useRef } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  LinearProgress,
  IconButton,
  Chip,
  Stack,
  Paper,
} from '@mui/material';
import {
  Close as CloseIcon,
  InsertDriveFile as InsertDriveFileIcon,
  Pause as PauseIcon,
  PlayArrow as PlayArrowIcon,
  Delete as DeleteIcon,
  Analytics as AnalyticsIcon,
} from '@mui/icons-material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useApi } from '../services/api';

interface LoadFilePopupProps {
  open: boolean;
  onClose: () => void;
}


const LoadFilePopup: React.FC<LoadFilePopupProps> = ({ open, onClose }) => {
  const api = useApi();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [hasDataForSEO, setHasDataForSEO] = useState(false);
  const [hasCheckedForActiveJob, setHasCheckedForActiveJob] = useState(false);

  // Check if data exists for SEO analysis
  const { data: auctionsData } = useQuery({
    queryKey: ['auctions-check-seo'],
    queryFn: () => api.getAuctionsReport(
      undefined, // preferred
      undefined, // auctionSite
      undefined, // offeringType
      undefined, // tld
      undefined, // tlds
      undefined, // hasStatistics
      undefined, // scored
      undefined, // minRank
      undefined, // maxRank
      undefined, // minScore
      undefined, // maxScore
      undefined, // expirationFromDate
      undefined, // expirationToDate
      'expiration_date', // sortBy
      'asc', // sortOrder
      1, // limit
      0  // offset
    ),
    enabled: open && !jobId, // Only check when popup is open and no job is running
    refetchInterval: 30000, // Check every 30 seconds
  });

  useEffect(() => {
    if (auctionsData && auctionsData.total_count > 0) {
      setHasDataForSEO(true);
    } else {
      setHasDataForSEO(false);
    }
  }, [auctionsData]);

  // Check for active job on component mount and when popup opens
  useEffect(() => {
    // When popup opens, reset hasCheckedForActiveJob so we can check again
    if (open && !jobId) {
      setHasCheckedForActiveJob(false);
    }
    
    // Check immediately on mount, and also when popup opens if no jobId is set
    if (jobId) {
      return; // Already have a jobId, no need to check
    }

    const checkActiveJob = async () => {
      try {
        // First, try to get job ID from localStorage (faster, no API call)
        const storedJobId = localStorage.getItem('activeUploadJobId');
        if (storedJobId) {
          console.log('Found stored jobId in localStorage:', storedJobId);
          // Try to get progress for this job ID directly
          try {
            const progress = await api.getUploadProgress(storedJobId);
            if (progress) {
              const status = progress.status;
              if (status === 'processing' || status === 'parsing' || status === 'pending') {
                console.log('Stored jobId is still active:', storedJobId, 'Status:', status);
                setJobId(storedJobId);
                if (progress.filename) {
                  const fileLikeObject = {
                    name: progress.filename,
                    size: 0,
                  } as File;
                  setSelectedFile(fileLikeObject);
                }
                // Provider is now auto-detected from filename, no need to restore
                return; // Found active job, no need to check latest-active
              } else if (status === 'completed' || status === 'failed') {
                // Job is done, clear from localStorage
                console.log('Stored jobId is completed/failed, clearing:', storedJobId, 'Status:', status);
                localStorage.removeItem('activeUploadJobId');
                if (status === 'failed') {
                  setIsPaused(true);
                }
              }
            }
          } catch (e) {
            // Job not found or error, clear from localStorage
            console.log('Stored jobId not found or error, clearing:', e);
            localStorage.removeItem('activeUploadJobId');
          }
        }

        // Fallback: try latest-active endpoint (may timeout, but that's ok)
        try {
          const activeProgress = await api.getLatestActiveUploadProgress();
          if (activeProgress && activeProgress.job_id) {
            console.log('Found job via latest-active:', activeProgress.job_id, 'Status:', activeProgress.status);
            
            // If job is failed or completed, don't treat it as active - just show the error/result
            if (activeProgress.status === 'failed' || activeProgress.status === 'completed') {
              console.log('Job is completed/failed, not treating as active:', activeProgress.status);
              setHasCheckedForActiveJob(true); // Mark as checked so we stop polling
              // Clear any stale jobId
              if (jobId) {
                console.log('Clearing stale jobId because latest-active job is completed/failed');
                setJobId(null);
              }
              try {
                localStorage.removeItem('activeUploadJobId');
              } catch (e) {
                console.warn('Failed to clear localStorage:', e);
              }
              // Don't store in localStorage or set jobId - job is done
              return; // Exit early, don't block new uploads
            }
            
            // Only restore jobId if job is actually active (processing, parsing, pending)
            console.log('Found active job via latest-active:', activeProgress.job_id, 'Status:', activeProgress.status);
            setJobId(activeProgress.job_id);
            // Store in localStorage
            try {
              localStorage.setItem('activeUploadJobId', activeProgress.job_id);
            } catch (e) {
              console.warn('Failed to store jobId in localStorage:', e);
            }
            
            // Restore filename if available
            if (activeProgress.filename) {
              // Create a minimal File-like object for display purposes
              // We can't create a real File object, but we can create an object with the name property
              const fileLikeObject = {
                name: activeProgress.filename,
                size: 0, // Size not available from progress data
              } as File;
              setSelectedFile(fileLikeObject);
            }
            
            // Provider is now auto-detected from filename, no need to restore
          } else {
            // No active job found - clear any stale state
            console.log('No active job found via latest-active, clearing stale state');
            setHasCheckedForActiveJob(true); // Mark as checked so we stop polling
            if (jobId) {
              console.log('Clearing stale jobId because no active job found');
              setJobId(null);
            }
            try {
              localStorage.removeItem('activeUploadJobId');
            } catch (e) {
              console.warn('Failed to clear localStorage:', e);
            }
          }
        } catch (error: any) {
          // Handle 404 or timeout - no active job
          if (error?.response?.status === 404 || error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
            console.log('No active job found (404/timeout), clearing stale state');
            setHasCheckedForActiveJob(true); // Mark as checked so we stop polling
            if (jobId) {
              console.log('Clearing stale jobId because no active job found (404/timeout)');
              setJobId(null);
            }
            try {
              localStorage.removeItem('activeUploadJobId');
            } catch (e) {
              console.warn('Failed to clear localStorage:', e);
            }
          } else {
            console.error('Failed to check for active upload job:', error);
          }
        }
      } catch (error) {
        console.error('Failed to check for active upload job:', error);
        // Clear stale state on any error
        if (jobId) {
          console.log('Clearing stale jobId due to error in checkActiveJob');
          setJobId(null);
        }
        try {
          localStorage.removeItem('activeUploadJobId');
        } catch (e) {
          console.warn('Failed to clear localStorage:', e);
        }
      }
    };

    // Check immediately, and also when popup opens
    checkActiveJob();
    if (open) {
      // Also check when popup opens (in case it wasn't checked on mount)
      const timeoutId = setTimeout(checkActiveJob, 500);
      return () => clearTimeout(timeoutId);
    }
  }, [open, jobId, api]);

  // Clear stale localStorage on mount if popup is open
  useEffect(() => {
    if (open && !jobId) {
      // If popup is open and no jobId, check localStorage and clear if stale
      const storedJobId = localStorage.getItem('activeUploadJobId');
      if (storedJobId) {
        // Verify the stored job is actually active
        api.getUploadProgress(storedJobId).then((progress) => {
          if (progress && (progress.status === 'completed' || progress.status === 'failed')) {
            console.log('Clearing stale jobId from localStorage:', storedJobId);
            localStorage.removeItem('activeUploadJobId');
          }
        }).catch(() => {
          // Job not found, clear it
          console.log('Stored jobId not found, clearing from localStorage:', storedJobId);
          localStorage.removeItem('activeUploadJobId');
        });
      }
    }
  }, [open, jobId, api]);

  // Poll for upload progress using jobId
  // Keep query enabled even after completion to preserve progress data
  const { 
    data: progressDataById, 
    refetch: refetchProgress,
    isLoading: isLoadingProgressById,
    error: progressErrorById 
  } = useQuery({
    queryKey: ['upload-progress', jobId],
    queryFn: async () => {
      console.log('Fetching progress for jobId:', jobId);
      const result = await api.getUploadProgress(jobId!);
      console.log('Progress data received:', result);
      
      // Log error details when job fails
      if (result.status === 'failed' && result.error_message) {
        console.error('CSV Upload Failed - Error Details:', {
          jobId: result.job_id,
          status: result.status,
          error_message: result.error_message,
          processed: result.processed_records,
          total: result.total_records,
          fullProgress: result
        });
        // Also log the full error message separately so it's not truncated
        console.error('Full Error Message:', result.error_message);
      }
      
      return result;
    },
    enabled: !!jobId && !isPaused,
    // Keep the data in cache even after jobId is cleared (for completed jobs)
    gcTime: 60000, // Keep in cache for 60 seconds
    refetchInterval: (query) => {
      // Poll every 2 seconds if processing, stop if completed or failed
      const data = query.state.data;
      const error = query.state.error as any;
      // Stop polling if we got a 404 (job doesn't exist)
      if (error?.response?.status === 404) {
        return false;
      }
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false;
      }
      return 2000;
    },
    retry: (failureCount, error: any) => {
      // Don't retry on 404 errors (job doesn't exist)
      if (error?.response?.status === 404) {
        return false;
      }
      // Retry up to 3 times for other errors
      return failureCount < 3;
    },
    retryDelay: 1000,
  });

  // Clear jobId if we get a 404 error for the specific jobId
  useEffect(() => {
    if (progressErrorById) {
      const error = progressErrorById as any;
      if (error?.response?.status === 404) {
        console.log('Job not found (404), clearing jobId and cache:', jobId);
        setJobId(null);
        setHasCheckedForActiveJob(true);
        try {
          localStorage.removeItem('activeUploadJobId');
        } catch (e) {
          console.warn('Failed to clear localStorage:', e);
        }
        // Clear the query cache and explicitly set data to null
        if (jobId) {
          queryClient.removeQueries({ queryKey: ['upload-progress', jobId] });
          queryClient.setQueryData(['upload-progress', jobId], null);
        }
      }
    }
  }, [progressErrorById, jobId, queryClient]);

  // Fallback: Poll for latest active upload progress when jobId is not set
  // This runs when popup is open OR when component is mounted (to detect active jobs on page load)
  const { 
    data: progressDataByActive, 
    isLoading: isLoadingProgressByActive,
    error: progressErrorByActive 
  } = useQuery({
    queryKey: ['upload-progress', 'latest-active'],
    queryFn: async () => {
      console.log('Fetching latest active progress');
      try {
        const result = await api.getLatestActiveUploadProgress();
        if (result && result.job_id) {
          // Only treat as active if status is actually active (not completed/failed)
          if (result.status === 'failed' || result.status === 'completed') {
            console.log('Found completed/failed job via fallback query, not treating as active:', result.status);
            setHasCheckedForActiveJob(true);
            // Clear any stale jobId
            if (jobId) {
              console.log('Clearing stale jobId because latest-active job is completed/failed');
              setJobId(null);
            }
            try {
              localStorage.removeItem('activeUploadJobId');
            } catch (e) {
              console.warn('Failed to clear localStorage:', e);
            }
            // Clear the query cache for this failed/completed job so it doesn't block uploads
            queryClient.removeQueries({ queryKey: ['upload-progress', 'latest-active'] });
            // Don't set jobId - allow new uploads
            // Don't return the result - return null so progressDataByActive is null and doesn't block uploads
            return null;
          }
          
          console.log('Found active job via fallback query:', result.job_id);
          setHasCheckedForActiveJob(true);
          // Set jobId so we can switch to the jobId-based query
          setJobId(result.job_id);
          // Also restore file info
          if (result.filename) {
            const fileLikeObject = {
              name: result.filename,
              size: 0,
            } as File;
            setSelectedFile(fileLikeObject);
          }
          // Provider is now auto-detected from filename, no need to restore
          return result;
        }
        // No active job found
        setHasCheckedForActiveJob(true); // Mark as checked even if no active job
        // Clear any stale state
        if (jobId) {
          console.log('Clearing stale jobId because no active job found');
          setJobId(null);
        }
        try {
          localStorage.removeItem('activeUploadJobId');
        } catch (e) {
          console.warn('Failed to clear localStorage:', e);
        }
        return null;
      } catch (error: any) {
        // Handle 404 or timeout - no active job
        if (error?.response?.status === 404 || error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
          console.log('No active job found (404/timeout), clearing stale state');
          setHasCheckedForActiveJob(true);
          if (jobId) {
            console.log('Clearing stale jobId because no active job found (404/timeout)');
            setJobId(null);
          }
          try {
            localStorage.removeItem('activeUploadJobId');
          } catch (e) {
            console.warn('Failed to clear localStorage:', e);
          }
          return null; // Return null to indicate no active job
        }
        // Re-throw other errors
        throw error;
      }
    },
    enabled: !jobId && !isPaused && (open || !hasCheckedForActiveJob), // Run when popup is open or when we haven't checked yet
    refetchInterval: (query) => {
      // Poll every 2 seconds if we have active data, stop if no data (404 means no active job)
      const data = query.state.data;
      const error = query.state.error as any;
      
      // Stop polling if we got a 404 or timeout (no active job found)
      if (error?.response?.status === 404 || error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
        setHasCheckedForActiveJob(true); // Mark as checked so we don't keep polling
        // Clear any stale jobId or localStorage
        if (jobId) {
          console.log('Clearing stale jobId because latest-active returned 404/timeout');
          setJobId(null);
        }
        try {
          localStorage.removeItem('activeUploadJobId');
        } catch (e) {
          console.warn('Failed to clear localStorage:', e);
        }
        return false; // No active job, stop polling
      }
      if (data?.status === 'completed' || data?.status === 'failed') {
        setHasCheckedForActiveJob(true);
        return false;
      }
      // Only poll if we have data (active job found) and popup is open
      if (data && open) {
        return 2000;
      }
      // If we've already checked and there's no active job, don't poll
      if (hasCheckedForActiveJob) {
        return false;
      }
      // If no data and no error yet, keep trying (but with longer interval) only if popup is open
      if (open && !hasCheckedForActiveJob) {
        return 5000; // Check less frequently when no active job but popup is open
      }
      return false; // Don't poll when popup is closed
    },
    retry: (failureCount, error: any) => {
      // Don't retry on 404 errors (no active job is expected)
      if (error?.response?.status === 404) {
        setHasCheckedForActiveJob(true);
        // Clear any stale state
        if (jobId) {
          console.log('Clearing stale jobId on 404 retry');
          setJobId(null);
        }
        try {
          localStorage.removeItem('activeUploadJobId');
        } catch (e) {
          console.warn('Failed to clear localStorage on retry:', e);
        }
        return false;
      }
      // Don't retry on timeout errors - likely no active job
      if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
        setHasCheckedForActiveJob(true);
        return false;
      }
      // Retry up to 2 times for other errors
      return failureCount < 2;
    },
    retryDelay: 1000,
  });

  // Use jobId-based progress if available, otherwise use latest-active
  // For display purposes, we want to show completed/failed jobs too (to show final metrics)
  // But for hasActiveJob, we filter out completed/failed
  // Also check for 404 or timeout errors - if we got a 404/timeout, don't use the data even if it exists in cache
  const progressErrorByIdIs404 = progressErrorById && (progressErrorById as any)?.response?.status === 404;
  const progressErrorByActiveIs404 = progressErrorByActive && 
    ((progressErrorByActive as any)?.response?.status === 404 || 
     (progressErrorByActive as any)?.code === 'ECONNABORTED' || 
     (progressErrorByActive as any)?.message?.includes('timeout'));
  
  // For display: show all progress data (including completed/failed) if no errors
  const progressDataForDisplay = (!progressErrorByIdIs404 && progressDataById) || 
    (!progressErrorByActiveIs404 && progressDataByActive) || null;
  
  // For hasActiveJob: only consider active jobs (not completed/failed)
  const progressDataByIdActive = progressDataById && 
    !progressErrorByIdIs404 &&
    progressDataById.status !== 'completed' && 
    progressDataById.status !== 'failed' 
    ? progressDataById : null;
  const progressDataByActiveActive = progressDataByActive && 
    !progressErrorByActiveIs404 &&
    progressDataByActive.status !== 'completed' && 
    progressDataByActive.status !== 'failed' 
    ? progressDataByActive : null;
  const progressData = progressDataByIdActive || progressDataByActiveActive;
  // Use progressDataForDisplay for UI, progressData for hasActiveJob logic
  const displayProgressData = progressDataForDisplay || progressData;
  const isLoadingProgress = isLoadingProgressById || isLoadingProgressByActive;
  const progressError = progressErrorById || progressErrorByActive;

  // Debug: Log when jobId changes
  useEffect(() => {
    if (jobId) {
      console.log('jobId set, starting progress polling:', jobId);
    }
  }, [jobId]);

  // Clear jobId if we get a 404 or timeout error from latest-active query
  useEffect(() => {
    if (progressErrorByActive) {
      const error = progressErrorByActive as any;
      const isTimeout = error?.code === 'ECONNABORTED' || error?.message?.includes('timeout');
      if (error?.response?.status === 404 || isTimeout) {
        console.log('No active job found (404/timeout from latest-active), clearing jobId and cache');
        setJobId(null);
        setHasCheckedForActiveJob(true);
        try {
          localStorage.removeItem('activeUploadJobId');
        } catch (e) {
          console.warn('Failed to clear localStorage:', e);
        }
        // Clear the query cache and explicitly set data to null
        queryClient.removeQueries({ queryKey: ['upload-progress', 'latest-active'] });
        queryClient.setQueryData(['upload-progress', 'latest-active'], null);
      }
    }
  }, [progressErrorByActive, queryClient]);

  // Clear localStorage and jobId when job completes or fails
  // Also clear query cache for failed/completed jobs
  // But delay clearing jobId to keep progress data visible briefly
  useEffect(() => {
    // Check progressDataById (from jobId-based query)
    if (progressDataById && (progressDataById.status === 'completed' || progressDataById.status === 'failed')) {
      try {
        localStorage.removeItem('activeUploadJobId');
        console.log('Job completed/failed (byId), cleared from localStorage');
      } catch (e) {
        console.warn('Failed to clear jobId from localStorage:', e);
      }
      // Don't clear jobId immediately - keep it so progress data stays visible
      // Only clear when user closes popup or starts new upload
      // This prevents the UI from flickering back to "processing" state
      setHasCheckedForActiveJob(true);
      console.log('Job completed/failed (byId), keeping jobId to preserve progress data');
    }
    // Also check progressDataByActive separately
    if (progressDataByActive && (progressDataByActive.status === 'completed' || progressDataByActive.status === 'failed')) {
      // Clear the latest-active query cache and don't set jobId
      queryClient.removeQueries({ queryKey: ['upload-progress', 'latest-active'] });
      setHasCheckedForActiveJob(true);
      // Make sure jobId is not set for failed/completed jobs from latest-active
      // But keep it to preserve progress data visibility
      if (jobId === progressDataByActive.job_id) {
        console.log('Latest-active job is completed/failed, keeping jobId to preserve progress data');
        // Don't clear jobId - keep progress data visible
      }
      console.log('Cleared latest-active query cache for completed/failed job');
    }
  }, [progressDataById?.status, progressDataByActive?.status, jobId, queryClient, progressDataById?.job_id, progressDataByActive?.job_id]);

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      // Auto-detect provider and offering type from filename - backend will handle this
      const response = await api.uploadAuctionsCSV(file, 'auto', undefined);
      return response;
    },
    onSuccess: (data) => {
      console.log('Upload started, jobId:', data.job_id);
      const newJobId = data.job_id || null;
      setJobId(newJobId);
      // Store job ID in localStorage for persistence across page reloads
      if (newJobId) {
        try {
          localStorage.setItem('activeUploadJobId', newJobId);
        } catch (e) {
          console.warn('Failed to store jobId in localStorage:', e);
        }
      }
      // After upload completes, check for data again
      setTimeout(() => {
        if (auctionsData) {
          setHasDataForSEO(true);
        }
      }, 5000);
    },
    onError: (error: any) => {
      console.error('Upload failed:', error);
      // Error will be displayed in the UI via uploadMutation.isError
      // Reset jobId if upload fails before job is created
      setJobId(null);
    },
  });

  // Trigger SEO analysis mutation
  const trafficDataMutation = useMutation({
    mutationFn: async () => {
      return await api.triggerBulkTrafficDataAnalysis(1000);
    },
    onSuccess: () => {
      // Show success message or update UI
      console.log('SEO Analysis triggered successfully');
      // Invalidate auctions query to refresh data after analysis completes
      queryClient.invalidateQueries({ queryKey: ['auctions-report'] });
    },
  });

  // Trigger bulk rank analysis mutation
  const bulkRankAnalysisMutation = useMutation({
    mutationFn: async () => {
      return await api.triggerBulkRankAnalysis(1000);
    },
    onSuccess: () => {
      // Show success message or update UI
      console.log('Bulk Rank Analysis triggered successfully');
      // Invalidate auctions query immediately to refresh data
      queryClient.invalidateQueries({ queryKey: ['auctions-report'] });
      // Also refresh after a delay to catch n8n webhook updates
      // n8n typically takes 10-30 seconds to process and call back
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['auctions-report'] });
      }, 30000); // Refresh after 30 seconds
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['auctions-report'] });
      }, 60000); // Refresh again after 60 seconds
    },
  });

  // Trigger bulk backlinks analysis mutation
  const bulkBacklinksAnalysisMutation = useMutation({
    mutationFn: async () => {
      return await api.triggerBulkBacklinksAnalysis(1000);
    },
    onSuccess: () => {
      // Show success message or update UI
      console.log('Bulk Backlinks Analysis triggered successfully');
      // Invalidate auctions query immediately to refresh data
      queryClient.invalidateQueries({ queryKey: ['auctions-report'] });
      // Also refresh after a delay to catch n8n webhook updates
      // n8n typically takes 10-30 seconds to process and call back
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['auctions-report'] });
      }, 30000); // Refresh after 30 seconds
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['auctions-report'] });
      }, 60000); // Refresh again after 60 seconds
    },
  });

  // Trigger bulk spam score analysis mutation
  const bulkSpamScoreAnalysisMutation = useMutation({
    mutationFn: async () => {
      return await api.triggerBulkSpamScoreAnalysis(1000);
    },
    onSuccess: () => {
      // Show success message or update UI
      console.log('Bulk Spam Score Analysis triggered successfully');
      // Invalidate auctions query immediately to refresh data
      queryClient.invalidateQueries({ queryKey: ['auctions-report'] });
      // Also refresh after a delay to catch n8n webhook updates
      // n8n typically takes 10-30 seconds to process and call back
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['auctions-report'] });
      }, 30000); // Refresh after 30 seconds
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['auctions-report'] });
      }, 60000); // Refresh again after 60 seconds
    },
  });

  const handleSelectFile = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Check if there's an active job - use hasActiveJob which checks both jobId and progressData
      if (hasActiveJob) {
        // Don't allow selecting a new file when there's an active job
        alert('A file is currently being processed. Please wait for it to complete before uploading a new file.');
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
        // Clear any previously selected file
        setSelectedFile(null);
        return;
      }
      setSelectedFile(file);
      // Clear previous jobId and reset state when starting new upload
      setJobId(null);
      setHasCheckedForActiveJob(false);
      // Automatically start loading the file
      uploadMutation.mutate(file);
    }
  };

  const handleDelete = () => {
    // Don't allow deleting if there's an active job
    if (hasActiveJob) {
      alert('Cannot delete file while processing is in progress. Please wait for the current job to complete.');
      return;
    }
    setSelectedFile(null);
    setJobId(null);
    setIsPaused(false);
    // Clear from localStorage
    try {
      localStorage.removeItem('activeUploadJobId');
    } catch (e) {
      console.warn('Failed to clear jobId from localStorage:', e);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handlePauseResume = () => {
    setIsPaused(!isPaused);
    if (!isPaused) {
      // Pause: stop polling
    } else {
      // Resume: restart polling
      refetchProgress();
    }
  };

  const handleTrafficDataAnalysis = () => {
    trafficDataMutation.mutate();
  };

  const handleBulkRankAnalysis = () => {
    bulkRankAnalysisMutation.mutate();
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getProgressPercentage = (): number => {
    if (!displayProgressData) return 0;
    return displayProgressData.progress_percentage || 0;
  };

  const getStatusColor = (status?: string): 'default' | 'success' | 'error' | 'warning' => {
    if (!status) return 'default';
    if (status === 'completed') return 'success';
    if (status === 'failed') return 'error';
    if (status === 'processing' || status === 'parsing') return 'warning';
    return 'default';
  };

  const totalRecords = displayProgressData?.total_records ?? 0;
  const processedRecords = displayProgressData?.processed_records ?? 0;
  const unprocessedRecords = Math.max(0, totalRecords - processedRecords);
  // Scored records would be domains that have been scored - we can estimate from processed records
  // or query separately. For now, we'll show processed as a proxy.
  const scoredRecords = processedRecords;
  
  // Check if we have data to display (not just loading state)
  const hasProgressData = displayProgressData !== undefined && displayProgressData !== null;
  
  // Check if there's an active job (processing, parsing, or pending)
  // Only consider checking if we haven't checked yet AND popup is open AND we're not already loading
  const isCheckingForActiveJob = !hasCheckedForActiveJob && !jobId && open && !isLoadingProgressByActive;
  // hasActiveJob should only be true if job is actually active (not completed or failed)
  // Since we already filter out failed/completed jobs from progressData, we can check progressData directly
  // If progressData exists, it means there's an active job (we filtered out completed/failed)
  // If jobId exists but no progressData yet (still loading), consider it active
  // Only consider job active if:
  // 1. We have a jobId AND progressData that shows it's actually active (not completed/failed)
  // 2. OR we're currently uploading (uploadMutation.isPending)
  // 3. OR we're loading progress for a jobId (but only if we haven't confirmed it's failed/completed/404)
  // Don't consider it active if:
  // - progressData shows completed/failed
  // - we got a 404 error
  // - we got a timeout error (means no active job)
  // - we've checked and found no active job (hasCheckedForActiveJob is true and no jobId)
  // Note: progressData already filters out 404/timeout errors, so if progressData exists, it's valid
  const progressErrorByActiveIsTimeout = progressErrorByActive && 
    ((progressErrorByActive as any)?.code === 'ECONNABORTED' || 
     (progressErrorByActive as any)?.message?.includes('timeout'));
  // If we've checked for an active job and found none (timeout/404), don't block uploads
  // If we've checked and confirmed no active job (404/timeout), or if we've checked and there's no jobId/data and not loading
  const hasConfirmedNoActiveJob = (hasCheckedForActiveJob && !jobId && (progressErrorByActiveIsTimeout || progressErrorByActiveIs404)) ||
    (hasCheckedForActiveJob && !jobId && !progressData && !isLoadingProgressByActive);
  const hasActiveJob = !hasConfirmedNoActiveJob && (
    uploadMutation.isPending ||
    (!!jobId && !!progressData && progressData.status !== 'completed' && progressData.status !== 'failed') ||
    (isLoadingProgressById && !!jobId && !progressDataById && !progressErrorByIdIs404 && !progressErrorByActiveIsTimeout) // Only if we're loading and don't have data yet AND no 404/timeout error
  );

  // Clear selectedFile if there's an active job (prevents showing new file selection when job is active)
  useEffect(() => {
    if (hasActiveJob && selectedFile && displayProgressData?.filename && selectedFile.name !== displayProgressData.filename) {
      // If there's an active job but the selectedFile doesn't match the active job's filename, clear it
      // This prevents showing a newly selected file when there's an active job
      console.log('Clearing selectedFile because active job detected:', displayProgressData.filename);
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  }, [hasActiveJob, selectedFile, displayProgressData?.filename]);

  // Clear jobId when popup closes (but keep it while open to show completed progress)
  useEffect(() => {
    if (!open && jobId) {
      // Only clear if job is completed/failed, not if it's still processing
      const currentProgress = progressDataById || progressDataByActive;
      if (currentProgress && (currentProgress.status === 'completed' || currentProgress.status === 'failed')) {
        console.log('Popup closed, clearing completed jobId');
        setJobId(null);
        setHasCheckedForActiveJob(false);
      }
    }
  }, [open, jobId, progressDataById, progressDataByActive]);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          bgcolor: '#0C152B',
          borderRadius: '12px',
        },
      }}
    >
      <DialogTitle
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          color: '#FFFFFF',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        }}
      >
        <Typography component="span" sx={{ fontWeight: 600, fontSize: '1.25rem' }}>
          Load File
        </Typography>
        <IconButton
          onClick={onClose}
          sx={{
            color: '#FFFFFF',
            '&:hover': {
              bgcolor: 'rgba(255, 255, 255, 0.1)',
            },
          }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ mt: 2 }}>
        <Stack spacing={3}>

          {/* Warning: Active Job */}
          {hasActiveJob && (
            <Paper
              sx={{
                p: 2,
                mb: 2,
                bgcolor: 'rgba(255, 193, 7, 0.1)',
                borderRadius: '8px',
                border: '1px solid rgba(255, 193, 7, 0.3)',
              }}
            >
              <Typography
                variant="body2"
                sx={{
                  color: '#FFC107',
                  fontWeight: 600,
                  mb: 0.5,
                }}
              >
                ⚠️ File Processing in Progress
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  color: 'rgba(255, 255, 255, 0.9)',
                }}
              >
                A file is currently being processed. Please wait for it to complete before uploading a new file.
              </Typography>
            </Paper>
          )}

          {/* File Action Buttons */}
          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
            <Button
              variant="outlined"
              onClick={handleSelectFile}
              disabled={hasActiveJob}
              sx={{
                color: '#FFFFFF',
                borderColor: 'rgba(255, 255, 255, 0.3)',
                '&:hover': {
                  borderColor: '#66CCFF',
                  bgcolor: 'rgba(102, 204, 255, 0.1)',
                },
                '&:disabled': {
                  borderColor: 'rgba(255, 255, 255, 0.1)',
                  color: 'rgba(255, 255, 255, 0.3)',
                },
              }}
            >
              Select File
            </Button>
          </Box>

          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />

          {/* Upload Error Display */}
          {uploadMutation.isError && (
            <Paper
              sx={{
                p: 2,
                mb: 2,
                bgcolor: 'rgba(255, 82, 82, 0.1)',
                borderRadius: '8px',
                border: '1px solid rgba(255, 82, 82, 0.3)',
              }}
            >
              <Typography
                variant="body2"
                sx={{
                  color: '#FF5252',
                  fontWeight: 500,
                  mb: 0.5,
                }}
              >
                Upload Error:
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  color: 'rgba(255, 255, 255, 0.9)',
                  wordBreak: 'break-word',
                }}
              >
                {uploadMutation.error instanceof Error
                  ? uploadMutation.error.message
                  : (uploadMutation.error as any)?.response?.data?.detail || 'Failed to upload file. Please try again.'}
              </Typography>
            </Paper>
          )}

          {/* File Info and Progress - Show when file is selected OR when there's an active job */}
          {/* Don't show new file selection if there's an active job - show the active job instead */}
          {((selectedFile && !hasActiveJob) || jobId || hasProgressData) && (
            <Paper
              sx={{
                p: 2,
                bgcolor: 'rgba(255, 255, 255, 0.05)',
                borderRadius: '8px',
              }}
            >
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Box
                    sx={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      bgcolor: displayProgressData?.status === 'completed' ? '#4CAF50' : '#66CCFF',
                    }}
                  />
                  <InsertDriveFileIcon sx={{ color: '#66CCFF', fontSize: 20 }} />
                  <Box>
                    <Typography sx={{ color: '#FFFFFF', fontWeight: 500 }}>
                      {/* Prioritize active job's filename over newly selected file */}
                      {displayProgressData?.filename || selectedFile?.name || 'Processing file...'}
                    </Typography>
                    {/* Show file size only if it's a newly selected file (not from active job) */}
                    {selectedFile && !hasActiveJob && (
                      <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.6)' }}>
                        {formatFileSize(selectedFile.size)}
                      </Typography>
                    )}
                  </Box>
                </Box>

                <Box sx={{ display: 'flex', gap: 1 }}>
                  <IconButton
                    size="small"
                    onClick={handlePauseResume}
                    disabled={!jobId}
                    sx={{
                      color: '#FFFFFF',
                      '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.1)' },
                    }}
                  >
                    {isPaused ? <PlayArrowIcon /> : <PauseIcon />}
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={handleDelete}
                    sx={{
                      color: '#FF5252',
                      '&:hover': { bgcolor: 'rgba(255, 82, 82, 0.1)' },
                    }}
                  >
                    <DeleteIcon />
                  </IconButton>
                </Box>
              </Box>

              {/* Loading State */}
              {isLoadingProgress && !displayProgressData && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" sx={{ color: 'rgba(255, 255, 255, 0.7)', mb: 1 }}>
                    Initializing upload...
                  </Typography>
                  <LinearProgress
                    sx={{
                      height: 8,
                      borderRadius: 4,
                      bgcolor: 'rgba(255, 255, 255, 0.1)',
                    }}
                  />
                </Box>
              )}

              {/* Error State */}
              {progressError && (
                <Box
                  sx={{
                    p: 1.5,
                    mb: 2,
                    bgcolor: 'rgba(255, 82, 82, 0.1)',
                    borderRadius: '4px',
                    border: '1px solid rgba(255, 82, 82, 0.3)',
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{
                      color: '#FF5252',
                      wordBreak: 'break-word',
                    }}
                  >
                    Error loading progress: {progressError instanceof Error ? progressError.message : 'Unknown error'}
                  </Typography>
                </Box>
              )}

              {/* Statistics - Always show when we have progress data or an active job */}
              {(hasProgressData || hasActiveJob) && (
                <Box sx={{ display: 'flex', gap: 3, mb: 2, flexWrap: 'wrap' }}>
                  <Box>
                    <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.6)' }}>
                      Total Records:
                    </Typography>
                    <Typography 
                      sx={{ 
                        color: !hasProgressData ? 'rgba(255, 255, 255, 0.5)' : '#FFFFFF', 
                        fontWeight: 600,
                        fontStyle: !hasProgressData ? 'italic' : 'normal'
                      }}
                    >
                      {!hasProgressData ? 'Loading...' : totalRecords.toLocaleString()}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.6)' }}>
                      Processed:
                    </Typography>
                    <Typography 
                      sx={{ 
                        color: !hasProgressData ? 'rgba(76, 175, 80, 0.5)' : '#4CAF50', 
                        fontWeight: 600,
                        fontStyle: !hasProgressData ? 'italic' : 'normal'
                      }}
                    >
                      {!hasProgressData ? 'Loading...' : processedRecords.toLocaleString()}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.6)' }}>
                      Unprocessed:
                    </Typography>
                    <Typography 
                      sx={{ 
                        color: !hasProgressData ? 'rgba(255, 82, 82, 0.5)' : '#FF5252', 
                        fontWeight: 600,
                        fontStyle: !hasProgressData ? 'italic' : 'normal'
                      }}
                    >
                      {!hasProgressData ? 'Loading...' : unprocessedRecords.toLocaleString()}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.6)' }}>
                      Scored:
                    </Typography>
                    <Typography 
                      sx={{ 
                        color: !hasProgressData ? 'rgba(102, 204, 255, 0.5)' : '#66CCFF', 
                        fontWeight: 600,
                        fontStyle: !hasProgressData ? 'italic' : 'normal'
                      }}
                    >
                      {!hasProgressData ? 'Loading...' : scoredRecords.toLocaleString()}
                    </Typography>
                  </Box>
                </Box>
              )}

              {/* Progress Bar */}
              <Box>
                <LinearProgress
                  variant={progressData ? "determinate" : "indeterminate"}
                  value={getProgressPercentage()}
                  sx={{
                    height: 8,
                    borderRadius: 4,
                    bgcolor: 'rgba(255, 255, 255, 0.1)',
                    '& .MuiLinearProgress-bar': {
                      bgcolor: '#66CCFF',
                      borderRadius: 4,
                    },
                  }}
                />
                <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.6)', mt: 0.5, display: 'block' }}>
                  {displayProgressData ? `${getProgressPercentage().toFixed(0)}%` : 'Processing...'}
                </Typography>
              </Box>

              {/* Status Chip */}
              {displayProgressData?.status && (
                <Box sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Chip
                    label={displayProgressData.status.toUpperCase()}
                    size="small"
                    color={getStatusColor(displayProgressData.status)}
                    sx={{ textTransform: 'uppercase' }}
                  />
                  {/* Error Message */}
                  {displayProgressData.status === 'failed' && displayProgressData.error_message && (
                    <Box
                      sx={{
                        p: 1.5,
                        bgcolor: 'rgba(255, 82, 82, 0.1)',
                        borderRadius: '4px',
                        border: '1px solid rgba(255, 82, 82, 0.3)',
                      }}
                    >
                      <Typography
                        variant="caption"
                        sx={{
                          color: '#FF5252',
                          fontWeight: 500,
                          display: 'block',
                          mb: 0.5,
                        }}
                      >
                        Error:
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{
                          color: 'rgba(255, 255, 255, 0.9)',
                          wordBreak: 'break-word',
                        }}
                      >
                        {displayProgressData.error_message}
                      </Typography>
                    </Box>
                  )}
                </Box>
              )}
            </Paper>
          )}
        </Stack>
      </DialogContent>

      <DialogActions
        sx={{
          borderTop: '1px solid rgba(255, 255, 255, 0.1)',
          p: 2,
          justifyContent: 'space-between',
        }}
      >
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            onClick={handleTrafficDataAnalysis}
            disabled={!hasDataForSEO || trafficDataMutation.isPending}
            startIcon={<AnalyticsIcon />}
            sx={{
              bgcolor: '#FF5252',
              color: '#FFFFFF',
              '&:hover': {
                bgcolor: '#FF4444',
              },
              '&:disabled': {
                bgcolor: 'rgba(255, 82, 82, 0.3)',
                color: 'rgba(255, 255, 255, 0.5)',
              },
            }}
          >
            {trafficDataMutation.isPending ? 'Processing...' : 'Traffic data (1000)'}
          </Button>
          <Button
            variant="contained"
            onClick={handleBulkRankAnalysis}
            disabled={!hasDataForSEO || bulkRankAnalysisMutation.isPending}
            startIcon={<AnalyticsIcon />}
            sx={{
              bgcolor: '#4CAF50',
              color: '#FFFFFF',
              '&:hover': {
                bgcolor: '#45A049',
              },
              '&:disabled': {
                bgcolor: 'rgba(76, 175, 80, 0.3)',
                color: 'rgba(255, 255, 255, 0.5)',
              },
            }}
          >
            {bulkRankAnalysisMutation.isPending ? 'Processing...' : 'Bulk Rank Analysis (1000)'}
          </Button>
          <Button
            variant="contained"
            disabled={!hasDataForSEO || bulkBacklinksAnalysisMutation.isPending}
            onClick={() => {
              bulkBacklinksAnalysisMutation.mutate();
            }}
            sx={{
              bgcolor: '#2196F3',
              color: '#FFFFFF',
              '&:hover': {
                bgcolor: '#1976D2',
              },
              '&:disabled': {
                bgcolor: 'rgba(255, 255, 255, 0.1)',
                color: 'rgba(255, 255, 255, 0.5)',
              },
            }}
          >
            {bulkBacklinksAnalysisMutation.isPending ? 'Processing...' : 'Bulk Backlinks Analysis (1000)'}
          </Button>
          <Button
            variant="contained"
            disabled={!hasDataForSEO || bulkSpamScoreAnalysisMutation.isPending}
            onClick={() => {
              bulkSpamScoreAnalysisMutation.mutate();
            }}
            sx={{
              bgcolor: '#9C27B0',
              color: '#FFFFFF',
              '&:hover': {
                bgcolor: '#7B1FA2',
              },
              '&:disabled': {
                bgcolor: 'rgba(255, 255, 255, 0.1)',
                color: 'rgba(255, 255, 255, 0.5)',
              },
            }}
          >
            {bulkSpamScoreAnalysisMutation.isPending ? 'Processing...' : 'Bulk Spam Score Analysis (1000)'}
          </Button>
        </Box>
        <Button
          onClick={onClose}
          sx={{
            color: '#FFFFFF',
            textTransform: 'none',
            '&:hover': {
              bgcolor: 'rgba(255, 255, 255, 0.1)',
            },
          }}
        >
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default LoadFilePopup;

