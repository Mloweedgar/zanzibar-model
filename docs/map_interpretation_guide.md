# 🗺️ Map Interpretation Guide

This guide helps you understand the three main views in the Zanzibar Water Quality Model dashboard.

## 1. 🦠 Pathogen Risk (E. coli)
This map shows the predicted contamination levels at specific borehole locations.

*   **What it shows:** The concentration of *E. coli* bacteria in groundwater.
*   **Metric:** CFU/100mL (Colony Forming Units per 100 milliliters).
*   **Visuals:**
    *   **Color:**
        *   🟢 **Green**: Low Risk (Safe)
        *   🟡 **Yellow**: Moderate Risk
        *   🔴 **Red**: High Risk (>100 CFU/100mL)
    *   **Size:** Larger points indicate higher contamination levels.
*   **Key Insight:** Look for clusters of red points. These are "hotspots" where sanitation interventions are most urgently needed.

## 2. 🌱 Nitrogen Load
This map shows the amount of nitrogen leaching into the ground from sanitation sources.

*   **What it shows:** The intensity of nitrogen pollution from toilets and septic tanks.
*   **Metric:** kg/year (Kilograms of Nitrogen per year).
*   **Visuals:**
    *   **Color:**
        *   🔵 **Light Blue**: Low Load
        *   🔵 **Dark Blue**: High Load (>50 kg/yr)
    *   **Size:** Fixed size.
*   **Key Insight:** Dark blue areas represent high-density pollution sources. These areas might not always match pathogen hotspots due to transport differences (nitrogen travels further than pathogens).

## 3. 🚽 Toilet Inventory
This map visualizes the raw sanitation census data, showing what types of toilets are used across the island.

*   **What it shows:** The distribution of different sanitation technologies.
*   **Visuals (Color Coded):**
    *   🟢 **Green**: Sewer (Best)
    *   🔵 **Blue**: Septic Tank
    *   🟠 **Orange**: Pit Latrine
    *   🔴 **Red**: Open Defecation (Worst)
*   **Key Insight:** Use this to validate your data. If you see a "Sewer" point in a rural village where no sewer exists, it might be a data error.
