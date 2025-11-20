"""Tests for the Zanzibar Model Engine."""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

from app import engine
from app import config

class TestEngine(unittest.TestCase):

    def setUp(self):
        # Create dummy data
        self.dummy_sanitation = pd.DataFrame({
            'id': [1, 2, 3, 4],
            'lat': [0.0, 0.0, 0.0, 0.0],
            'long': [0.0, 0.0, 0.0, 0.0],
            'toilet_category_id': [1, 2, 3, 4], # Sewer, Pit, Septic, OD
            'household_population': [10, 10, 10, 10]
        })
        
        self.dummy_boreholes = pd.DataFrame({
            'id': ['b1'],
            'lat': [0.0001], # Very close
            'long': [0.0001],
            'Q_L_per_day': [1000.0]
        })

    def test_apply_interventions_no_change(self):
        scenario = {'pop_factor': 1.0}
        df = engine.apply_interventions(self.dummy_sanitation, scenario)
        self.assertEqual(len(df), 4)
        self.assertEqual(df['household_population'].sum(), 40)

    def test_apply_interventions_pop_growth(self):
        scenario = {'pop_factor': 1.5}
        df = engine.apply_interventions(self.dummy_sanitation, scenario)
        self.assertEqual(df['household_population'].sum(), 60)

    def test_apply_interventions_od_reduction(self):
        # Convert 50% OD (cat 4) to Septic (cat 3)
        scenario = {'od_reduction_percent': 50.0}
        df = engine.apply_interventions(self.dummy_sanitation, scenario)
        
        # Original OD row should have 5 pop
        od_row = df[df['toilet_category_id'] == 4]
        self.assertEqual(od_row['household_population'].sum(), 5.0)
        
        # New Septic row should have 5 pop (plus original septic 10 = 15)
        septic_rows = df[df['toilet_category_id'] == 3]
        self.assertEqual(septic_rows['household_population'].sum(), 15.0)
        
        # Total pop conserved
        self.assertEqual(df['household_population'].sum(), 40.0)

    def test_compute_load_fio(self):
        pcfg = engine.PollutantConfig(
            name='fio',
            output_load_path=Path('dummy.csv'),
            efio=1.0,
            decay_rate=0.0
        )
        # Efficiencies: 1=0.5, 2=0.1, 3=0.3, 4=0.0
        # Leakage: 1=0.5, 2=0.9, 3=0.7, 4=1.0
        
        df = self.dummy_sanitation.copy()
        df['pathogen_containment_efficiency'] = df['toilet_category_id'].map(config.CONTAINMENT_EFFICIENCY_DEFAULT)
        
        res = engine.compute_load(df, pcfg)
        
        # OD (id 4) -> Pop 10 * EFIO 1.0 * Leakage 1.0 = 10.0
        self.assertEqual(res.loc[res['toilet_category_id'] == 4, 'load'].values[0], 10.0)
        
        # Sewer (id 1) -> Pop 10 * EFIO 1.0 * Leakage 0.5 = 5.0
        self.assertEqual(res.loc[res['toilet_category_id'] == 1, 'load'].values[0], 5.0)

    def test_transport_vectorized(self):
        pcfg = engine.PollutantConfig(
            name='fio',
            output_load_path=Path('dummy.csv'),
            efio=1.0,
            decay_rate=0.0 # No decay
        )
        
        toilets = self.dummy_sanitation.copy()
        toilets['load'] = 100.0 # 4 toilets * 100 = 400 total load
        
        # Radius large enough to cover everything
        res = engine.run_transport(toilets, self.dummy_boreholes, pcfg, radius_m=10000.0)
        
        self.assertEqual(len(res), 1)
        # Should capture all 4 toilets
        self.assertAlmostEqual(res['aggregated_load'].values[0], 400.0)

if __name__ == '__main__':
    unittest.main()
