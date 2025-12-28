-- Migration to load scoring data into word_frequency and industry_keywords tables
-- This migration is a placeholder - actual data loading will be done via Python script
-- See: backend/scripts/load_scoring_data_to_db.py

-- Note: The data will be loaded using the Python script which reads from:
-- - backend/src/services/scoring_data/word_frequency.json
-- - backend/src/services/scoring_data/industry_keywords.json

-- This migration file exists to document the data loading step
-- Run the Python script after applying this migration:
-- python backend/scripts/load_scoring_data_to_db.py
