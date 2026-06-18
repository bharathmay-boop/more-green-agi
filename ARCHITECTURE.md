# Architecture

## Current State
- Existing Shopify website with minimal custom theme elements.

## Proposed State (Mass Premium Overhaul)
  - **Tech Stack**: Native Shopify Theme (Cloned from `dawn` base into `moregreen-v2-theme`). Custom Liquid sections combined with specific Vanilla CSS rules inside `assets/moregreen-premium.css`.
  - **Core Strategy**: Shift from simple supplement positioning to an "Everyday Ingredient" narrative using the **Dark Label Mass Premium** aesthetic.
  - **Key Enhancements (V2)**:
    - High-end aesthetics via `.dark-label` CSS utilities (rich shadows, deep green backgrounds).
    - Pivot away from "Green Gold" entirely. Focus on a 4-SKU Stand-Up Pouch architecture: Sunflower 30g (60%), Blueberry 30g (30%), Moringa 100g, Wheatgrass 80g.
    - Explicit trust signals (Doctor Founded, NABL Verified, 51% Complete Protein) heavily emphasized in Hero & Product cards.
    - Exported as `moregreen-v2-mass-premium.zip` using POSIX-compliant `tar` to avoid Shopify Windows upload errors.
