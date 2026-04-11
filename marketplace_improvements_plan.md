# Implementation Plan: Marketplace Improvements

## Overview
This document outlines the changes required to improve the Marketplace page, including UI reorganization, functionality fixes, and mobile responsiveness.

## Tasks

### 1. Remove Search Functionality
- **Files**: `frontend/src/app/pages/marketplace/marketplace.html`, `frontend/src/app/pages/marketplace/marketplace.ts`
- **Changes**:
    - Delete the "Quick search analysis" input box and its container from the HTML.
    - Remove `searchQuery` signal, `onSearch()` method, and search-related logic from the TypeScript file.

### 2. Fix Table Sorting
- **Files**: `frontend/src/app/pages/marketplace/marketplace.html`, `frontend/src/app/pages/marketplace/marketplace.ts`
- **Changes**:
    - Verify that all table headers in `marketplace.html` have the correct `(click)="toggleSort('field_name')"` handlers.
    - Ensure the field names passed match the backend expected sort keys.

### 3. Rearrange Action Buttons & Filters
- **Files**: `frontend/src/app/pages/marketplace/marketplace.html`
- **Changes**:
    - Relocate the **Fill Metrics** button to the far right of the header/action area.
    - Group the following checkboxes to the left of "Fill Metrics":
        - **Pinned**
        - **w/SEO Stats** (Renamed from 'SEO Stats')
        - **w/name score** (Renamed from 'scored')
    - Align these checkboxes vertically with a small gap.
    - Position the **Filters** button to the left of this checkbox group.

### 4. Enhance Filters Box (TLD Filtering)
- **Files**: `frontend/src/app/pages/marketplace/marketplace.html`, `frontend/src/app/pages/marketplace/marketplace.ts`
- **Changes**:
    - Add a TLD section inside the filters dropdown.
    - Implement checkboxes for common TLDs (`.com`, `.net`, `.ai`, `.org`, `.io`, etc.) and an "All other TLDs" option.
    - Update `MarketplaceComponent` state and `fetchAuctions()` to send TLD filters to the API.

### 5. Update Table Action Buttons
- **Files**: `frontend/src/app/pages/marketplace/marketplace.html`, `frontend/src/app/pages/marketplace/marketplace.ts`
- **Changes**:
    - Remove the existing two action buttons in the far right column.
    - Replace with a single **Deep Analysis** button.
    - Configure the button to navigate to `/deepanalysis`.

### 6. Sidebar Text Update
- **Files**: `frontend/src/app/components/sidebar/sidebar.html` (or `.ts`)
- **Changes**:
    - Change text "Recent Scans" $\rightarrow$ "Recent Reports".

### 7. Mobile Responsiveness
- **Files**: `frontend/src/app/pages/marketplace/marketplace.html`, `frontend/src/app/pages/marketplace/marketplace.ts`
- **Changes**:
    - Set `table-container` to `w-full`.
    - Implement a hamburger menu icon to collapse the filters/actions panel on mobile.
    - Use Tailwind responsive prefixes (`sm:`, `md:`, `lg:`) to ensure the layout adapts to smaller screens.
