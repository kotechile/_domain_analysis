A user’s journey through the Domain Analysis System ("Domain Scout App") is designed to move from
  high-volume filtering to deep, AI-assisted due diligence. Here is how the
  workflow is structured:


  1. Onboarding & Authentication
   * Account Creation: Users sign up via email or Google OAuth. The system uses
     Supabase Auth for session management.
   * Initial Credits: Upon registration, users typically start with a base "Free
     Tier" subscription.
   * Credit Management:
       * Dashboard: Users can view their current balance and transaction history
         (e.g., "Deducted 0.16 credits for Stats Sync").
       * Pricing: The system uses a Tiered Pricing Model managed by the
         PricingService. For example, an LLM call costing \$0.05 is billed at a
         markup (e.g., \$0.15–\$0.20 in credits).
       * Payment Gap: Currently, the system has a /credits/purchase endpoint.
       *PAyment processs still needs to be created
         that mocks the purchase flow. It adds credits to the account but is not
         yet integrated with a live payment processor like Stripe.


  2. Marketplace Discovery (The Funnel)
   * Live Lists: Users see a consolidated list of domains from marketplaces like
     GoDaddy and Name Silo.
   * Semantic Scoring (Level 0): This is the first filter. The system calculates
     a score based purely on the domain's construction:
       * Domain Age (40%): Older domains are more "trusted."
       * Lexical Frequency (30%): Uses commonality of words (identifying
         "dictionary" words).
       * Commercial Intent (30%): Semantic analysis to see if the keywords match
         high-value industries (e.g., finance, tech, health).
       * Result: Users see a "Meaning Score" (0–100) and a "Pass/Fail"
         recommendation to quickly skip gibberish or low-value domains.


  3. Analysis Levels (Detailed vs. Quick)
  If a domain looks interesting, the user can choose to "Enrich" it. This
  triggers external API calls and deducts credits.


  Quick Analysis (Level 1 - Essential)
   * Purpose: Rapid validation of SEO strength without deep-diving into
     historical data.
   * Features:
       * Basic SEO Metrics: Real-time Domain Rating (DR) and Estimated Organic
         Traffic via DataForSEO.
       * Backlink Summary: Total referring domains and top-level backlink
         counts.
       * Spam Check: Initial "Spam Score" to flag toxic profiles.


  Detailed Analysis (Level 2 - Deep Dive)
   * Purpose: Comprehensive due diligence for high-value investments.
   * Features:
       * All Quick Analysis Features +
       * Wayback Machine History: Analysis of first/last captures to ensure the
         domain wasn't used for a PBN (Private Blog Network) or illegal content.
       * Keyword Analysis: A detailed breakdown of the top keywords the domain
         currently (or recently) ranked for.
       * Referring Domains Detail: A list of the specific high-authority sites
         linking to the domain.
       * AI Investment Memo (Gemini): An LLM-generated report including:
           * Niche Suggestions: Best industries for this domain.
           * Content Plan: A 3-month roadmap for rebuilding the site.
           * Monetization Strategy: Suggestions (Affiliate, Ads, SaaS, etc.).
           * Pros/Cons Table: A clear breakdown of why to buy or pass.


  4. Technical Workflow
   * Asynchronous Processing: Since Detailed Analysis takes time (fetching from
     3+ APIs and an LLM), the user sees a Progress Indicator. The backend runs
     these as background tasks, updating the UI as each phase (Essential →
     Detailed → AI) completes.
   * Storage: All reports are saved in Supabase, allowing users to revisit their
     "Analysis History" without spending more credits.